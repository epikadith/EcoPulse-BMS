"""
Main entry point for the EcoPulse-MCP backend.
Ties together configuration, simulation, MCP, agent loop, and websocket broadcasting.
"""

import asyncio
import json
import logging
import os
import sys

from src.config.settings import load_config
from src.simulator.building import BuildingSimulator
from src.mcp_server.server import create_mcp_server
from src.agent.loop import run_agent_loop
from src.websocket_server.server import start_websocket_server


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production use."""

    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging():
    """Configure structured JSON logging for the entire backend."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger("ecopulse")
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    return root_logger


async def main():
    logger = setup_logging()
    logger.info("Initializing EcoPulse Backend...")

    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "default.json")
    try:
        config = load_config(config_path)
    except Exception as e:
        logger.error("Error loading config: %s", e)
        sys.exit(1)

    logger.info("Configuration loaded. LLM model: %s", config.llm.model)

    # 1. Initialize Simulator
    simulator = BuildingSimulator()
    logger.info("Simulator initialized.")

    # 2. Create MCP Server
    mcp_server = create_mcp_server(simulator, config)
    logger.info("MCP Server created.")

    # 3. Start tasks
    logger.info(
        "Starting WebSocket server on %s:%d",
        config.websocket.host,
        config.websocket.port,
    )

    ws_task = asyncio.create_task(start_websocket_server(config))
    agent_task = asyncio.create_task(run_agent_loop(mcp_server, simulator, config))

    try:
        await asyncio.gather(ws_task, agent_task)
    except asyncio.CancelledError:
        logger.info("Shutting down...")


def main_entry():
    """Synchronous entry point for [project.scripts]."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting gracefully.")


if __name__ == "__main__":
    main_entry()
