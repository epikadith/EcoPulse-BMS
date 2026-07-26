"""
Building Simulator (Mock EnergyPlus) — 3-zone small office.

Provides realistic synthetic data: diurnal temperature cycles,
workday occupancy patterns, and energy consumption based on HVAC load.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Any

from .comfort import calculate_pmv, calculate_ppd
from .carbon import CarbonTracker


@dataclass
class ZoneState:
    """State for a single building zone."""
    name: str
    indoor_temp: float = 22.0       # °C
    hvac_setpoint: float = 22.0     # °C
    ventilation_rate: float = 50.0  # 0–100%
    shading_position: float = 0.0   # 0–100% (0 = fully open)
    thermal_mass_factor: float = 0.5  # How quickly zone responds to outdoor temp


@dataclass
class BuildingSimulator:
    """
    Mock EnergyPlus simulator for a 3-zone small office building.

    Zones: South (sun-exposed), North (shaded), Core (interior).
    Produces realistic diurnal cycles, occupancy patterns, and energy data.
    """

    # Simulation clock
    sim_time_minutes: float = 0.0  # minutes since midnight (0–1440)
    day: int = 0

    # Outdoor environment
    outdoor_temp: float = 22.0          # °C
    outdoor_humidity: float = 50.0      # %RH
    solar_irradiance: float = 0.0       # W/m²

    # Occupancy
    occupancy_count: int = 0
    max_occupancy: int = 50

    # Energy tracking
    current_energy_kwh: float = 0.0     # instantaneous kW
    cumulative_energy_kwh: float = 0.0  # total kWh consumed
    baseline_energy_kwh: float = 0.0    # baseline (no optimization) cumulative

    # Zones
    zones: dict[str, ZoneState] = field(default_factory=dict)

    # Carbon tracker
    carbon_tracker: CarbonTracker = field(default_factory=CarbonTracker)

    def __post_init__(self):
        if not self.zones:
            self.zones = {
                "south": ZoneState(
                    name="south",
                    indoor_temp=22.0,
                    thermal_mass_factor=0.6,  # More sun exposure
                ),
                "north": ZoneState(
                    name="north",
                    indoor_temp=21.5,
                    thermal_mass_factor=0.4,  # Less sun exposure
                ),
                "core": ZoneState(
                    name="core",
                    indoor_temp=22.0,
                    thermal_mass_factor=0.3,  # Interior, most insulated
                ),
            }

    @property
    def hour_of_day(self) -> float:
        """Current hour of day (0.0–24.0)."""
        return (self.sim_time_minutes % 1440) / 60.0

    def tick(self, timestep_minutes: float = 5.0) -> dict[str, Any]:
        """
        Advance the simulation by the given timestep.

        Updates outdoor conditions, occupancy, zone temperatures,
        and energy consumption.

        Returns the current metrics snapshot.
        """
        self.sim_time_minutes += timestep_minutes
        if self.sim_time_minutes >= 1440:
            self.sim_time_minutes -= 1440
            self.day += 1

        hour = self.hour_of_day

        # --- Outdoor conditions ---
        self._update_outdoor_conditions(hour)

        # --- Occupancy ---
        self._update_occupancy(hour)

        # --- Zone temperatures ---
        total_energy = 0.0
        for zone in self.zones.values():
            zone_energy = self._update_zone(zone, timestep_minutes, hour)
            total_energy += zone_energy

        # Convert to kW (energy per hour)
        self.current_energy_kwh = total_energy
        self.cumulative_energy_kwh += total_energy * (timestep_minutes / 60.0)

        # Baseline: assume fixed 22°C setpoint, 50% ventilation, no shading
        baseline_energy = self._calculate_baseline_energy(hour)
        self.baseline_energy_kwh += baseline_energy * (timestep_minutes / 60.0)

        # Update carbon tracking
        self.carbon_tracker.update(
            energy_kwh=total_energy * (timestep_minutes / 60.0),
            timestep_minutes=timestep_minutes,
        )

        return self.get_metrics()

    def _update_outdoor_conditions(self, hour: float) -> None:
        """
        Simulate outdoor conditions with diurnal patterns.

        Temperature: sinusoidal curve, 15°C night → 32°C peak at 14:00.
        Humidity: inversely correlated with temperature.
        Solar irradiance: bell curve peaking at solar noon (12:00).
        """
        # Temperature: sinusoidal with peak at 14:00 (hour 14)
        # Range: ~15°C (night minimum) to ~32°C (afternoon peak)
        mean_temp = 23.5
        amplitude = 8.5
        # Phase shift: peak at 14:00 → sin peaks at π/2
        phase = 2 * math.pi * (hour - 14.0) / 24.0
        self.outdoor_temp = mean_temp + amplitude * math.sin(-phase + math.pi / 2)

        # Humidity: inversely correlated with temperature
        self.outdoor_humidity = max(30, min(80, 70 - (self.outdoor_temp - 20) * 1.5))

        # Solar irradiance: bell curve, 0 at night, peak ~800 W/m² at noon
        if 6.0 <= hour <= 18.0:
            solar_phase = math.pi * (hour - 6.0) / 12.0
            self.solar_irradiance = 800 * math.sin(solar_phase)
        else:
            self.solar_irradiance = 0.0

    def _update_occupancy(self, hour: float) -> None:
        """
        Simulate occupancy with a workday bell curve.

        Peak occupancy 09:00–17:00, zero overnight.
        """
        if 7.0 <= hour <= 19.0:
            # Bell curve centered at 12:30
            center = 12.5
            sigma = 3.0
            occupancy_fraction = math.exp(-0.5 * ((hour - center) / sigma) ** 2)
            self.occupancy_count = int(self.max_occupancy * occupancy_fraction)
        else:
            self.occupancy_count = 0

    def _update_zone(self, zone: ZoneState, timestep_minutes: float, hour: float) -> float:
        """
        Update a zone's indoor temperature based on HVAC, outdoor conditions, and solar gain.

        Returns instantaneous energy consumption in kW for this zone.
        """
        dt = timestep_minutes / 60.0  # Convert to hours

        # --- Thermal drift toward outdoor temperature ---
        drift_rate = zone.thermal_mass_factor * 0.3  # °C/hour per °C difference
        temp_diff = self.outdoor_temp - zone.indoor_temp
        thermal_drift = drift_rate * temp_diff * dt

        # --- Solar gain (south zone gets more) ---
        solar_gain = 0.0
        if zone.name == "south":
            solar_factor = 0.004  # °C per W/m² per hour
        elif zone.name == "north":
            solar_factor = 0.0015
        else:
            solar_factor = 0.0008

        # Shading reduces solar gain
        shading_reduction = 1.0 - (zone.shading_position / 100.0) * 0.8
        solar_gain = solar_factor * self.solar_irradiance * shading_reduction * dt

        # --- Internal heat gains from occupancy ---
        internal_gain = 0.0
        if self.occupancy_count > 0:
            # ~100W per person, distributed across zones
            heat_per_zone = (self.occupancy_count * 100 / 3) / 1000  # kW
            internal_gain = heat_per_zone * 0.15 * dt  # °C contribution

        # --- HVAC effort ---
        setpoint_error = zone.hvac_setpoint - zone.indoor_temp
        # HVAC correction proportional to error, capped at ±4°C/hr
        hvac_correction = max(-4.0, min(4.0, setpoint_error * 1.5)) * dt

        # --- Update temperature ---
        zone.indoor_temp += thermal_drift + solar_gain + internal_gain + hvac_correction

        # --- Ventilation effect (fresh air brings outdoor temp influence) ---
        vent_factor = (zone.ventilation_rate / 100.0) * 0.1 * dt
        zone.indoor_temp += vent_factor * (self.outdoor_temp - zone.indoor_temp)

        # --- Energy consumption ---
        # Energy = f(|HVAC effort|, ventilation, outdoor-indoor delta)
        hvac_energy = abs(setpoint_error) * 2.0  # kW proportional to effort
        vent_energy = (zone.ventilation_rate / 100.0) * 1.5  # kW for fan
        energy_kw = hvac_energy + vent_energy

        return energy_kw

    def _calculate_baseline_energy(self, hour: float) -> float:
        """Calculate baseline energy assuming fixed 22°C, 50% vent, no shading."""
        total = 0.0
        for zone in self.zones.values():
            setpoint_error = abs(22.0 - zone.indoor_temp)
            hvac_energy = setpoint_error * 2.0
            vent_energy = 0.5 * 1.5  # 50% ventilation
            total += hvac_energy + vent_energy
        return total

    def get_metrics(self) -> dict[str, Any]:
        """Return a complete snapshot of all current metrics."""
        zones_data = {}
        for name, zone in self.zones.items():
            pmv = calculate_pmv(
                air_temp=zone.indoor_temp,
                humidity=self.outdoor_humidity,
                air_velocity=zone.ventilation_rate / 200.0,  # Approximate
            )
            ppd = calculate_ppd(pmv)
            zones_data[name] = {
                "indoor_temp": round(zone.indoor_temp, 2),
                "hvac_setpoint": round(zone.hvac_setpoint, 2),
                "ventilation_rate": round(zone.ventilation_rate, 2),
                "shading_position": round(zone.shading_position, 2),
                "pmv": round(pmv, 3),
                "ppd": round(ppd, 2),
            }

        return {
            "timestamp_minutes": round(self.sim_time_minutes, 1),
            "hour_of_day": round(self.hour_of_day, 2),
            "day": self.day,
            "outdoor": {
                "temperature": round(self.outdoor_temp, 2),
                "humidity": round(self.outdoor_humidity, 2),
                "solar_irradiance": round(self.solar_irradiance, 2),
            },
            "occupancy": self.occupancy_count,
            "zones": zones_data,
            "energy": {
                "current_kw": round(self.current_energy_kwh, 3),
                "cumulative_kwh": round(self.cumulative_energy_kwh, 3),
                "baseline_kwh": round(self.baseline_energy_kwh, 3),
            },
            "carbon": {
                "current_kg_per_h": round(self.carbon_tracker.current_rate, 4),
                "cumulative_kg": round(self.carbon_tracker.cumulative_kg, 4),
            },
        }

    def apply_action(self, zone: str, action_type: str, value: float) -> dict[str, Any]:
        """
        Apply a control action to a zone.

        Args:
            zone: Zone name ("south", "north", or "core")
            action_type: One of "set_hvac_temperature", "adjust_ventilation", "set_shading"
            value: The target value

        Returns:
            Dict with success status and current zone state.

        Raises:
            ValueError: If zone or action_type is invalid.
        """
        if zone not in self.zones:
            raise ValueError(f"Unknown zone: '{zone}'. Valid zones: {list(self.zones.keys())}")

        zone_state = self.zones[zone]

        if action_type == "set_hvac_temperature":
            zone_state.hvac_setpoint = value
        elif action_type == "adjust_ventilation":
            zone_state.ventilation_rate = value
        elif action_type == "set_shading":
            zone_state.shading_position = value
        else:
            raise ValueError(
                f"Unknown action_type: '{action_type}'. "
                f"Valid types: set_hvac_temperature, adjust_ventilation, set_shading"
            )

        return {
            "success": True,
            "zone": zone,
            "action": action_type,
            "value": value,
            "current_state": {
                "indoor_temp": round(zone_state.indoor_temp, 2),
                "hvac_setpoint": round(zone_state.hvac_setpoint, 2),
                "ventilation_rate": round(zone_state.ventilation_rate, 2),
                "shading_position": round(zone_state.shading_position, 2),
            },
        }
