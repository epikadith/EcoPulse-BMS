from typing import Tuple
from src.config.settings import Config

def validate_action(action_type: str, zone: str, value: float, config: Config) -> Tuple[bool, str]:
    """
    Validates an LLM-generated command against safety constraints before execution.
    
    Args:
        action_type: One of "set_hvac_temperature", "adjust_ventilation", "set_shading"
        zone: The zone name (e.g., "south", "north", "core")
        value: The numerical value for the action
        config: The current system configuration containing constraints
        
    Returns:
        A tuple of (is_valid, reason)
    """
    
    if zone not in config.zones:
        return False, f"Unknown zone: '{zone}'. Valid zones are: {config.zones}"
        
    constraints = config.constraints
    
    if action_type == "set_hvac_temperature":
        if not (constraints.temperature_min <= value <= constraints.temperature_max):
            return False, f"Temperature {value}°C is out of bounds [{constraints.temperature_min}, {constraints.temperature_max}]"
            
    elif action_type == "adjust_ventilation":
        if not (constraints.ventilation_min <= value <= constraints.ventilation_max):
            return False, f"Ventilation {value}% is out of bounds [{constraints.ventilation_min}, {constraints.ventilation_max}]"
            
    elif action_type == "set_shading":
        if not (constraints.shading_min <= value <= constraints.shading_max):
            return False, f"Shading {value}% is out of bounds [{constraints.shading_min}, {constraints.shading_max}]"
            
    else:
        return False, f"Unknown action_type: '{action_type}'"
        
    return True, ""
