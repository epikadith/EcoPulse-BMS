"""Tests for the Building Simulator (Mock EnergyPlus)."""

import pytest
from src.simulator.building import BuildingSimulator
from src.simulator.comfort import calculate_pmv, calculate_ppd
from src.simulator.carbon import CarbonTracker


class TestBuildingSimulator:
    """Tests for the core BuildingSimulator class."""

    def test_initialization_creates_three_zones(self):
        sim = BuildingSimulator()
        assert set(sim.zones.keys()) == {"south", "north", "core"}

    def test_tick_advances_time(self):
        sim = BuildingSimulator()
        initial_time = sim.sim_time_minutes
        sim.tick(15)
        assert sim.sim_time_minutes == initial_time + 15

    def test_tick_wraps_day(self):
        sim = BuildingSimulator()
        sim.sim_time_minutes = 1430  # 23:50
        sim.tick(15)
        assert sim.sim_time_minutes == pytest.approx(5.0, abs=1)
        assert sim.day == 1

    def test_tick_changes_temperatures(self):
        sim = BuildingSimulator()
        initial_temps = {
            name: zone.indoor_temp for name, zone in sim.zones.items()
        }
        # Run several ticks to allow temperatures to change
        for _ in range(10):
            sim.tick(15)
        # At least one zone temperature should have changed
        changed = any(
            sim.zones[name].indoor_temp != initial_temps[name]
            for name in sim.zones
        )
        assert changed, "Zone temperatures should change after ticking"

    def test_apply_action_updates_setpoint(self):
        sim = BuildingSimulator()
        result = sim.apply_action("south", "set_hvac_temperature", 23.5)
        assert result["success"] is True
        assert sim.zones["south"].hvac_setpoint == 23.5

    def test_apply_action_updates_ventilation(self):
        sim = BuildingSimulator()
        result = sim.apply_action("north", "adjust_ventilation", 75.0)
        assert result["success"] is True
        assert sim.zones["north"].ventilation_rate == 75.0

    def test_apply_action_updates_shading(self):
        sim = BuildingSimulator()
        result = sim.apply_action("core", "set_shading", 80.0)
        assert result["success"] is True
        assert sim.zones["core"].shading_position == 80.0

    def test_apply_action_invalid_zone_raises(self):
        sim = BuildingSimulator()
        with pytest.raises(ValueError, match="Unknown zone"):
            sim.apply_action("basement", "set_hvac_temperature", 22.0)

    def test_apply_action_invalid_action_raises(self):
        sim = BuildingSimulator()
        with pytest.raises(ValueError, match="Unknown action_type"):
            sim.apply_action("south", "turn_off_lights", 0)

    def test_outdoor_temp_diurnal_pattern(self):
        """Night temperatures should be lower than daytime."""
        sim = BuildingSimulator()

        # Advance to midnight (0:00)
        sim.sim_time_minutes = 0
        sim._update_outdoor_conditions(0.0)
        night_temp = sim.outdoor_temp

        # Advance to 14:00 (peak)
        sim._update_outdoor_conditions(14.0)
        day_temp = sim.outdoor_temp

        assert day_temp > night_temp, (
            f"Daytime temp ({day_temp:.1f}°C) should exceed "
            f"nighttime temp ({night_temp:.1f}°C)"
        )

    def test_occupancy_zero_at_midnight(self):
        sim = BuildingSimulator()
        sim._update_occupancy(0.0)
        assert sim.occupancy_count == 0

    def test_occupancy_positive_at_noon(self):
        sim = BuildingSimulator()
        sim._update_occupancy(12.0)
        assert sim.occupancy_count > 0

    def test_occupancy_zero_late_night(self):
        sim = BuildingSimulator()
        sim._update_occupancy(23.0)
        assert sim.occupancy_count == 0

    def test_energy_increases_with_hvac_load(self):
        """Higher setpoint error should produce more energy consumption."""
        sim1 = BuildingSimulator()
        sim2 = BuildingSimulator()

        # sim1: setpoint close to current temp (low effort)
        sim1.apply_action("south", "set_hvac_temperature", 22.0)
        # sim2: setpoint far from current temp (high effort)
        sim2.apply_action("south", "set_hvac_temperature", 24.0)

        metrics1 = sim1.tick(15)
        metrics2 = sim2.tick(15)

        # sim2 should consume more energy due to larger setpoint error
        assert metrics2["energy"]["current_kw"] >= metrics1["energy"]["current_kw"]

    def test_get_metrics_returns_complete_data(self):
        sim = BuildingSimulator()
        sim.tick(15)
        metrics = sim.get_metrics()

        # Check top-level keys
        assert "timestamp_minutes" in metrics
        assert "hour_of_day" in metrics
        assert "day" in metrics
        assert "outdoor" in metrics
        assert "occupancy" in metrics
        assert "zones" in metrics
        assert "energy" in metrics
        assert "carbon" in metrics

        # Check outdoor data
        assert "temperature" in metrics["outdoor"]
        assert "humidity" in metrics["outdoor"]
        assert "solar_irradiance" in metrics["outdoor"]

        # Check each zone has required fields
        for zone_name in ["south", "north", "core"]:
            zone = metrics["zones"][zone_name]
            assert "indoor_temp" in zone
            assert "hvac_setpoint" in zone
            assert "ventilation_rate" in zone
            assert "shading_position" in zone
            assert "pmv" in zone
            assert "ppd" in zone

        # Check energy fields
        assert "current_kw" in metrics["energy"]
        assert "cumulative_kwh" in metrics["energy"]
        assert "baseline_kwh" in metrics["energy"]

    def test_full_day_simulation(self):
        """Run a full 24-hour simulation and verify stability."""
        sim = BuildingSimulator()
        metrics_list = []
        for _ in range(96):  # 96 * 15min = 24 hours
            metrics = sim.tick(15)
            metrics_list.append(metrics)

        # Should complete without errors
        assert len(metrics_list) == 96
        # Cumulative energy should be positive
        assert metrics_list[-1]["energy"]["cumulative_kwh"] > 0
        # All zone temps should remain in a reasonable range (10–40°C)
        for m in metrics_list:
            for zone in m["zones"].values():
                assert 10.0 <= zone["indoor_temp"] <= 40.0


