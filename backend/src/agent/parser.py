"""
LLM response parser for the BMS agent.

Extracts structured tool calls from LLM output, handling malformed
responses gracefully (log warning, return empty list).
"""

import json
import logging
from dataclasses import dataclass

logger = logging.getLogger("ecopulse.agent.parser")

VALID_TOOLS = frozenset([
    "set_hvac_temperature",
    "adjust_ventilation",
    "set_shading",
])


@dataclass
class Action:
    """A single validated action extracted from LLM output."""
    tool: str
    args: dict

    def __post_init__(self):
        if not isinstance(self.args, dict):
            self.args = {}


def parse_llm_response(response: dict) -> list[Action]:
    """
    Parse a structured LLM response into a list of Action objects.

    Expects the response dict to contain an "actions" key with a list
    of tool call dicts, each having "tool" and "args" keys.

    Handles malformed responses gracefully — logs a warning and returns
    an empty action list instead of crashing.

    Args:
        response: The parsed JSON dict from the LLM.

    Returns:
        A list of Action objects. Empty list if response is malformed.
    """
    if not isinstance(response, dict):
        logger.warning("LLM response is not a dict: %s", type(response).__name__)
        return []

    if "error" in response:
        logger.warning("LLM returned an error: %s", response["error"])
        return []

    actions_raw = response.get("actions")
    if actions_raw is None:
        logger.warning("LLM response missing 'actions' key: %s", list(response.keys()))
        return []

    if not isinstance(actions_raw, list):
        logger.warning("LLM 'actions' is not a list: %s", type(actions_raw).__name__)
        return []

    actions = []
    for i, item in enumerate(actions_raw):
        if not isinstance(item, dict):
            logger.warning("Action %d is not a dict, skipping: %s", i, type(item).__name__)
            continue

        tool = item.get("tool")
        if not tool or not isinstance(tool, str):
            logger.warning("Action %d has invalid tool name, skipping", i)
            continue

        if tool not in VALID_TOOLS:
            logger.warning("Action %d has unknown tool '%s', skipping", i, tool)
            continue

        args = item.get("args", {})
        actions.append(Action(tool=tool, args=args))

    return actions


def extract_reasoning(response: dict) -> str:
    """
    Extract the chain-of-thought reasoning from the LLM response.

    Args:
        response: The parsed JSON dict from the LLM.

    Returns:
        The reasoning string, or empty string if not present.
    """
    if not isinstance(response, dict):
        return ""
    return response.get("reasoning", "")
