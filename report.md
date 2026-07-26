# System Architecture Document

## Overview
This document outlines the system architecture for **EcoPulse**, an AI-driven closed-loop Building Management System built for the Honeywell Hackathon. The system integrates the EnergyPlus physics engine with a local large language model (LLM) via a Model Context Protocol (MCP) interface to dynamically control HVAC operations.

## 1. Tool-Calling Architecture
We utilize a decentralized tool-calling architecture to bridge the semantic decision-making of the LLM with the deterministic physics of EnergyPlus. 
- **Model Context Protocol (MCP):** The backend exposes a custom MCP server containing tools that read and write directly to the EnergyPlus API instance (e.g., `get_zone_status`, `set_heating_setpoint`, `set_cooling_setpoint`).
- **Co-Simulation Hook:** We leverage the `pyenergyplus` API's callback system to pause the simulation at every zone timestep. When paused, the Python environment executes the tool calls initiated by the LLM and injects the new actuator values into the running memory state of EnergyPlus before resuming.

## 2. Prompt Engineering Strategies
To ensure the LLM outputs safe and consistent control actions, we rely on the following prompt engineering strategies:
- **State-Contextual Prompts:** The prompt is dynamically injected with the exact current state of the building (indoor temperatures, PMV indices, outdoor dry-bulb temperature, and current setpoints) rather than just a generalized task description.
- **Strict Bounding Constraints:** The system prompt forces the LLM to prioritize human thermal comfort (maintaining PMV between -0.5 and +0.5) while minimizing energy consumption. 
- **Explainability:** The LLM is instructed to briefly reason its decision before executing a tool call, ensuring transparency in *why* a particular HVAC unit was turned on or adjusted.

## 3. Prompt Latency Management
Calling a local LLM at every 15-minute timestep across a full year of simulation would introduce massive latency and bottleneck the system. We manage latency using a **Reactive Control Loop**:
- **Threshold Triggers:** The Python orchestrator monitors the PMV and temperature of every zone natively in code.
- **Event-Driven LLM Invocation:** The LLM is *only* queried when a zone breaches a predefined comfort threshold (e.g., temperature drops below 20°C or PMV falls out of the comfortable range). 
- **Scheduled Sleep:** During periods where the building is comfortable, the agent remains dormant, allowing EnergyPlus to run at maximum computational speed.

## 4. Technical Approach to Handling Lengthy Simulation Logs
EnergyPlus generates incredibly verbose `.err`, `.eso`, and `.rdd` files. Sending these directly to an LLM would blow up the context window.
- **In-Memory Streaming:** Instead of relying on post-simulation log files, we scrape the critical variables (like `Facility Total Purchased Electricity Rate` and Zone Mean Air Temperatures) directly from the running memory (RAM) of the simulator using the `pyenergyplus` API.
- **Rolling Window Context:** We maintain a short, rolling window of recent zone states in the Python memory. Only this highly condensed, immediate snapshot is sent to the LLM during a query, completely bypassing the need to parse raw `.err` or `.eso` files mid-simulation.
