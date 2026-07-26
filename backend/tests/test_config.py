"""Tests for the Configuration Module."""

import json
import os
import pytest
from src.config.settings import load_config, get_config, Config

@pytest.fixture
def temp_config_file(tmp_path):
    config_data = {
        "llm": {
            "model": "mistral",
            "temperature": 0.5
        },
        "optimization": {
            "mode": "comfort",
            "weights": { "energy": 0.2, "comfort": 0.8 }
        },
        "control_loop": {
            "interval_seconds": 60,
            "thresholds": {
                "temperature_high": 25.0,
                "temperature_low": 19.0
            }
        },
        "zones": ["east", "west"],
        "constraints": {
            "temperature_min": 19.0,
            "temperature_max": 25.0,
            "ventilation_min": 10.0,
            "ventilation_max": 90.0,
            "shading_min": 10.0,
            "shading_max": 90.0
        },
        "websocket": {
            "host": "127.0.0.1",
            "port": 9000
        }
    }
    file_path = tmp_path / "test_config.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
    return str(file_path)

@pytest.fixture
def minimal_config_file(tmp_path):
    config_data = {
        "zones": ["south"]
    }
    file_path = tmp_path / "test_config_minimal.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
    return str(file_path)

@pytest.fixture
def invalid_config_file(tmp_path):
    config_data = {
        "llm": {"model": "llama3"}
    }
    file_path = tmp_path / "test_config_invalid.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f)
    return str(file_path)

def test_valid_config_loads_correctly(temp_config_file):
    cfg = load_config(temp_config_file)
    assert cfg.llm.model == "mistral"
    assert cfg.llm.temperature == 0.5
    assert cfg.optimization.mode == "comfort"
    assert cfg.optimization.weights["energy"] == 0.2
    assert cfg.control_loop.interval_seconds == 60
    assert cfg.zones == ["east", "west"]
    assert cfg.constraints.temperature_min == 19.0
    assert cfg.websocket.host == "127.0.0.1"
    assert cfg.websocket.port == 9000
    
    # Check singleton updates
    assert get_config() is cfg

def test_missing_optional_keys_get_defaults(minimal_config_file):
    cfg = load_config(minimal_config_file)
    assert cfg.zones == ["south"]
    
    # Defaults
    assert cfg.llm.model == "llama3"
    assert cfg.control_loop.interval_seconds == 30
    assert cfg.websocket.port == 8765
    assert cfg.constraints.temperature_min == 20.0

def test_invalid_config_raises_error(invalid_config_file):
    with pytest.raises(ValueError, match="Configuration must contain a 'zones' list."):
        load_config(invalid_config_file)

def test_file_not_found_raises_error():
    with pytest.raises(FileNotFoundError):
        load_config("nonexistent_file_path.json")

def test_env_variable_overrides(temp_config_file, monkeypatch):
    monkeypatch.setenv("ECOPULSE_LLM_MODEL", "qwen")
    monkeypatch.setenv("ECOPULSE_WS_PORT", "9999")
    
    cfg = load_config(temp_config_file)
    
    # Overridden by env vars
    assert cfg.llm.model == "qwen"
    assert cfg.websocket.port == 9999
    
    # Unchanged
    assert cfg.llm.temperature == 0.5
    assert cfg.websocket.host == "127.0.0.1"

def test_get_config_returns_default_if_not_loaded(monkeypatch):
    import src.config.settings
    # Clear the singleton to simulate fresh start
    monkeypatch.setattr(src.config.settings, "_CONFIG_INSTANCE", None)
    
    cfg = get_config()
    assert isinstance(cfg, Config)
    assert cfg.llm.model == "llama3"  # default