class TestComfortCalculator:
    """Tests for PMV/PPD comfort calculations."""

    def test_pmv_comfortable_conditions(self):
        """Standard office conditions should yield near-zero PMV."""
        pmv = calculate_pmv(air_temp=22.0, humidity=50.0, air_velocity=0.1)
        assert -1.5 < pmv < 1.5, f"PMV {pmv} is outside comfortable range"

    def test_pmv_hot_conditions(self):
        """Hot environment should produce positive PMV."""
        pmv = calculate_pmv(air_temp=30.0, humidity=60.0, air_velocity=0.1)
        assert pmv > 0, f"PMV should be positive in hot conditions, got {pmv}"

    def test_pmv_cold_conditions(self):
        """Cold environment should produce negative PMV."""
        pmv = calculate_pmv(air_temp=15.0, humidity=40.0, air_velocity=0.1)
        assert pmv < 0, f"PMV should be negative in cold conditions, got {pmv}"

    def test_pmv_clamped_range(self):
        """PMV should be clamped to [-3, 3]."""
        pmv_hot = calculate_pmv(air_temp=40.0, humidity=80.0)
        pmv_cold = calculate_pmv(air_temp=5.0, humidity=20.0)
        assert -3.0 <= pmv_hot <= 3.0
        assert -3.0 <= pmv_cold <= 3.0

    def test_ppd_minimum(self):
        """PPD should never go below 5%."""
        ppd = calculate_ppd(0.0)  # Perfect PMV
        assert ppd == pytest.approx(5.0, abs=0.5)

    def test_ppd_increases_with_pmv_magnitude(self):
        """PPD should increase as PMV moves away from 0."""
        ppd_neutral = calculate_ppd(0.0)
        ppd_warm = calculate_ppd(1.0)
        ppd_hot = calculate_ppd(2.0)
        assert ppd_warm > ppd_neutral
        assert ppd_hot > ppd_warm


class TestCarbonTracker:
    """Tests for carbon emissions tracking."""

    def test_initial_state(self):
        tracker = CarbonTracker()
        assert tracker.cumulative_kg == 0.0
        assert tracker.current_rate == 0.0

    def test_update_accumulates(self):
        tracker = CarbonTracker(emission_factor=0.4)
        tracker.update(energy_kwh=10.0, timestep_minutes=60)
        assert tracker.cumulative_kg == pytest.approx(4.0)  # 10 * 0.4
        assert tracker.current_rate == pytest.approx(4.0)   # 4 kg in 1 hour

    def test_cumulative_increases(self):
        tracker = CarbonTracker(emission_factor=0.5)
        tracker.update(energy_kwh=2.0, timestep_minutes=30)
        first = tracker.cumulative_kg
        tracker.update(energy_kwh=3.0, timestep_minutes=30)
        assert tracker.cumulative_kg > first

    def test_carbon_scales_with_energy(self):
        """Higher energy should produce more carbon."""
        t1 = CarbonTracker(emission_factor=0.4)
        t2 = CarbonTracker(emission_factor=0.4)
        t1.update(energy_kwh=5.0, timestep_minutes=60)
        t2.update(energy_kwh=10.0, timestep_minutes=60)
        assert t2.cumulative_kg > t1.cumulative_kg

    def test_reset(self):
        tracker = CarbonTracker()
        tracker.update(energy_kwh=10.0, timestep_minutes=60)
        tracker.reset()
        assert tracker.cumulative_kg == 0.0
        assert tracker.current_rate == 0.0
