# EcoPulse-MCP — Task Breakdown

> **Project:** AI-Powered Autonomous Smart Building Optimization  
> **Goal:** Closed-loop BMS — Simulation → LLM Reasoning → Control Action → Visualization  
> **Status Legend:** `[ ]` TODO · `[/]` In Progress · `[x]` Completed

---

## Phase 1: Project Scaffolding & Environment Setup

Set up the monorepo structure, Python backend via `uv`, and Vue.js frontend via Vite/npm.

### Tasks

- [x] **1.1** Initialize Git repo with `.gitignore` (Python, Node.js, EnergyPlus artifacts, `uv` lockfiles, `node_modules/`, `.venv/`)
- [x] **1.2** Create monorepo directory structure:
  ```
  backend/
    src/
      simulator/
      mcp_server/
      agent/
      websocket_server/
      config/
      validation/
    tests/
  frontend/
    src/
      components/
      composables/
      views/
  config/
    default.json
  ```
- [x] **1.3** Initialize Python project in `backend/` using `uv init`
- [x] **1.4** Add core Python dependencies via `uv add`:
  - `polars`
  - `ollama`
  - `mcp`
  - `websockets`
  - `pytest` (dev dependency: `uv add --dev pytest`)
- [x] **1.5** Initialize Vue.js frontend in `frontend/` using Vite:
  - `npm create vite@latest ./ -- --template vue`
  - `npm install`
  - `npm install apexcharts vue3-apexcharts`
- [x] **1.6** Create `config/default.json` with initial configuration skeleton:
  ```json
  {
    "llm": {
      "model": "gemma4:e4b",
      "temperature": 0.3
    },
    "optimization": {
      "mode": "balanced",
      "weights": { "energy": 0.5, "comfort": 0.5 }
    },
    "control_loop": {
      "interval_seconds": 30,
      "thresholds": {
        "temperature_high": 24.0,
        "temperature_low": 20.0
      }
    },
    "zones": ["south", "north", "core"],
    "constraints": {
      "temperature_min": 20.0,
      "temperature_max": 24.0,
      "ventilation_min": 0,
      "ventilation_max": 100,
      "shading_min": 0,
      "shading_max": 100
    },
    "websocket": {
      "host": "0.0.0.0",
      "port": 8765
    }
  }
  ```

### Phase 1 Verification

| # | Test | Command | Pass Criteria |
|---|------|---------|---------------|
| 1 | Python env activates | `cd backend && uv run python -c "import polars; import ollama; print('OK')"` | Prints `OK` |
| 2 | Pytest discoverable | `cd backend && uv run pytest --co -q` | Exits 0 (no errors, 0 tests collected is fine) |
| 3 | Frontend dev server starts | `cd frontend && npm run dev` | Vite dev server starts on localhost |
| 4 | Config loads | `cd backend && uv run python -c "import json; c=json.load(open('../config/default.json')); assert c['llm']['model']=='gemma4:e4b'; print('OK')"` | Prints `OK` |

### Phase 1 Status: `[x]`

---

## Phase 2: Building Simulator (Mock EnergyPlus)

Build a realistic 3-zone office simulator that produces diurnal temperature cycles, workday occupancy patterns, and energy consumption based on HVAC load.

### Tasks

- [x] **2.1** Create `backend/src/simulator/__init__.py`
- [x] **2.2** Implement `backend/src/simulator/building.py` — `BuildingSimulator` class:
  - 3 zones: South, North, Core
  - Per-zone state: indoor temperature, HVAC setpoint, ventilation rate, shading position
  - Global state: outdoor temperature, humidity, solar irradiance, occupancy count
  - `tick(timestep_minutes)` method advancing the simulation clock:
    - Outdoor temp follows a sinusoidal diurnal curve (e.g., 15°C night → 32°C peak at 14:00)
    - Occupancy follows a workday bell curve (peak 09:00–17:00, zero overnight)
    - Indoor temps drift toward outdoor temp, countered by HVAC effort
    - Energy consumption = f(HVAC load, ventilation, outdoor-indoor delta)
  - `get_metrics()` → returns a dict of all current readings
  - `apply_action(zone, action_type, value)` → applies a control action
