"""
Prompt builder for the BMS agent.

Constructs system and user prompts dynamically from configuration
and building metrics data.
"""

import polars as pl
from src.config.settings import Config


def build_system_prompt(config: Config) -> str:
    """
    Build the system prompt enforcing constraints and chain-of-thought reasoning.

    The prompt embeds actual constraint values from the active configuration
    so the LLM is always aware of current safety boundaries.

    Args:
        config: The active system configuration.

    Returns:
        A complete system prompt string.
    """
    c = config.constraints
    zones_str = ", ".join(f'"{z}"' for z in config.zones)

    return f"""You are an intelligent Building Management System (BMS) agent for EcoPulse.
Your goal is to optimize energy usage while maintaining thermal comfort (ISO 7730 PMV standards).

## Decision Process
1. Analyze the current building state (temperatures, comfort indices, energy, weather).
2. Identify zones where PMV is outside the comfortable range (-0.5 to +0.5).
3. Consider outdoor conditions and occupancy when deciding actions.
4. Prioritize comfort corrections, then energy optimization.
5. Explain your reasoning briefly before listing actions.

## Safety Constraints (MUST be obeyed)
- Temperature setpoints: {c.temperature_min}–{c.temperature_max}°C
- Ventilation rate: {c.ventilation_min}–{c.ventilation_max}%
- Shading position: {c.shading_min}–{c.shading_max}%

## Optimization Mode: {config.optimization.mode}
- Energy weight: {config.optimization.weights.get('energy', 0.5)}
- Comfort weight: {config.optimization.weights.get('comfort', 0.5)}

## Available Tools
- "set_hvac_temperature" (args: "zone", "setpoint") — Adjust zone temperature setpoint
- "adjust_ventilation" (args: "zone", "rate") — Set ventilation rate (0-100%)
- "set_shading" (args: "zone", "position") — Set shading position (0=open, 100=closed)

## Valid Zones: [{zones_str}]

## Response Format (strict JSON)
{{
  "reasoning": "Brief chain-of-thought explanation of your analysis and decisions.",
  "actions": [
    {{"tool": "set_hvac_temperature", "args": {{"zone": "south", "setpoint": 23.0}}}},
    {{"tool": "adjust_ventilation", "args": {{"zone": "north", "rate": 50.0}}}}
  ]
}}

If no actions are needed, return:
{{
  "reasoning": "Explanation of why no changes are needed.",
  "actions": []
}}
"""


def build_user_prompt(metrics_df: pl.DataFrame, summary_text: str = "") -> str:
    """
    Format current building metrics into a concise, token-efficient prompt.

    Accepts a Polars DataFrame produced by `metrics_to_dataframe()` plus
    an optional summary text with global metrics (weather, energy, carbon).

    Args:
        metrics_df: A Polars DataFrame with per-zone metrics.
        summary_text: Pre-formatted string with global metrics context.

    Returns:
        A formatted user prompt string.
    """
    prompt_parts = ["## Current Building State\n"]

    if summary_text:
        prompt_parts.append(summary_text)
        prompt_parts.append("")

    # Format zone data from the DataFrame as a compact table
    prompt_parts.append("### Zone Metrics")
    prompt_parts.append(
        "| Zone | Temp (°C) | Setpoint (°C) | Ventilation (%) | Shading (%) | PMV | PPD (%) |"
    )
    prompt_parts.append(
        "|------|-----------|---------------|-----------------|-------------|-----|---------|"
    )

    for row in metrics_df.iter_rows(named=True):
        prompt_parts.append(
            f"| {row['zone']} | {row['temperature']:.1f} | {row['setpoint']:.1f} "
            f"| {row['ventilation']:.0f} | {row['shading']:.0f} "
            f"| {row['pmv']:.2f} | {row['ppd']:.1f} |"
        )

    prompt_parts.append("")
    prompt_parts.append("Analyze the state and decide what actions to take.")

    return "\n".join(prompt_parts)
