"""
Polars-based data pipeline for the BMS agent.

Structures raw simulator metrics into typed DataFrames for analysis
and produces compact, token-efficient text for LLM prompts.
"""

import polars as pl


def metrics_to_dataframe(metrics: dict) -> pl.DataFrame:
    """
    Convert a raw metrics dict from the simulator into a Polars DataFrame.

    The resulting DataFrame has one row per zone with columns:
    zone, temperature, setpoint, ventilation, shading, pmv, ppd

    Args:
        metrics: The raw dict from BuildingSimulator.get_metrics().

    Returns:
        A Polars DataFrame with per-zone metrics.
    """
    zones_data = metrics.get("zones", {})

    rows = []
    for zone_name, zone_metrics in zones_data.items():
        rows.append({
            "zone": zone_name,
            "temperature": zone_metrics.get("indoor_temp", 0.0),
            "setpoint": zone_metrics.get("hvac_setpoint", 0.0),
            "ventilation": zone_metrics.get("ventilation_rate", 0.0),
            "shading": zone_metrics.get("shading_position", 0.0),
            "pmv": zone_metrics.get("pmv", 0.0),
            "ppd": zone_metrics.get("ppd", 0.0),
        })

    schema = {
        "zone": pl.Utf8,
        "temperature": pl.Float64,
        "setpoint": pl.Float64,
        "ventilation": pl.Float64,
        "shading": pl.Float64,
        "pmv": pl.Float64,
        "ppd": pl.Float64,
    }

    return pl.DataFrame(rows, schema=schema)


def dataframe_to_prompt_text(df: pl.DataFrame, metrics: dict) -> str:
    """
    Convert a zone DataFrame and global metrics into a compact,
    token-efficient text representation for LLM prompting.

    Args:
        df: The per-zone Polars DataFrame.
        metrics: The full raw metrics dict (for global data).

    Returns:
        A compact multi-line string suitable for inclusion in an LLM prompt.
    """
    lines = []

    # Global context
    outdoor = metrics.get("outdoor", {})
    energy = metrics.get("energy", {})
    carbon = metrics.get("carbon", {})
    hour = metrics.get("hour_of_day", 0.0)
    occupancy = metrics.get("occupancy", 0)

    lines.append(f"Time: {hour:.1f}h | Occupancy: {occupancy}")
    lines.append(
        f"Outdoor: {outdoor.get('temperature', 0):.1f}°C, "
        f"{outdoor.get('humidity', 0):.0f}%RH, "
        f"{outdoor.get('solar_irradiance', 0):.0f} W/m²"
    )
    lines.append(
        f"Energy: {energy.get('current_kw', 0):.1f} kW "
        f"(cumulative: {energy.get('cumulative_kwh', 0):.1f} kWh, "
        f"baseline: {energy.get('baseline_kwh', 0):.1f} kWh)"
    )
    lines.append(
        f"Carbon: {carbon.get('current_kg_per_h', 0):.2f} kg/h "
        f"(total: {carbon.get('cumulative_kg', 0):.2f} kg)"
    )

    # Zone summary stats from Polars
    comfort_stats = df.select([
        pl.col("pmv").mean().alias("avg_pmv"),
        pl.col("ppd").mean().alias("avg_ppd"),
        pl.col("temperature").mean().alias("avg_temp"),
    ])
    row = comfort_stats.row(0, named=True)
    lines.append(
        f"Averages — Temp: {row['avg_temp']:.1f}°C, "
        f"PMV: {row['avg_pmv']:.2f}, PPD: {row['avg_ppd']:.1f}%"
    )

    return "\n".join(lines)