- [x] **2.3** Implement `backend/src/simulator/comfort.py` — PMV/PPD comfort index calculator:
  - Simplified Fanger PMV model based on indoor temp, humidity, air velocity
  - PPD derived from PMV
- [x] **2.4** Implement `backend/src/simulator/carbon.py` — carbon footprint estimator:
  - kgCO2/kWh factor (configurable, default ~0.4 for mixed grid)
  - Returns instantaneous and cumulative carbon emissions
- [x] **2.5** Write unit tests in `backend/tests/test_simulator.py`:
  - Verify `tick()` advances time and changes temperatures
  - Verify `apply_action()` correctly updates zone setpoints
  - Verify outdoor temperature follows a diurnal pattern (night < day)
  - Verify occupancy is 0 at midnight, >0 at noon
  - Verify energy increases when HVAC load increases
  - Verify PMV is within expected range for normal indoor conditions
  - Verify carbon emissions scale with energy usage

### Phase 2 Verification

| # | Test | Command | Pass Criteria |
|---|------|---------|---------------|
| 1 | All simulator tests pass | `cd backend && uv run pytest tests/test_simulator.py -v` | All tests green |
| 2 | Simulator produces realistic data | `cd backend && uv run python -c "from src.simulator.building import BuildingSimulator; s=BuildingSimulator(); [s.tick(15) for _ in range(96)]; m=s.get_metrics(); print(m)"` | Prints metrics dict with realistic values over a 24h cycle |

### Phase 2 Status: `[x]`

---

## Phase 3: Configuration Module

A clean config loader that reads `default.json`, applies defaults, and exposes typed configuration.

### Tasks

- [x] **3.1** Create `backend/src/config/__init__.py`
- [x] **3.2** Implement `backend/src/config/settings.py`:
  - `load_config(path)` → reads JSON, validates required keys, applies defaults
  - Expose as a singleton or importable config object
  - Support environment variable overrides for key fields (e.g., `ECOPULSE_LLM_MODEL`)
- [x] **3.3** Write unit tests in `backend/tests/test_config.py`:
  - Valid config loads correctly
  - Missing optional keys get defaults
  - Invalid config (e.g., missing `zones`) raises descriptive error

### Phase 3 Verification

| # | Test | Command | Pass Criteria |
|---|------|---------|---------------|
| 1 | Config tests pass | `cd backend && uv run pytest tests/test_config.py -v` | All tests green |

### Phase 3 Status: `[x]`

---

## Phase 4: Validation Layer

Standalone module that enforces hard safety constraints on every LLM-generated command before execution.

### Tasks

- [x] **4.1** Create `backend/src/validation/__init__.py`
- [x] **4.2** Implement `backend/src/validation/validator.py`:
  - `validate_action(action_type, zone, value, config) → (bool, str)`
  - Rules loaded from config constraints:
    - Temperature setpoints: 20–24°C
    - Ventilation rate: 0–100%
    - Shading position: 0–100%
  - Returns `(True, "")` on pass, `(False, "reason")` on fail
- [x] **4.3** Write unit tests in `backend/tests/test_validation.py`:
  - Valid setpoint (22°C) → passes
  - Out-of-range setpoint (18°C) → rejected with message
  - Out-of-range setpoint (26°C) → rejected with message
  - Ventilation at -5% → rejected
  - Ventilation at 101% → rejected
  - Shading at 50% → passes
  - Unknown action type → rejected
  - Unknown zone → rejected

### Phase 4 Verification

| # | Test | Command | Pass Criteria |
|---|------|---------|---------------|
| 1 | Validation tests pass | `cd backend && uv run pytest tests/test_validation.py -v` | All tests green |
| 2 | Edge cases covered | Check test count ≥ 8 | At least 8 test cases |

