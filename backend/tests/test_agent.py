"""Tests for the LLM Agent Module — prompt, parser, data pipeline, and orchestrator."""

import pytest
import json
from unittest.mock import patch
import polars as pl

from src.agent.llm import query_llm
from src.agent.loop import run_agent_step, AgentOrchestrator
from src.agent.prompt import build_system_prompt, build_user_prompt
from src.agent.parser import parse_llm_response, extract_reasoning, Action
from src.agent.data_pipeline import metrics_to_dataframe, dataframe_to_prompt_text
from src.config.settings import Config
from src.simulator.building import BuildingSimulator
from src.mcp_server.server import create_mcp_server


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def config():
    return Config()

@pytest.fixture
def simulator():
    sim = BuildingSimulator()
    sim.tick(15)  # Advance once so metrics are non-trivial
    return sim

@pytest.fixture
def mcp_server(config):
    sim = BuildingSimulator()
    return create_mcp_server(sim, config)

@pytest.fixture
def sample_metrics(simulator):
    return simulator.get_metrics()


# ──────────────────────────────────────────────────────────────
# Prompt building tests (6.2)
# ──────────────────────────────────────────────────────────────

def test_system_prompt_contains_constraints(config):
    prompt = build_system_prompt(config)
    assert "20.0" in prompt  # temperature_min
    assert "24.0" in prompt  # temperature_max
    assert "100.0" in prompt  # ventilation_max / shading_max

def test_system_prompt_contains_zones(config):
    prompt = build_system_prompt(config)
    assert '"south"' in prompt
    assert '"north"' in prompt
    assert '"core"' in prompt

def test_system_prompt_contains_optimization_mode(config):
    prompt = build_system_prompt(config)
    assert "balanced" in prompt

def test_user_prompt_contains_zone_table(sample_metrics):
    df = metrics_to_dataframe(sample_metrics)
    summary = dataframe_to_prompt_text(df, sample_metrics)
    prompt = build_user_prompt(df, summary)
    assert "Zone" in prompt
    assert "south" in prompt
    assert "PMV" in prompt


# ──────────────────────────────────────────────────────────────
# Parser tests (6.3)
# ──────────────────────────────────────────────────────────────

def test_parse_valid_actions():
    response = {
        "reasoning": "Zone south is too warm.",
        "actions": [
            {"tool": "set_hvac_temperature", "args": {"zone": "south", "setpoint": 22.0}},
            {"tool": "adjust_ventilation", "args": {"zone": "north", "rate": 60.0}},
        ]
    }
    actions = parse_llm_response(response)
    assert len(actions) == 2
    assert actions[0].tool == "set_hvac_temperature"
    assert actions[0].args["zone"] == "south"
    assert actions[1].tool == "adjust_ventilation"

def test_parse_malformed_response_returns_empty():
    assert parse_llm_response("not a dict") == []
    assert parse_llm_response(None) == []
    assert parse_llm_response(42) == []

def test_parse_missing_actions_key_returns_empty():
    assert parse_llm_response({"reasoning": "nothing"}) == []

def test_parse_error_response_returns_empty():
    assert parse_llm_response({"error": "LLM failed"}) == []

def test_parse_skips_unknown_tools():
    response = {
        "actions": [
            {"tool": "activate_fire_alarm", "args": {}},
            {"tool": "set_shading", "args": {"zone": "core", "position": 50.0}},
        ]
    }
    actions = parse_llm_response(response)
    assert len(actions) == 1
    assert actions[0].tool == "set_shading"

def test_parse_empty_actions():
    response = {"reasoning": "All good", "actions": []}
    actions = parse_llm_response(response)
    assert actions == []

def test_extract_reasoning_present():
    assert extract_reasoning({"reasoning": "It's warm"}) == "It's warm"

def test_extract_reasoning_missing():
    assert extract_reasoning({"actions": []}) == ""
    assert extract_reasoning("invalid") == ""


# ──────────────────────────────────────────────────────────────
# Data pipeline tests (6.5)
# ──────────────────────────────────────────────────────────────

def test_metrics_to_dataframe_returns_valid_df(sample_metrics):
    df = metrics_to_dataframe(sample_metrics)
    assert isinstance(df, pl.DataFrame)
    assert len(df) == 3  # 3 zones

def test_metrics_to_dataframe_has_expected_columns(sample_metrics):
    df = metrics_to_dataframe(sample_metrics)
    expected = {"zone", "temperature", "setpoint", "ventilation", "shading", "pmv", "ppd"}
    assert set(df.columns) == expected

def test_metrics_to_dataframe_zone_names(sample_metrics):
    df = metrics_to_dataframe(sample_metrics)
    zones = set(df["zone"].to_list())
    assert zones == {"south", "north", "core"}

