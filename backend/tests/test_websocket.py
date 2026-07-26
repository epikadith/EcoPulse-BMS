"""Integration tests for the WebSocket server."""

import asyncio
import json
import pytest
import websockets

from src.config.settings import Config
from src.websocket_server.server import (
    start_websocket_server,
    broadcast_message,
    _CONNECTED_CLIENTS,
)


@pytest.fixture
def config():
    cfg = Config()
    # Use a non-standard port to avoid conflicts
    cfg.websocket.host = "127.0.0.1"
    cfg.websocket.port = 18765
    return cfg


@pytest.mark.anyio
async def test_websocket_connect_and_receive(config):
    """Start server, connect a test client, broadcast a message, verify receipt."""
    # Start the server in the background
    server_task = asyncio.create_task(start_websocket_server(config))

    # Give the server a moment to start
    await asyncio.sleep(0.3)

    try:
        async with websockets.connect(
            f"ws://{config.websocket.host}:{config.websocket.port}"
        ) as ws:
            # Broadcast a test message
            test_msg = {"type": "metrics", "data": {"test": True}}
            await broadcast_message(test_msg)

            # Receive it on the client
            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            received = json.loads(raw)

            assert received["type"] == "metrics"
            assert received["data"]["test"] is True
    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        _CONNECTED_CLIENTS.clear()


@pytest.mark.anyio
async def test_websocket_message_structure(config):
    """Verify the JSON message structure matches the expected schema."""
    server_task = asyncio.create_task(start_websocket_server(config))
    await asyncio.sleep(0.3)

    try:
        async with websockets.connect(
            f"ws://{config.websocket.host}:{config.websocket.port}"
        ) as ws:
            # Broadcast an agent_action message
            agent_msg = {
                "type": "agent_action",
                "data": {
                    "success": True,
                    "reasoning": "Test reasoning",
                    "actions_executed": [
                        {"tool": "set_hvac_temperature", "args": {"zone": "south", "setpoint": 22.0}}
                    ],
                },
            }
            await broadcast_message(agent_msg)

            raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            received = json.loads(raw)

            # Verify structure
            assert "type" in received
            assert received["type"] in ("metrics", "agent_action")
            assert "data" in received
            assert received["data"]["success"] is True
            assert "actions_executed" in received["data"]
            assert len(received["data"]["actions_executed"]) == 1
    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        _CONNECTED_CLIENTS.clear()


@pytest.mark.anyio
async def test_websocket_multiple_clients(config):
    """Verify broadcast reaches all connected clients."""
    server_task = asyncio.create_task(start_websocket_server(config))
    await asyncio.sleep(0.3)

    uri = f"ws://{config.websocket.host}:{config.websocket.port}"

    try:
        async with websockets.connect(uri) as ws1, websockets.connect(uri) as ws2:
            await asyncio.sleep(0.1)  # Let both register

            test_msg = {"type": "metrics", "data": {"multi": True}}
            await broadcast_message(test_msg)

            raw1 = await asyncio.wait_for(ws1.recv(), timeout=2.0)
            raw2 = await asyncio.wait_for(ws2.recv(), timeout=2.0)

            assert json.loads(raw1)["data"]["multi"] is True
            assert json.loads(raw2)["data"]["multi"] is True
    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        _CONNECTED_CLIENTS.clear()
