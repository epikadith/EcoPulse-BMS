import os
import sys
import time
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pyenergyplus.api import EnergyPlusAPI

def run():
    api = EnergyPlusAPI()
    state = api.state_manager.new_state()
    
    idf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'simulation', 'expanded.idf'))
    epw_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'simulation', 'weather.epw'))
    out_dir = os.path.dirname(idf_path) + "/ep_output"
    
    cmd_args = ["-w", epw_path, "-d", out_dir, idf_path]
    
    api.runtime.set_console_output_status(state, False)
    
    # Request everything
    api.exchange.request_variable(state, "Site Outdoor Air Drybulb Temperature", "Environment")
    api.exchange.request_variable(state, "Site Outdoor Air Relative Humidity", "Environment")
    
    api.exchange.request_variable(state, "Chiller Electricity Rate", "MAIN CHILLER")
    api.exchange.request_variable(state, "Cooling Tower Fan Electricity Rate", "MAIN TOWER")
    api.exchange.request_variable(state, "Boiler NaturalGas Rate", "MAIN BOILER")
    
    api.exchange.request_variable(state, "Chiller Electricity Rate", "Main Chiller")
    api.exchange.request_variable(state, "Cooling Tower Fan Electricity Rate", "Main Tower")
    api.exchange.request_variable(state, "Boiler NaturalGas Rate", "Main Boiler")
    
    found_vars = []
    
    def on_init(state_ptr):
        if not api.exchange.api_data_fully_ready(state_ptr):
            return
            
        print("API is ready. Checking handles...")
        
        # Check Environment
        h1 = api.exchange.get_variable_handle(state_ptr, "Site Outdoor Air Drybulb Temperature", "Environment")
        h2 = api.exchange.get_variable_handle(state_ptr, "Site Outdoor Air Relative Humidity", "Environment")
        print(f"out_temp (Environment) = {h1}")
        print(f"out_hum (Environment) = {h2}")
        
        # Check uppercase
        h3 = api.exchange.get_variable_handle(state_ptr, "Chiller Electricity Rate", "MAIN CHILLER")
        print(f"chiller (MAIN CHILLER) = {h3}")
        
        # Check proper case
        h4 = api.exchange.get_variable_handle(state_ptr, "Chiller Electricity Rate", "Main Chiller")
        print(f"chiller (Main Chiller) = {h4}")
        
        # Get all variables? We can't directly get all names from API easily, but let's see these.
        
        api.runtime.stop_simulation(state_ptr)
    
    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, on_init)
    
    t = threading.Thread(target=api.runtime.run_energyplus, args=(state, cmd_args))
    t.start()
    t.join()

if __name__ == "__main__":
    run()