### Phase 4 Status: `[x]`

---

## Phase 5: MCP Server

Expose the simulator controls as MCP tools that the LLM can invoke.

### Tasks

- [x] **5.1** Create `backend/src/mcp_server/__init__.py`
- [x] **5.2** Implement `backend/src/mcp_server/server.py`:
  - Initialize the MCP server using the `mcp` Python SDK
  - Register tools with JSON schemas:
    - `get_building_status()` → returns full metrics snapshot
    - `set_hvac_temperature(zone: str, setpoint: float)` → validated, then applied
    - `adjust_ventilation(zone: str, rate: float)` → validated, then applied
    - `set_shading(zone: str, position: float)` → validated, then applied
  - Each tool invocation runs through the validation layer before calling the simulator
  - Return structured JSON responses (success/failure + data)
- [x] **5.3** Write unit tests in `backend/tests/test_mcp_server.py`:
  - `get_building_status` returns complete metrics
  - `set_hvac_temperature("south", 22.0)` succeeds
  - `set_hvac_temperature("south", 30.0)` rejected by validation
  - `adjust_ventilation("north", 50)` succeeds
  - `set_shading("core", 75)` succeeds
  - Invalid zone name is rejected

### Phase 5 Verification

| # | Test | Command | Pass Criteria |
|---|------|---------|---------------|
| 1 | MCP server tests pass | `cd backend && uv run pytest tests/test_mcp_server.py -v` | All tests green |
| 2 | Tools are registered | Verify tool list includes all 4 tools | 4 tools registered |

### Phase 5 Status: `[x]`

---

## Phase 6: Agent / Orchestrator & Ollama Integration

The core control loop: read state → prompt LLM → parse response → validate → execute.

### Tasks

- [x] **6.1** Create `backend/src/agent/__init__.py`
- [x] **6.2** Implement `backend/src/agent/prompt.py`:
  - `build_system_prompt(config)` → returns the system prompt enforcing constraints and chain-of-thought
  - `build_user_prompt(metrics_df: polars.DataFrame)` → formats current metrics into a concise prompt
- [x] **6.3** Implement `backend/src/agent/parser.py`:
  - `parse_llm_response(response: str) → list[Action]`
  - Extract structured tool calls from LLM output (JSON or function-call format)
  - Handle malformed responses gracefully (log warning, skip cycle)
- [x] **6.4** Implement `backend/src/agent/orchestrator.py`:
  - `AgentOrchestrator` class:
    - Configurable fixed-interval loop (default 30s)
    - Threshold-triggered reactive loop (temperature crosses bounds)
    - Each cycle:
      1. `get_building_status()` via MCP
      2. Structure into Polars DataFrame
      3. Build prompt
      4. Call Ollama API (`ollama.chat()`)
      5. Parse LLM response into actions
      6. Validate each action
      7. Execute valid actions via MCP tools
      8. Log decision (reasoning + actions) for dashboard
    - Emit events/messages for the WebSocket layer
- [x] **6.5** Implement data structuring with Polars in `backend/src/agent/data_pipeline.py`:
  - `metrics_to_dataframe(metrics: dict) → polars.DataFrame`
  - `dataframe_to_prompt_text(df: polars.DataFrame) → str` (compact, token-efficient format)
- [x] **6.6** Write unit tests in `backend/tests/test_agent.py`:
  - **Prompt building:** Verify system prompt contains safety constraints
  - **Parsing:** Verify valid JSON tool calls are parsed correctly
  - **Parsing:** Verify malformed response returns empty action list (no crash)
  - **Orchestrator (mocked LLM):** Mock Ollama to return a known response. Verify the orchestrator reads state, calls LLM, and executes the parsed actions.
  - **Data pipeline:** Verify `metrics_to_dataframe` returns a valid Polars DataFrame with expected columns

### Phase 6 Verification

