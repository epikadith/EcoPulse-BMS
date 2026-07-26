import os
import sys
import time
import pytest
import threading

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.simulator.ep_adapter import PyEnergyPlusSimulator

def test_energyplus_handles_initialization():
    """
    Spins up the EnergyPlus simulator in isolation to verify that all
    API variables (sensors and actuators) are successfully tracked and fetched
    without returning -1.
    """
    idf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'simulation', 'expanded.idf'))
    epw_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'simulation', 'weather.epw'))
    
    # Initialize the simulator with correct IDF zones
    zones = ["SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"]
    sim = PyEnergyPlusSimulator(idf_path, epw_path, zones)
    sim.start()
    
    timeout = 20.0
    start = time.time()
    
    # Wait until warmup is complete and the handles are queried
    while not sim.warmup_complete:
        if time.time() - start > timeout:
            pytest.fail("EnergyPlus simulation took too long to warmup.")
        time.sleep(0.5)
        
    # Give the thread a tiny bit of extra time to finish the _get_handles execution
    time.sleep(1.0)
    
    missing_sensors = []
    missing_actuators = []
    
    for k, v in sim.sensor_handles.items():
        if v == -1:
            missing_sensors.append(k)
            
    for k, v in sim.actuator_handles.items():
        if v == -1:
            missing_actuators.append(k)
            
    # Stop the simulation cleanly if possible
    sim.api.runtime.stop_simulation(sim.state)
            
    # Assert there are no missing handles
    assert len(missing_sensors) == 0, f"Missing sensor handles: {missing_sensors}"
    assert len(missing_actuators) == 0, f"Missing actuator handles: {missing_actuators}"
