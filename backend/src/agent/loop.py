"""
Agent orchestrator for the EcoPulse BMS.

Provides both the refactored AgentOrchestrator class (with threshold-triggered
reactive mode) and backward-compatible standalone functions.
"""

import asyncio
import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.config.settings import Config
from src.agent.llm import query_llm
from src.agent.prompt import build_system_prompt, build_user_prompt
from src.agent.parser import parse_llm_response, extract_reasoning, Action
from src.agent.data_pipeline import metrics_to_dataframe, dataframe_to_prompt_text
from src.websocket_server.server import broadcast_message

logger = logging.getLogger("ecopulse.agent.loop")


def _extract_text(result: Any) -> str:
    """Safely extracts text from FastMCP tool call results."""
    if hasattr(result, "content"):
        result = result.content
    if isinstance(result, tuple) and len(result) > 0:
        result = result[0]
    if isinstance(result, str):
        return result
    if isinstance(result, list) and len(result) > 0:
        item = result[0]
        if hasattr(item, "text"):
            return item.text
        elif isinstance(item, dict) and "text" in item:
            return item["text"]
        elif hasattr(item, "type") and item.type == "text":
            return getattr(item, "text", str(item))
        return str(item)
    return str(result)


class AgentOrchestrator:
    """
    Core agent orchestrator with configurable loop modes.

    Supports:
    - Fixed-interval loop (default 30s)
    - Threshold-triggered reactive loop (temperature crosses bounds)
    """

    def __init__(self, mcp_server: FastMCP, simulator, config: Config):
        self.mcp_server = mcp_server
        self.simulator = simulator
        self.config = config
        self.system_prompt = build_system_prompt(config)
        self.decision_log: list[dict] = []

    def _check_thresholds(self, metrics: dict) -> bool:
        """
        Check if any zone temperature has crossed the configured thresholds.

        Returns True if a threshold was crossed (triggering a reactive cycle).
        """
        thresholds = self.config.control_loop.thresholds
        temp_high = thresholds.get("temperature_high", 24.0)
        temp_low = thresholds.get("temperature_low", 20.0)

        zones = metrics.get("zones", {})
        for zone_name, zone_data in zones.items():
            temp = zone_data.get("indoor_temp", 22.0)
            if temp > temp_high or temp < temp_low:
                logger.info(
                    "Threshold triggered: zone '%s' at %.1f°C (bounds: %.1f–%.1f)",
                    zone_name, temp, temp_low, temp_high,
                )
                return True
        return False

    async def run_step(self) -> dict:
        """
        Execute a single agent reasoning cycle.

        1. Fetch building state via MCP
        2. Structure into Polars DataFrame
        3. Build prompt
        4. Call Ollama API
        5. Parse LLM response into actions
        6. Validate each action (done by MCP tools)
        7. Execute valid actions via MCP tools
        8. Log decision for dashboard
        """
        # 1. Fetch state
        status_result = await self.mcp_server.call_tool("get_building_status", {})
        status_json = _extract_text(status_result)
        metrics = json.loads(status_json)

        # 2. Structure into Polars DataFrame
        df = metrics_to_dataframe(metrics)

        # 3. Build prompts
        summary_text = dataframe_to_prompt_text(df, metrics)
        user_prompt = build_user_prompt(df, summary_text)

        # 4. Query LLM (run in thread to prevent blocking the event loop)
        logger.info(f"Querying LLM ({self.config.llm.model})...")
        try:
            llm_response = await asyncio.wait_for(
                asyncio.to_thread(query_llm, user_prompt, self.system_prompt, self.config),
                timeout=120.0
            )
            logger.info("LLM query returned successfully.")
        except asyncio.TimeoutError:
            logger.error("LLM query timed out after 120 seconds.")
            llm_response = {"error": "LLM timed out"}
        except Exception as e:
            logger.error(f"LLM query raised exception: {e}")
            llm_response = {"error": str(e)}

        if "error" in llm_response:
            decision = {
                "success": False,
                "error": llm_response["error"],
                "reasoning": "",
            }
            self.decision_log.append(decision)
            return decision

        # 5. Parse response
        reasoning = extract_reasoning(llm_response)
        actions = parse_llm_response(llm_response)

        # 6 & 7. Execute actions (validation happens inside MCP tools)
        results = []
        for action in actions:
            try:
                res = await self.mcp_server.call_tool(action.tool, action.args)
                results.append({
                    "tool": action.tool,
                    "args": action.args,
                    "result": _extract_text(res),
                })
            except Exception as e:
                results.append({
                    "tool": action.tool,
                    "args": action.args,
                    "error": str(e),
                })

        # 8. Log decision
        decision = {
            "success": True,
            "reasoning": reasoning,
            "actions_executed": results,
        }
        self.decision_log.append(decision)

        logger.info(
            "Agent cycle complete: %d actions executed, reasoning: %s",
            len(results),
            reasoning[:100] if reasoning else "(none)",
        )

        return decision

    async def run_loop(self):
        """
        Run the continuous agent control loop with both fixed-interval
        and threshold-triggered reactive modes.
        """
        logger.info("Agent orchestrator loop started.")
        interval = self.config.control_loop.interval_seconds

        while True:
            # Advance simulation
            self.simulator.tick(15.0)

            # Get current metrics for broadcasting and threshold checking
            metrics = self.simulator.get_metrics()
            await broadcast_message({"type": "metrics", "data": metrics})

            # Always run on fixed interval, but also check thresholds
            threshold_triggered = self._check_thresholds(metrics)

            if threshold_triggered:
                logger.info("Running reactive agent cycle (threshold triggered)")

            # Run reasoning
            result = await self.run_step()

            # Broadcast decision
            await broadcast_message({"type": "agent_action", "data": result})

            # Wait for the next interval
            await asyncio.sleep(interval)


# ──────────────────────────────────────────────────────────────
# Backward-compatible standalone functions
# ──────────────────────────────────────────────────────────────

async def run_agent_step(mcp_server: FastMCP, config: Config) -> dict:
    """
    Executes a single pass of the agent reasoning loop.
    Backward-compatible wrapper around AgentOrchestrator.run_step().
    """
    # 1. Fetch State
    status_result = await mcp_server.call_tool("get_building_status", {})
    status_json = _extract_text(status_result)

    # 2. Build prompt using new modules
    metrics = json.loads(status_json)
    df = metrics_to_dataframe(metrics)
    summary_text = dataframe_to_prompt_text(df, metrics)
    system_prompt = build_system_prompt(config)
    user_prompt = build_user_prompt(df, summary_text)

    # 3. Query LLM (run in thread to prevent blocking the event loop)
    llm_response = await asyncio.to_thread(query_llm, user_prompt, system_prompt, config)

    if "error" in llm_response:
        return {"success": False, "error": llm_response["error"]}

    # 4. Parse and execute actions
    actions = parse_llm_response(llm_response)
    reasoning = extract_reasoning(llm_response)
    results = []

    for action in actions:
        try:
            res = await mcp_server.call_tool(action.tool, action.args)
            results.append({
                "tool": action.tool,
                "args": action.args,
                "result": _extract_text(res),
            })
        except Exception as e:
            results.append({
                "tool": action.tool,
                "args": action.args,
                "error": str(e),
            })

    return {
        "success": True,
        "reasoning": reasoning,
        "actions_executed": results,
    }


async def run_agent_loop(mcp_server: FastMCP, simulator, config: Config):
    """
    Runs the continuous agent control loop.
    Uses AgentOrchestrator internally.
    """
    orchestrator = AgentOrchestrator(mcp_server, simulator, config)
    await orchestrator.run_loop()