| # | Test | Command | Pass Criteria |
|---|------|---------|---------------|
| 1 | Agent tests pass | `cd backend && uv run pytest tests/test_agent.py -v` | All tests green |
| 2 | End-to-end mock cycle | Run orchestrator with mocked LLM for 1 cycle | Completes without error, produces a decision log entry |
| 3 | Polars integration | Verify DataFrame has columns: `zone`, `temperature`, `setpoint`, `occupancy`, etc. | DataFrame schema matches expectations |

### Phase 6 Status: `[x]`

---

## Phase 7: WebSocket Server

Lightweight async server that pushes real-time data to the frontend dashboard.

### Tasks

- [x] **7.1** Create `backend/src/websocket_server/__init__.py`
- [x] **7.2** Implement `backend/src/websocket_server/server.py`:
  - Initialize a `websockets` server that broadcasts building metrics and LLM decisions to connected frontend clients
  - Hook it into the main agent loop (or run alongside it via `asyncio.gather`)
- [x] **7.3** Create `backend/src/main.py`:
  - The entry point that ties together config, simulator, mcp server, agent loop, and websocket server
- [x] **7.4 (Optional)** Write a quick script to test the WS connection health, loop status
  - Graceful handling of client connect/disconnect
- [x] **7.5** Write integration test in `backend/tests/test_websocket.py`:
  - Start server, connect a test client, send a message, verify receipt
  - Verify message structure matches expected JSON schema

### Phase 7 Verification

| # | Test | Command | Pass Criteria |
|---|------|---------|---------------|
| 1 | WebSocket tests pass | `cd backend && uv run pytest tests/test_websocket.py -v` | All tests green |
| 2 | Manual smoke test | Start backend, connect via `websocat ws://localhost:8765` | Receives JSON messages |

### Phase 7 Status: `[x]`

---

## Phase 8: Backend Integration & Main Entry Point

Wire all backend components together into a runnable application.

### Tasks

- [x] **8.1** Create `backend/src/main.py`:
  - Load config
  - Initialize simulator
  - Initialize MCP server with simulator
  - Initialize agent orchestrator with MCP server + Ollama
  - Start WebSocket server
  - Start agent loop
  - Graceful shutdown on SIGINT
- [x] **8.2** Add a `[project.scripts]` entry in `pyproject.toml` or a run script so the backend starts with `uv run python -m src.main` or similar
- [x] **8.3** Full backend integration test in `backend/tests/test_integration.py`:
  - Mock Ollama, start simulator + MCP + agent + WebSocket
  - Run 3 agent cycles
  - Verify WebSocket client receives ≥ 3 `metrics_update` and ≥ 3 `llm_decision` messages
  - Verify simulator state has changed from initial values

### Phase 8 Verification

| # | Test | Command | Pass Criteria |
|---|------|---------|---------------|
| 1 | Integration test passes | `cd backend && uv run pytest tests/test_integration.py -v` | All tests green |
| 2 | Backend runs standalone | `cd backend && uv run python -m src.main` (with Ollama running) | Starts, runs agent cycles, logs decisions |
| 3 | All backend tests pass | `cd backend && uv run pytest -v` | Full green test suite |

### Phase 8 Status: `[x]`

---

## Phase 9: Frontend Dashboard (Vue.js + ApexCharts)

Build the live monitoring dashboard that connects to the backend WebSocket.

### Tasks

- [x] **9.1** Set up project structure:
  - Create composable `frontend/src/composables/useWebSocket.js` for WebSocket connection management
  - Create a Pinia store or reactive state module for global metrics state
- [x] **9.2** Build dashboard layout in `frontend/src/App.vue`:
  - Responsive grid layout (CSS Grid or Flexbox)
  - Modular panel slots for each widget
- [x] **9.3** Implement `EnergyPanel.vue`:
  - ApexCharts line chart: real-time energy consumption vs. baseline
  - Auto-scrolling time axis
