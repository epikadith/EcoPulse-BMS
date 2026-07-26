import json
from mcp.server.fastmcp import FastMCP
from src.simulator.ep_adapter import PyEnergyPlusSimulator
from src.config.settings import Config
from src.validation.validator import validate_action

def create_mcp_server(simulator: PyEnergyPlusSimulator, config: Config) -> FastMCP:
    """
    Creates and configures an MCP server exposing building simulator controls.
    
    Args:
        simulator: The PyEnergyPlusSimulator instance
        config: System configuration
        
    Returns:
        A configured FastMCP server instance
    """
    mcp = FastMCP("EcoPulse")

    @mcp.tool()
    def get_building_status() -> str:
        """Returns all current zone metrics, weather, and energy data."""
        # When querying the status, we don't return it from the simulator anymore because
        # the status is pushed by the simulator thread.
        # However, for MCP tool consistency, we can return the last known state.
        # But wait! We will handle state fetching in loop.py directly.
        return json.dumps({"status": "handled_by_orchestrator"})

    @mcp.tool()
    def set_hvac_temperature(zone: str, setpoint: float) -> str:
        """
        Adjust zone temperature setpoint.
        
        Args:
            zone: The target zone (south, north, core).
            setpoint: The target temperature setpoint in °C.
        """
        is_valid, reason = validate_action("set_hvac_temperature", zone, setpoint, config)
        if not is_valid:
            return json.dumps({"success": False, "error": reason})
        try:
            return json.dumps({"success": True, "zone": zone, "action": "set_hvac_temperature", "value": setpoint})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @mcp.tool()
    def adjust_ventilation(zone: str, rate: float) -> str:
        """
        Set ventilation rate (0-100%).
        
        Args:
            zone: The target zone (south, north, core).
            rate: The target ventilation rate.
        """
        is_valid, reason = validate_action("adjust_ventilation", zone, rate, config)
        if not is_valid:
            return json.dumps({"success": False, "error": reason})
        try:
            return json.dumps({"success": True, "zone": zone, "action": "adjust_ventilation", "value": rate})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    @mcp.tool()
    def set_shading(zone: str, position: float) -> str:
        """
        Set shading position (0-100%, 0=fully open).
        
        Args:
            zone: The target zone (south, north, core).
            position: The target shading position.
        """
        is_valid, reason = validate_action("set_shading", zone, position, config)
        if not is_valid:
            return json.dumps({"success": False, "error": reason})
        try:
            return json.dumps({"success": True, "zone": zone, "action": "set_shading", "value": position})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    return mcp
