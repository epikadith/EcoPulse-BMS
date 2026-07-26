import json
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMConfig:
    model: str = "gemma4:e4b"
    temperature: float = 0.3


@dataclass
class OptimizationConfig:
    mode: str = "balanced"
    weights: dict[str, float] = field(default_factory=lambda: {"energy": 0.5, "comfort": 0.5})


@dataclass
class ControlLoopConfig:
    interval_seconds: int = 30
    thresholds: dict[str, float] = field(
        default_factory=lambda: {"temperature_high": 24.0, "temperature_low": 20.0}
    )


@dataclass
class ConstraintsConfig:
    temperature_min: float = 20.0
    temperature_max: float = 24.0
    ventilation_min: float = 0.0
    ventilation_max: float = 100.0
    shading_min: float = 0.0
    shading_max: float = 100.0


@dataclass
class WebsocketConfig:
    host: str = "0.0.0.0"
    port: int = 8765


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    control_loop: ControlLoopConfig = field(default_factory=ControlLoopConfig)
    zones: list[str] = field(default_factory=lambda: ["south", "north", "core"])
    constraints: ConstraintsConfig = field(default_factory=ConstraintsConfig)
    websocket: WebsocketConfig = field(default_factory=WebsocketConfig)


_CONFIG_INSTANCE = None


def load_config(path: str) -> Config:
    """Load configuration from JSON and apply environment variable overrides."""
    global _CONFIG_INSTANCE

    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Validate required keys (e.g., zones must be present and valid)
    if "zones" not in data or not isinstance(data["zones"], list):
        raise ValueError("Configuration must contain a 'zones' list.")

    cfg = Config()
    cfg.zones = data.get("zones", cfg.zones)

    if "llm" in data:
        cfg.llm.model = data["llm"].get("model", cfg.llm.model)
        cfg.llm.temperature = data["llm"].get("temperature", cfg.llm.temperature)

    if "optimization" in data:
        cfg.optimization.mode = data["optimization"].get("mode", cfg.optimization.mode)
        cfg.optimization.weights = data["optimization"].get("weights", cfg.optimization.weights)

    if "control_loop" in data:
        cfg.control_loop.interval_seconds = data["control_loop"].get("interval_seconds", cfg.control_loop.interval_seconds)
        cfg.control_loop.thresholds = data["control_loop"].get("thresholds", cfg.control_loop.thresholds)

    if "constraints" in data:
        for k in ["temperature_min", "temperature_max", "ventilation_min", "ventilation_max", "shading_min", "shading_max"]:
            if k in data["constraints"]:
                setattr(cfg.constraints, k, data["constraints"][k])

    if "websocket" in data:
        cfg.websocket.host = data["websocket"].get("host", cfg.websocket.host)
        cfg.websocket.port = data["websocket"].get("port", cfg.websocket.port)

    # Apply environment variable overrides
    if os.environ.get("ECOPULSE_LLM_MODEL"):
        cfg.llm.model = os.environ.get("ECOPULSE_LLM_MODEL")
    if os.environ.get("ECOPULSE_WS_PORT"):
        try:
            cfg.websocket.port = int(os.environ.get("ECOPULSE_WS_PORT"))
        except ValueError:
            pass

    _CONFIG_INSTANCE = cfg
    return cfg


def get_config() -> Config:
    """Get the globally loaded configuration object. Returns a default Config if not loaded yet."""
    global _CONFIG_INSTANCE
    if _CONFIG_INSTANCE is None:
        _CONFIG_INSTANCE = Config()
    return _CONFIG_INSTANCE
