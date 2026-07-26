"""
PMV/PPD comfort index calculator.

Calibrated empirical PMV model based on Fanger's thermal comfort theory.
PMV ranges from -3 (cold) to +3 (hot), with 0 being neutral/comfortable.
PPD (Predicted Percentage Dissatisfied) is derived from PMV.

This is a numerically stable simplification suitable for real-time BMS use.
"""

import math


def calculate_pmv(
    air_temp: float,
    humidity: float = 50.0,
    air_velocity: float = 0.1,
    mean_radiant_temp: float | None = None,
    metabolic_rate: float = 1.2,  # met (typical office work)
    clothing_insulation: float = 0.7,  # clo (typical business casual)
) -> float:
    """
    Calculate the Predicted Mean Vote (PMV).

    Uses a calibrated empirical model based on Fanger's comfort equation.
    Numerically stable across the full range of indoor conditions.

    Reference neutral points (PMV ≈ 0):
        - 1.2 met, 0.7 clo → ~22.5°C
        - 1.0 met, 1.0 clo → ~23.0°C
        - 1.4 met, 0.5 clo → ~21.5°C

    Args:
        air_temp: Indoor air temperature (°C)
        humidity: Relative humidity (%)
        air_velocity: Air velocity (m/s)
        mean_radiant_temp: Mean radiant temperature (°C). Defaults to air_temp.
        metabolic_rate: Metabolic rate in met units (1 met = 58.2 W/m²)
        clothing_insulation: Clothing insulation in clo units

    Returns:
        PMV value (-3 to +3 scale)
    """
    if mean_radiant_temp is None:
        mean_radiant_temp = air_temp

    # Operative temperature (weighted average of air and radiant temp)
    t_op = 0.5 * air_temp + 0.5 * mean_radiant_temp

    # Neutral (comfort) temperature depends on clothing and activity
    # Calibrated to match Fanger model at standard conditions
    t_neutral = 21.0 + 2.0 * clothing_insulation + 0.5 * (1.0 - metabolic_rate)

    # Base PMV: ~0.45 PMV per °C deviation from neutral
    # Higher metabolic rate increases sensitivity slightly
    sensitivity = 0.40 + 0.05 * metabolic_rate
    pmv = sensitivity * (t_op - t_neutral)

    # Humidity correction: high humidity makes warm conditions feel warmer
    # and cold conditions feel slightly less cold
    humidity_offset = (humidity - 50.0) * 0.008
    if t_op > t_neutral:
        pmv += humidity_offset
    else:
        pmv += humidity_offset * 0.3  # Less effect in cooling

    # Air velocity correction: higher air speed increases heat loss (feels cooler)
    velocity_cooling = max(0.0, air_velocity - 0.05) * 0.8
    pmv -= velocity_cooling

    # Clamp to valid range
    return max(-3.0, min(3.0, round(pmv, 3)))


def calculate_ppd(pmv: float) -> float:
    """
    Calculate the Predicted Percentage Dissatisfied (PPD) from PMV.

    PPD represents the percentage of people who would be thermally
    dissatisfied with the conditions.

    Args:
        pmv: Predicted Mean Vote value

    Returns:
        PPD value (5–100%). Even at PMV=0, PPD is 5% (minimum dissatisfaction).
    """
    ppd = 100.0 - 95.0 * math.exp(-0.03353 * pmv ** 4 - 0.2179 * pmv ** 2)
    return max(5.0, min(100.0, round(ppd, 2)))
