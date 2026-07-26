import json
from mcp.server.fastmcp import FastMCP
from src.simulator.building import BuildingSimulator
from src.config.settings import Config
from src.validation.validator import validate_action

def create_mcp_server(simulator: BuildingSimulator, config: Config) -> FastMCP:
    """
    Creates and configures an MCP server exposing building simulator controls.
    
    Args:
        simulator: The BuildingSimulator instance
        config: System configuration
        
    Returns:
        A configured FastMCP server instance
    """
    mcp = FastMCP("EcoPulse")

    @mcp.tool()
    def get_building_status() -> str:
        """Returns all current zone metrics, weather, and energy data."""
        return json.dumps(simulator.get_metrics())

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
            res = simulator.apply_action(zone, "set_hvac_temperature", setpoint)
            return json.dumps(res)
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
            res = simulator.apply_action(zone, "adjust_ventilation", rate)
            return json.dumps(res)
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
            res = simulator.apply_action(zone, "set_shading", position)
            return json.dumps(res)
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    return mcp