- [x] **9.4** Implement `ComfortPanel.vue`:
  - Current PMV/PPD values per zone
  - Color-coded status indicators (green = comfortable, yellow = marginal, red = out of range)
- [x] **9.5** Implement `ZoneTemperaturePanel.vue`:
  - Per-zone current temperature vs. setpoint
  - ApexCharts bar or gauge chart
- [x] **9.6** Implement `WeatherPanel.vue`:
  - Outdoor temperature, humidity, solar irradiance display
- [x] **9.7** Implement `CarbonPanel.vue`:
  - Instantaneous CO₂ (kg/h) and cumulative total
  - ApexCharts area chart for trend
- [x] **9.8** Implement `HVACStatusPanel.vue`:
  - Table showing per-zone: setpoint, ventilation rate, shading position
- [x] **9.9** Implement `LLMLogPanel.vue`:
  - Scrollable, timestamped log of LLM reasoning and actions
  - Auto-scroll to latest entry
  - Chain-of-thought reasoning prominently displayed
- [x] **9.10** Implement `ConfigPanel.vue` (optional stretch): Skipped for core implementation

### Phase 9 Verification

| # | Test | Command | Pass Criteria |
|---|------|---------|---------------|
| 1 | Frontend builds | `cd frontend && npm run build` | Build succeeds with no errors |
| 2 | Dev server runs | `cd frontend && npm run dev` | Vite serves the app |
| 3 | WebSocket connects | Open dashboard in browser with backend running | Dashboard receives and renders live data |
| 4 | All 7 panels render | Visual inspection | All panels visible with data |
| 5 | Responsive layout | Resize browser window | Panels reflow cleanly |

### Phase 9 Status: `[x]`

---

## Phase 10: End-to-End Integration & Polish

Full system test — backend + frontend running together as a cohesive demo.

### Tasks

- [x] **10.1** Create a startup script `start.sh` that launches backend and frontend together
- [x] **10.2** End-to-end smoke test:
  - Start backend (with Ollama running)
  - Start frontend
  - Verify dashboard displays live data after ~1 minute
  - Verify LLM log shows chain-of-thought reasoning
  - Verify energy chart shows consumption trending
  - Verify zone temperatures respond to LLM adjustments
- [x] **10.3** Polish: error handling, loading states, reconnection logic in frontend
- [x] **10.4** Polish: clean up logging in backend (structured JSON logs)
- [x] **10.5** Write `README.md` with:
  - Project overview
  - Architecture diagram (text or Mermaid)
  - Prerequisites (Python, Node.js, Ollama, uv)
  - Quick-start instructions
  - Screenshot / demo description

### Phase 10 Verification

| # | Test | Command | Pass Criteria |
|---|------|---------|---------------|
| 1 | Full test suite | `cd backend && uv run pytest -v` | All backend tests green |
| 2 | Frontend builds clean | `cd frontend && npm run build` | Zero errors, zero warnings |
| 3 | Demo script works | `bash start.sh` | Both services start, dashboard is live |
| 4 | 5-minute soak test | Let system run for 5 min | No crashes, data flows continuously, LLM makes ≥5 decisions |

### Phase 10 Status: `[x]`

---

## Summary

| Phase | Description | Key Deliverable |
|-------|-------------|-----------------|
| 1 | Project Scaffolding | Monorepo + deps installed |
| 2 | Building Simulator | Realistic 3-zone mock EnergyPlus |
| 3 | Configuration Module | JSON config loader with defaults |
| 4 | Validation Layer | Safety constraint enforcement |
| 5 | MCP Server | LLM-invocable tool interface |
| 6 | Agent / Orchestrator | Core LLM reasoning loop |
| 7 | WebSocket Server | Real-time data push to frontend |
| 8 | Backend Integration | Runnable backend with all modules |
| 9 | Frontend Dashboard | Live Vue.js + ApexCharts UI |
| 10 | End-to-End & Polish | Demo-ready full system |
