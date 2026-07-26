"""Tests for the MCP Server Module."""

import json
import pytest
from mcp.server.fastmcp import FastMCP
from src.simulator.building import BuildingSimulator
from src.config.settings import Config
from src.mcp_server.server import create_mcp_server


@pytest.fixture
def sim():
    return BuildingSimulator()

@pytest.fixture
def config():
    return Config()

@pytest.fixture
def mcp_server(sim, config) -> FastMCP:
    return create_mcp_server(sim, config)

@pytest.mark.anyio
async def test_tools_registered(mcp_server):
    tools = await mcp_server.list_tools()
    tool_names = [t.name for t in tools]
    
    assert "get_building_status" in tool_names
    assert "set_hvac_temperature" in tool_names
    assert "adjust_ventilation" in tool_names
    assert "set_shading" in tool_names

def _extract_text(result) -> str:
    # If the result is a CallToolResult object with a content attribute
    if hasattr(result, "content"):
        result = result.content
        
    # If the result is a tuple (e.g. some versions of fastmcp return tuples)
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

@pytest.mark.anyio
async def test_validation_failure_returns_cleanly(mcp_server):
    # setpoint out of bounds (config default min is 20, max is 24)
    args = {"zone": "south", "setpoint": 10.0}
    result = await mcp_server.call_tool("set_hvac_temperature", args)
    
    resp_text = _extract_text(result)
    resp = json.loads(resp_text)
    
    assert resp["success"] is False
    assert "out of bounds" in resp["error"]

@pytest.mark.anyio
async def test_valid_command_updates_simulator(mcp_server, sim):
    args = {"zone": "north", "setpoint": 23.5}
    result = await mcp_server.call_tool("set_hvac_temperature", args)
    
    resp_text = _extract_text(result)
    resp = json.loads(resp_text)
    
    assert resp["success"] is True
    assert sim.zones["north"].hvac_setpoint == 23.5

@pytest.mark.anyio
async def test_get_building_status(mcp_server):
    result = await mcp_server.call_tool("get_building_status", {})
    
    resp_text = _extract_text(result)
    resp = json.loads(resp_text)
    
    assert "zones" in resp
    assert "south" in resp["zones"]
    assert "energy" in resp
