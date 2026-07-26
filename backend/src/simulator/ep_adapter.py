import os
import sys
import threading
import queue
import time
import logging
from typing import Any

# Ensure pyenergyplus is in the path
sys.path.insert(0, '/usr/local/EnergyPlus-26-1-0')
try:
    from pyenergyplus.api import EnergyPlusAPI
except ImportError:
    raise ImportError("pyenergyplus not found. Ensure EnergyPlus v26.1.0 is installed at /usr/local/EnergyPlus-26-1-0")

logger = logging.getLogger("ecopulse.simulator.ep_adapter")

class PyEnergyPlusSimulator:
    def __init__(self, idf_path: str, epw_path: str, zones: list[str]):
        self.idf_path = idf_path
        self.epw_path = epw_path
        self.zones = zones
        
        self.api = EnergyPlusAPI()
        self.state = self.api.state_manager.new_state()
        
        # Queues for synchronization
        # metrics_queue sends the latest metrics out to the async loop
        self.metrics_queue = queue.Queue(maxsize=1)
        # actions_queue receives actions (a list of dicts) from the async loop
        self.actions_queue = queue.Queue(maxsize=1)
        # ui_queue for fast non-blocking frontend updates
        self.ui_queue = queue.Queue(maxsize=10)
        
        self._thread = None
        
        # Data tracking
        self.timestep_counter = 0
        
        # Sensor Handles
        self.sensor_handles = {}
        # Actuator Handles
        self.actuator_handles = {}
        
        # Data tracking
        self.sim_time_minutes = 0.0
        self.day = 0
        self.cumulative_energy_j = 0.0
        self.baseline_energy_kwh = 0.0 # Mock baseline tracking
        
        self.warmup_complete = False

    def start(self):
        """Starts EnergyPlus in a background thread."""
        self._thread = threading.Thread(target=self._run_energyplus, daemon=True)
        self._thread.start()

    def _run_energyplus(self):
        """The blocking EnergyPlus run call."""
        # Register callbacks
        self.api.runtime.callback_begin_zone_timestep_after_init_heat_balance(self.state, self._timestep_callback)
        self.api.runtime.callback_inside_system_iteration_loop(self.state, self._system_iteration_callback)
        
        logger.info(f"Starting EnergyPlus simulation with {self.idf_path}")
        
        # Run E+
        # -d output_dir is useful for debugging
        out_dir = os.path.dirname(self.idf_path) + "/ep_output"
        cmd_args = [
            "-w", self.epw_path,
            "-d", out_dir,
            self.idf_path
        ]
        
        # Temporarily disable standard output printing from E+ to keep console clean
        self.api.runtime.set_console_output_status(self.state, False)
        
        result = self.api.runtime.run_energyplus(self.state, cmd_args)
        if result != 0:
            logger.error(f"EnergyPlus simulation failed with code {result}")
        else:
            logger.info("EnergyPlus simulation completed successfully.")

    def _timestep_callback(self, state):
        """Called by EnergyPlus at each zone timestep."""
        if self.api.exchange.warmup_flag(state):
            return
            
        if not self.warmup_complete:
            logger.info("EnergyPlus warmup complete. Beginning active co-simulation.")
            self.warmup_complete = True
            self._get_handles(state)
            
        # 1. Read Sensors
        metrics = self._read_metrics(state)
        
        self.timestep_counter += 1
        should_trigger = (self.timestep_counter % 30 == 0) or self._check_thresholds(metrics)
        
        if should_trigger:
            # 2. Push to Queue and Wait for Actions
            # We block E+ here until the orchestrator is ready.
            try:
                self.metrics_queue.put(metrics, timeout=600)
            except queue.Full:
                logger.warning("Metrics queue full, dropping frame.")
                return
    
            try:
                actions = self.actions_queue.get(timeout=600) # Wait for LLM
            except queue.Empty:
                logger.warning("Actions queue timeout, proceeding without actions.")
                actions = []
                
            # 3. Apply Actions
            self._apply_actions(state, actions)
        else:
            # 4. Fast path: Just push to UI queue
            try:
                self.ui_queue.put_nowait(metrics)
            except queue.Full:
                pass
                
            # THROTTLE: Sleep for 1.0 second so the frontend isn't bombarded with thousands of timesteps per second
            time.sleep(1.0)
                
    def _check_thresholds(self, metrics: dict) -> bool:
        zones = metrics.get("zones", {})
        for z, data in zones.items():
            t = data.get("indoor_temp", 22.0)
            if t > 24.0 or t < 20.0:
                return True
        return False
        
    def _system_iteration_callback(self, state):
        """Called inside system iteration to apply schedule overrides."""
        if self.api.exchange.warmup_flag(state):
            return
        # If we need to actuate schedules, we do it here. 
        # For now we apply setpoints in the zone timestep callback if they hold.

    def _get_handles(self, state):
        """Get variable and actuator handles."""
        # Environment
        self.sensor_handles["out_temp"] = self.api.exchange.get_variable_handle(state, "Site Outdoor Air Drybulb Temperature", "Environment")
        self.sensor_handles["out_hum"] = self.api.exchange.get_variable_handle(state, "Site Outdoor Air Relative Humidity", "Environment")
        
        # Try to get the facility electricity meter
        self.sensor_handles["hvac_power"] = self.api.exchange.get_meter_handle(state, "Electricity:Facility")
        
        # Zones
        for zone in self.zones:
            zone_upper = zone.upper()
            self.sensor_handles[f"temp_{zone}"] = self.api.exchange.get_variable_handle(state, "Zone Mean Air Temperature", zone_upper)
        
        # Schedule Actuators
        self.actuator_handles["htg_setp"] = self.api.exchange.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", "Htg-SetP-Sch")
        self.actuator_handles["clg_setp"] = self.api.exchange.get_actuator_handle(state, "Schedule:Compact", "Schedule Value", "Clg-SetP-Sch")
        
        # Log any missing handles
        for k, v in self.sensor_handles.items():
            if v == -1:
                logger.error(f"Missing sensor handle for {k}")
        for k, v in self.actuator_handles.items():
            if v == -1:
                logger.error(f"Missing actuator handle for {k}")

    def _read_metrics(self, state) -> dict:
        """Reads current state from E+ and formats it like the old simulator."""
        out_temp = self.api.exchange.get_variable_value(state, self.sensor_handles["out_temp"]) if self.sensor_handles["out_temp"] != -1 else 22.0
        out_hum = self.api.exchange.get_variable_value(state, self.sensor_handles["out_hum"]) if self.sensor_handles["out_hum"] != -1 else 50.0
        
        # Handle meter or fallback
        if self.sensor_handles["hvac_power"] != -1:
            hvac_power_w = self.api.exchange.get_meter_value(state, self.sensor_handles["hvac_power"])
        else:
            hvac_power_w = 0.0
        
        hvac_power_kw = hvac_power_w / 1000.0 if hvac_power_w > 0 else 0.0
        
        time_step = self.api.exchange.zone_time_step_number(state)
        hour = self.api.exchange.hour(state)
        minute = self.api.exchange.minutes(state)
        
        self.sim_time_minutes = hour * 60 + minute
        self.day = self.api.exchange.day_of_year(state)
        
        # Energy tracking
        dt_hours = self.api.exchange.zone_time_step(state) # Fraction of an hour
        self.cumulative_energy_j += hvac_power_w * (dt_hours * 3600)
        cumulative_kwh = self.cumulative_energy_j / 3600000.0
        self.baseline_energy_kwh += 0.5 * dt_hours # Mock baseline for now
        
        zones_data = {}
        from .comfort import calculate_pmv, calculate_ppd
        
        for zone in self.zones:
            handle = self.sensor_handles.get(f"temp_{zone}", -1)
            temp = self.api.exchange.get_variable_value(state, handle) if handle != -1 else 22.0
            pmv = calculate_pmv(air_temp=temp, humidity=out_hum, air_velocity=0.1)
            ppd = calculate_ppd(pmv)
            
            zones_data[zone] = {
                "indoor_temp": round(temp, 2),
                "hvac_setpoint": 22.0, # We'll track this better later
                "ventilation_rate": 50.0,
                "shading_position": 0.0,
                "pmv": round(pmv, 3),
                "ppd": round(ppd, 2),
            }
            
        return {
            "timestamp_minutes": round(self.sim_time_minutes, 1),
            "hour_of_day": round(hour + minute/60.0, 2),
            "day": self.day,
            "outdoor": {
                "temperature": round(out_temp, 2),
                "humidity": round(out_hum, 2),
                "solar_irradiance": 0.0,
            },
            "occupancy": 10, # Mocked
            "zones": zones_data,
            "energy": {
                "current_kw": round(hvac_power_kw, 3),
                "cumulative_kwh": round(cumulative_kwh, 3),
                "baseline_kwh": round(self.baseline_energy_kwh, 3),
            },
            "carbon": {
                "current_kg_per_h": round(hvac_power_kw * 0.4, 4),
                "cumulative_kg": round(cumulative_kwh * 0.4, 4),
            },
        }

    def _apply_actions(self, state, actions: list):
        """Applies a list of actions to E+ actuators."""
        for action in actions:
            if not action.get("success", False):
                continue
                
            zone = action.get("zone")
            a_type = action.get("action")
            val = action.get("value")
            
            if a_type == "set_hvac_temperature":
                # Override the global schedule
                htg = self.actuator_handles.get("htg_setp", -1)
                clg = self.actuator_handles.get("clg_setp", -1)
                if htg != -1:
                    self.api.exchange.set_actuator_value(state, htg, val - 1.0)
                if clg != -1:
                    self.api.exchange.set_actuator_value(state, clg, val + 1.0)
            # Other actions can be wired later