def test_dataframe_to_prompt_text_contains_context(sample_metrics):
    df = metrics_to_dataframe(sample_metrics)
    text = dataframe_to_prompt_text(df, sample_metrics)
    assert "Outdoor:" in text
    assert "Energy:" in text
    assert "Carbon:" in text
    assert "Averages" in text


# ──────────────────────────────────────────────────────────────
# LLM query tests (existing)
# ──────────────────────────────────────────────────────────────

def test_query_llm_parses_json_successfully(config):
    mock_response = {
        "message": {
            "content": '{"actions": [{"tool": "set_hvac_temperature", "args": {"zone": "south", "setpoint": 22.0}}]}'
        }
    }
    with patch("src.agent.llm.ollama.chat", return_value=mock_response):
        result = query_llm('{"status": "ok"}', "system prompt", config)
        assert "error" not in result
        assert len(result["actions"]) == 1
        assert result["actions"][0]["tool"] == "set_hvac_temperature"

def test_query_llm_handles_invalid_json(config):
    mock_response = {
        "message": {
            "content": 'This is not valid JSON'
        }
    }
    with patch("src.agent.llm.ollama.chat", return_value=mock_response):
        result = query_llm('{"status": "ok"}', "system prompt", config)
        assert "error" in result
        assert result["error"] == "Failed to parse JSON"


# ──────────────────────────────────────────────────────────────
# Orchestrator / run_agent_step tests (6.4/6.6)
# ──────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_run_agent_step_executes_actions(mcp_server, config):
    mock_response = {
        "reasoning": "Adjusting for comfort.",
        "actions": [
            {"tool": "set_hvac_temperature", "args": {"zone": "north", "setpoint": 23.5}},
            {"tool": "set_shading", "args": {"zone": "core", "position": 50.0}}
        ]
    }
    with patch("src.agent.loop.query_llm", return_value=mock_response):
        result = await run_agent_step(mcp_server, config)

        assert result["success"] is True
        assert len(result["actions_executed"]) == 2

        action1 = result["actions_executed"][0]
        assert action1["tool"] == "set_hvac_temperature"
        res1_dict = json.loads(action1["result"])
        assert res1_dict["success"] is True

        action2 = result["actions_executed"][1]
        assert action2["tool"] == "set_shading"
        res2_dict = json.loads(action2["result"])
        assert res2_dict["success"] is True

@pytest.mark.anyio
async def test_run_agent_step_handles_invalid_tool(mcp_server, config):
    """Unknown tools should be filtered out by the parser, not crash."""
    mock_response = {
        "actions": [
            {"tool": "activate_fire_alarm", "args": {}}
        ]
    }
    with patch("src.agent.loop.query_llm", return_value=mock_response):
        result = await run_agent_step(mcp_server, config)

        assert result["success"] is True
        # Parser filters unknown tools, so no actions executed
        assert len(result["actions_executed"]) == 0

@pytest.mark.anyio
async def test_run_agent_step_handles_llm_error(mcp_server, config):
    mock_response = {"error": "LLM failed"}
    with patch("src.agent.loop.query_llm", return_value=mock_response):
        result = await run_agent_step(mcp_server, config)

        assert result["success"] is False
        assert result["error"] == "LLM failed"

@pytest.mark.anyio
async def test_orchestrator_step_with_mocked_llm(config):
    """End-to-end mock cycle: orchestrator reads state, calls LLM, executes actions."""
    sim = BuildingSimulator()
    mcp = create_mcp_server(sim, config)
    orchestrator = AgentOrchestrator(mcp, sim, config)

    mock_response = {
        "reasoning": "South zone is slightly warm; lowering setpoint.",
        "actions": [
            {"tool": "set_hvac_temperature", "args": {"zone": "south", "setpoint": 21.5}}
        ]
    }
    with patch("src.agent.loop.query_llm", return_value=mock_response):
        result = await orchestrator.run_step()

    assert result["success"] is True
    assert result["reasoning"] == "South zone is slightly warm; lowering setpoint."
    assert len(result["actions_executed"]) == 1
    assert len(orchestrator.decision_log) == 1
    assert sim.zones["south"].hvac_setpoint == 21.5

@pytest.mark.anyio
async def test_orchestrator_threshold_detection(config):
    """Verify threshold detection triggers when temperature crosses bounds."""
    sim = BuildingSimulator()
    mcp = create_mcp_server(sim, config)
    orchestrator = AgentOrchestrator(mcp, sim, config)

    # Force a zone temperature out of bounds
    sim.zones["south"].indoor_temp = 25.5  # Above 24.0 threshold
    metrics = sim.get_metrics()

    assert orchestrator._check_thresholds(metrics) is True

    # Reset to within bounds
    sim.zones["south"].indoor_temp = 22.0
    metrics = sim.get_metrics()

    assert orchestrator._check_thresholds(metrics) is False
