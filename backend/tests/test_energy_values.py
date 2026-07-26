import os
import sys
import time
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.simulator.ep_adapter import PyEnergyPlusSimulator

def test_energy_values():
    idf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'simulation', 'expanded.idf'))
    epw_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'simulation', 'weather.epw'))
    
    zones = ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]
    sim = PyEnergyPlusSimulator(idf_path, epw_path, zones)
    
    # We will hook into the read_metrics to print the values
    original_read = sim._read_metrics
    
    values_seen = []
    
    def hooked_read(state):
        metrics = original_read(state)
        
        elec_w = sim.api.exchange.get_variable_value(state, sim.sensor_handles["elec_power"]) if sim.sensor_handles.get("elec_power", -1) != -1 else 0.0
        val = elec_w
        
        values_seen.append(val)
        
        hour = sim.api.exchange.hour(state)
        minute = sim.api.exchange.minutes(state)
        
        zone_temps = {z: metrics["zones"][z]["indoor_temp"] for z in metrics.get("zones", {})}
        
        out_temp = sim.api.exchange.get_variable_value(state, sim.sensor_handles["out_temp"]) if sim.sensor_handles["out_temp"] != -1 else 22.0
            
        day = sim.api.exchange.day_of_year(state)
        kind = sim.api.exchange.kind_of_sim(state)
            
        print(f"Timestep {sim.timestep_counter} (Day {day}, Kind {kind}, Time {hour:02d}:{minute:02d}): out_temp={out_temp:.1f}, power_w={val:.2f}, temps={zone_temps}")
        return metrics
        
    sim._read_metrics = hooked_read
    
    sim.start()
    
    timeout = 30.0
    start = time.time()
    
    # Wait until warmup is complete and we see at least 50 values
    while not sim.warmup_complete or len(values_seen) < 50:
        if time.time() - start > timeout:
            sim.api.runtime.stop_simulation(sim.state)
            pytest.fail(f"Timeout waiting for values. Saw: {len(values_seen)} values")
        time.sleep(0.5)
        
    sim.api.runtime.stop_simulation(sim.state)
    
    non_zero = [v for v in values_seen if v > 0.0]
    print(f"\nCollected {len(values_seen)} values.")
    print(f"Non-zero values: {len(non_zero)}")
    if len(non_zero) == 0:
        pytest.fail("All energy values were 0.0!")
    
