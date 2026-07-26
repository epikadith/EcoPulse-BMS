"""
Carbon footprint estimator.

Tracks instantaneous and cumulative CO₂ emissions based on
energy consumption and a configurable grid emission factor.
"""

from dataclasses import dataclass


@dataclass
class CarbonTracker:
    """
    Tracks carbon emissions from building energy usage.

    Uses a grid emission factor (kgCO₂/kWh) to convert
    energy consumption to carbon emissions.
    """

    emission_factor: float = 0.4  # kgCO₂ per kWh (mixed grid default)
    cumulative_kg: float = 0.0    # Total kgCO₂ emitted
    current_rate: float = 0.0     # Current kgCO₂/hour

    def update(self, energy_kwh: float, timestep_minutes: float) -> None:
        """
        Update carbon tracking with new energy consumption data.

        Args:
            energy_kwh: Energy consumed in this timestep (kWh)
            timestep_minutes: Duration of the timestep in minutes
        """
        carbon_kg = energy_kwh * self.emission_factor
        self.cumulative_kg += carbon_kg

        # Current rate in kg/hour
        if timestep_minutes > 0:
            self.current_rate = carbon_kg / (timestep_minutes / 60.0)
        else:
            self.current_rate = 0.0

    def reset(self) -> None:
        """Reset cumulative tracking."""
        self.cumulative_kg = 0.0
        self.current_rate = 0.0
