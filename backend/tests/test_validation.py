"""Tests for the Validation Layer."""

import pytest
from src.config.settings import Config, ConstraintsConfig
from src.validation.validator import validate_action

@pytest.fixture
def config():
    cfg = Config()
    cfg.zones = ["south", "north", "core"]
    cfg.constraints = ConstraintsConfig(
        temperature_min=20.0,
        temperature_max=24.0,
        ventilation_min=0.0,
        ventilation_max=100.0,
        shading_min=0.0,
        shading_max=100.0
    )
    return cfg


def test_valid_setpoint_passes(config):
    is_valid, reason = validate_action("set_hvac_temperature", "south", 22.0, config)
    assert is_valid is True
    assert reason == ""


def test_out_of_range_setpoint_low_rejected(config):
    is_valid, reason = validate_action("set_hvac_temperature", "south", 18.0, config)
    assert is_valid is False
    assert "out of bounds" in reason


def test_out_of_range_setpoint_high_rejected(config):
    is_valid, reason = validate_action("set_hvac_temperature", "north", 26.0, config)
    assert is_valid is False
    assert "out of bounds" in reason


def test_ventilation_low_rejected(config):
    is_valid, reason = validate_action("adjust_ventilation", "core", -5.0, config)
    assert is_valid is False
    assert "out of bounds" in reason


def test_ventilation_high_rejected(config):
    is_valid, reason = validate_action("adjust_ventilation", "south", 101.0, config)
    assert is_valid is False
    assert "out of bounds" in reason


def test_valid_ventilation_passes(config):
    is_valid, reason = validate_action("adjust_ventilation", "north", 50.0, config)
    assert is_valid is True
    assert reason == ""


def test_valid_shading_passes(config):
    is_valid, reason = validate_action("set_shading", "north", 50.0, config)
    assert is_valid is True
    assert reason == ""


def test_unknown_action_type_rejected(config):
    is_valid, reason = validate_action("activate_sprinklers", "south", 1.0, config)
    assert is_valid is False
    assert "Unknown action_type" in reason


def test_unknown_zone_rejected(config):
    is_valid, reason = validate_action("set_hvac_temperature", "basement", 22.0, config)
    assert is_valid is False
    assert "Unknown zone" in reason
