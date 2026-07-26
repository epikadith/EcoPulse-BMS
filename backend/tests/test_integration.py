"""
Full backend integration test.

Mocks the Ollama LLM, starts the simulator + MCP + agent + WebSocket,
runs multiple agent cycles, and verifies the full data flow.
"""

import asyncio
import json
import pytest
import websockets
from unittest.mock import patch

from src.config.settings import Config
from src.simulator.building import BuildingSimulator
from src.mcp_server.server import create_mcp_server
from src.agent.loop import AgentOrchestrator
from src.websocket_server.server import (
    start_websocket_server,
    broadcast_message,
    _CONNECTED_CLIENTS,
)


@pytest.fixture
def config():
    cfg = Config()
    cfg.websocket.host = "127.0.0.1"
    cfg.websocket.port = 28765  # Unique port for integration tests
    cfg.control_loop.interval_seconds = 0  # No delay in tests
    return cfg


@pytest.fixture
def simulator():
    return BuildingSimulator()


@pytest.fixture
def mcp_server(simulator, config):
    return create_mcp_server(simulator, config)


MOCK_LLM_RESPONSE = {
    "reasoning": "Integration test: adjusting south zone setpoint for comfort.",
    "actions": [
        {"tool": "set_hvac_temperature", "args": {"zone": "south", "setpoint": 23.0}},
    ],
}


@pytest.mark.anyio
async def test_full_integration_3_cycles(config, simulator, mcp_server):
    """
    Run 3 full agent cycles with mocked LLM.
    Verify:
    - WebSocket client receives ≥3 metrics_update and ≥3 agent_action messages
    - Simulator state has changed from initial values
    """
    orchestrator = AgentOrchestrator(mcp_server, simulator, config)

    # Start WebSocket server
    ws_task = asyncio.create_task(start_websocket_server(config))
    await asyncio.sleep(0.3)

    received_messages = []

    try:
        async with websockets.connect(
            f"ws://{config.websocket.host}:{config.websocket.port}"
        ) as ws:
            # Run 3 agent cycles with mocked LLM
            with patch("src.agent.loop.query_llm", return_value=MOCK_LLM_RESPONSE):
                for _ in range(3):
                    # Advance simulation
                    simulator.tick(15.0)
                    metrics = simulator.get_metrics()
                    await broadcast_message({"type": "metrics", "data": metrics})

                    # Run reasoning
                    result = await orchestrator.run_step()
                    await broadcast_message({"type": "agent_action", "data": result})

            # Collect all messages from the WebSocket
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.5)
                    received_messages.append(json.loads(raw))
                except (asyncio.TimeoutError, Exception):
                    break

        # Verify message counts
        metrics_msgs = [m for m in received_messages if m.get("type") == "metrics"]
        action_msgs = [m for m in received_messages if m.get("type") == "agent_action"]

        assert len(metrics_msgs) >= 3, f"Expected ≥3 metrics messages, got {len(metrics_msgs)}"
        assert len(action_msgs) >= 3, f"Expected ≥3 agent_action messages, got {len(action_msgs)}"

        # Verify simulator state changed
        assert simulator.zones["south"].hvac_setpoint == 23.0, "Setpoint should have been updated"
        assert simulator.sim_time_minutes > 0, "Simulation time should have advanced"
        assert simulator.cumulative_energy_kwh > 0, "Energy should have been consumed"

        # Verify decision log
        assert len(orchestrator.decision_log) == 3

    finally:
        ws_task.cancel()
        try:
            await ws_task
        except asyncio.CancelledError:
            pass
        _CONNECTED_CLIENTS.clear()


@pytest.mark.anyio
async def test_integration_llm_error_recovery(config, simulator, mcp_server):
    """Verify the system handles LLM errors gracefully without crashing."""
    orchestrator = AgentOrchestrator(mcp_server, simulator, config)

    error_response = {"error": "Model not found"}

    with patch("src.agent.loop.query_llm", return_value=error_response):
        result = await orchestrator.run_step()

    assert result["success"] is False
    assert "Model not found" in result["error"]
    assert len(orchestrator.decision_log) == 1
