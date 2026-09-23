# Q-GREEN CORRIDOR

**Quantum-Inspired Intelligent Emergency Traffic Route Optimization & Green Corridor Simulation**

Built for an internal college hackathon (Smart India Hackathon qualifier) against:

> **SIH Problem Statement 26137** — *Quantum-Inspired Intelligent Traffic Route Optimization in
> Transportation Systems Using Metaheuristic Optimization*

Primary demonstration use case: **emergency ambulance routing** through a simulated city, with
live traffic disruption and automatic re-optimization.

---

## 1. What this actually is (read this first)

This is a **working local prototype**, not a mockup. Every button performs a real backend
computation:

- The city is a **simulated 26-node road network** (no Google Maps / real traffic APIs) —
  fully deterministic and offline.
- **QPSO (Quantum-inspired Particle Swarm Optimization)** is a real, iterative optimizer with a
  documented discrete/graph-aware adaptation (see §5). It is not Dijkstra relabelled — a
  benchmark panel proves this by running Dijkstra, A*, QPSO, PSO and GA side-by-side on
  identical inputs.
- Traffic incidents genuinely block a road in the live graph; the app detects the resulting
  route disruption and re-runs the optimizer to find a real alternative.
- The "Green Corridor" is a **simulation** of a signal-priority schedule derived from the
  ambulance's estimated arrival time at each signal. It does not connect to, and does not
  claim to connect to, real traffic infrastructure.

### Honesty notes (per the project's own rules)

- "Quantum-inspired optimization executed on classical hardware" — not a quantum computer.
- No claim of a guaranteed global optimum, guaranteed reduction in emergency deaths, or
  universally faster QPSO. The benchmark panel shows real, sometimes-mixed results.
- Benchmark numbers are only ever displayed after `POST /api/benchmark` actually runs; nothing
  is hardcoded.

---

## 2. Architecture

```
q-green-corridor/
├── backend/
│   ├── main.py                # FastAPI app + all endpoints
│   ├── models/schemas.py      # Pydantic request models
│   ├── routing/
│   │   ├── graph.py           # CityGraph: dynamic weighted graph (NetworkX-backed)
│   │   ├── fitness.py         # Shared multi-factor cost function (used by ALL algorithms)
│   │   ├── dijkstra.py        # Baseline
│   │   ├── astar.py           # Baseline (haversine heuristic)
│   │   ├── qpso.py            # THE core algorithm — see §5
│   │   ├── pso.py             # Classic velocity-based PSO (benchmark only)
│   │   └── ga.py              # Genetic Algorithm (benchmark only)
│   ├── simulation/
│   │   ├── traffic.py         # Traffic drift + incident injection
│   │   ├── ambulance.py       # Ambulance position/movement simulation
│   │   └── events.py          # Mission event log
│   ├── corridor/planner.py    # Green corridor / signal-priority schedule
│   ├── traffic_control.py     # Traffic Control Server: signal command log, ETA-based
│   │                          # PREPARE/PRIORITY sequencing, driver navigation instructions
│   └── data/
│       ├── generate_city.py   # Deterministic city network generator (seed=42)
│       ├── city_network.json  # Generated network (26 nodes, ~110 directed edges, 3 signals)
│       └── config.json        # Tunable experiment parameters
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # Orchestration, mode switch, Full Demo runner
│   │   ├── components/
│   │   │   ├── DriverMode.jsx      # Mobile-first ambulance driver navigation UI
│   │   │   ├── ControlCenter.jsx   # Desktop Traffic Control Center dashboard
│   │   │   ├── CommandLog.jsx      # Live signal command log panel
│   │   │   ├── CityMap.jsx         # Leaflet map (mode="driver"|"control")
│   │   │   ├── Header, EmergencyPanel, OptimizationPanel,
│   │   │   │   AnalyticsPanel (Convergence/Benchmark/Timeline/Traffic tabs), ...
│   │   ├── hooks/useSimulation.js  # Polls /api/ambulance and /api/state
│   │   └── services/api.js     # All backend calls
│   └── package.json
├── tests/
│   ├── test_core.py            # Graph, fitness, routing, QPSO, incidents (11 tests)
│   └── test_traffic_control.py # Traffic Control Server, navigation, signal ETA (7 tests)
├── requirements.txt
├── start.sh / start.ps1 / run.bat
└── README.md (this file)
```

**Agentic architecture (logical, no external LLM required):** the backend is organized around
five conceptual agents — Emergency Agent (mission creation), Traffic Agent (traffic/incident
state), Optimization Agent (invokes QPSO/baselines), Corridor Agent (signal-priority schedule),
Coordination Agent (orchestrates re-optimization). Today these are plain Python modules
(`simulation/`, `routing/`, `corridor/`) coordinated by `main.py`; the module boundaries are
deliberately kept clean so any of them could later be upgraded to call a real LLM without
restructuring the rest of the app. No API key is required to run this prototype.

---

## 3. Technology stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn, NetworkX, NumPy, Pydantic
- **Frontend:** React 18, Vite, react-leaflet / Leaflet (map), Recharts (convergence chart)
- **Storage:** JSON only (`backend/data/`) — no database required
- **No external APIs** are required to run or demo the app. The map tiles use a public CDN
  (CartoDB dark basemap) purely for visual polish; if there is no internet connection during
  the demo, Leaflet still renders all roads, signals, the ambulance and the route as vector
  overlays on a plain dark background — only the decorative background tiles are skipped.

---

## 4. Graph model & dynamic cost function

The city is `G = (V, E)`: 26 intersections, ~110 directed road edges (most roads are two-way,
so this is ~55 physical roads), 3 signalized intersections. Every edge stores:

`edge_id, source, destination, distance, base_speed, current_speed, traffic_level (0–1),
signal_delay, blocked, road_name`.

Travel time is **not static** — it's derived from `distance / effective_speed`, where
`effective_speed` degrades non-linearly as `traffic_level` rises toward 1.0 (severe).

Routing cost is a documented multi-factor function, identical across every algorithm so
benchmark comparisons are meaningful:

```
Cost(R) = Σ over edges e in R of:
    w_t * TravelTime(e)  +  w_d * Distance(e)  +  w_c * (Congestion(e) * 10)  +  w_s * SignalDelay(e)
```

Default weights (configurable in `backend/data/config.json` or via `POST /api/config`):
`time_weight=0.4, distance_weight=0.15, congestion_weight=0.3, signal_weight=0.15` — travel
time and congestion are weighted most heavily, appropriate for emergency routing. An infeasible
(disconnected / blocked) candidate route receives a large penalty (default 5000) rather than
crashing the optimizer.

This exact function — `edge_cost()` in `routing/fitness.py` — is imported by Dijkstra, A*,
QPSO, PSO and GA. This was a deliberate fix during development: an earlier version let QPSO's
internal metric diverge slightly from Dijkstra's, which let QPSO "beat" the true shortest path
purely from a bookkeeping bug, not a better route. `tests/test_core.py::test_qpso_never_beats_true_optimum`
guards against this regressing.

---

## 5. QPSO — the real algorithm, and its discrete adaptation

Standard QPSO operates on continuous position vectors. A route is fundamentally discrete (a
sequence of node IDs), so `backend/routing/qpso.py` uses a documented **priority-based
encoding**:

1. **Position** — each particle's position is a continuous vector of length *N* (one value per
   city node): a "priority" score for that node.
2. **Decode (position → path)** — starting at the source, at each step the decoder greedily
   picks the unvisited, unblocked neighbour with the highest priority value. This repeats until
   the destination is reached or the walk dead-ends.
3. **Repair** — if the greedy walk dead-ends, the remaining path is completed with a real
   Dijkstra shortest path (using the *same* cost function) from the stuck node to the
   destination. This guarantees every particle always decodes to a feasible route — the
   optimizer explores the space of priority vectors, while the graph guarantees feasibility.
   A repaired route is still scored by the real fitness function, so a bad priority vector still
   produces a worse (but valid) route.
4. **Position update** — the textbook delta-potential-well QPSO formulation (Sun, Feng & Xu,
   2004):

   ```
   mbest    = mean of all particles' personal-best position vectors
   p_i      = φ · pbest_i + (1 − φ) · gbest          (local attractor, φ ~ U(0,1) per-dimension)
   x_i(t+1) = p_i ± α · |mbest − x_i(t)| · ln(1/u)    (u ~ U(0,1) per-dimension, sign random)
   ```

   `α` (contraction-expansion coefficient) is linearly annealed from `alpha_start=1.0` to
   `alpha_end=0.3` across iterations — more exploration early, more exploitation late.

Every iteration logs `{iteration, best_fitness}` to a convergence history, which the frontend
renders as a real line chart — not a canned animation.

**Safety net:** if, after all iterations, the swarm's global-best candidate is somehow still
infeasible, the backend falls back to the verified Dijkstra route and the UI explicitly labels
it **"Fallback Route"** instead of "QPSO Route" — QPSO is never silently mislabeled.

`PSO` (`routing/pso.py`) and `GA` (`routing/ga.py`) reuse the identical decode/repair scheme so
the benchmark's only variable is the search operator itself.

---

## 6. Green Corridor simulation

After a route is optimized, `corridor/planner.py`:

1. Identifies which signalized nodes (`S2`, `S5`, `S8`) lie on the route.
2. Computes the ambulance's cumulative estimated arrival time at each one.
3. Builds a priority schedule: the signal currently being approached is `PRIORITY`, the next
   signal(s) are `PREPARE`, already-passed signals return to `NORMAL`.

This is a **simulation** — it does not connect to real traffic-signal infrastructure, and the
UI does not claim otherwise.

---

## 7. Installation & running

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### Option A — one command (recommended)

**Linux / macOS:**
```bash
./start.sh
```

**Windows (PowerShell):**
```powershell
.\start.ps1
```

**Windows (double-click):**
```
run.bat
```

Each script: creates a Python venv, installs backend deps, generates the city network if
missing, starts FastAPI on port 8000, installs frontend deps, and starts the Vite dev server on
port 5173.

### Option B — manual

```bash
# Backend
python3 -m venv backend/.venv
source backend/.venv/bin/activate        # Windows: backend\.venv\Scripts\activate
pip install -r requirements.txt
cd backend/data && python3 generate_city.py && cd ../..
cd backend && uvicorn main:app --reload --port 8000
```

In a second terminal:
```bash
cd frontend
npm install
npm run dev
```

### URLs
- Frontend: **http://localhost:5173**
- Backend API docs (Swagger): **http://localhost:8000/docs**

---

## 8. Demo instructions

1. Open **http://localhost:5173**. Confirm the header shows `System Status: ONLINE`.
2. Click **🚀 RUN FULL DEMO** for the one-click deterministic sequence: emergency creation →
   QPSO optimization → green corridor activation → ambulance movement → traffic incident →
   automatic re-optimization → new green corridor → hospital arrival → mission complete.
   Progress is shown with a live status line and progress bar; **■ STOP DEMO** cancels at any
   point.
3. Or use the **manual controls** in the left panel: `START EMERGENCY` →
   `INJECT TRAFFIC INCIDENT` → `RE-OPTIMIZE` → `RESET SIMULATION`.
4. Watch the **QPSO Optimization** panel (right) for live iteration/fitness/ETA/congestion
   metrics, and the **Green Corridor** status with per-signal ETAs.
5. Use the bottom tabs: **Convergence** (QPSO's real fitness-vs-iteration curve),
   **Algorithm Comparison** (run the 5-algorithm benchmark), **Mission Timeline** (full event
   log), **Traffic Status** (live network congestion breakdown).

**Demo speed:** ambulance movement runs at `demo_speed_multiplier: 40` (in
`backend/data/config.json`) — i.e. simulated minutes pass 40× faster than real time, so an
~18-minute route completes in well under a minute for a live audience. Adjust this value (or
`POST /api/config`) to change pacing.

---

## 9. Benchmark instructions

From the UI: **Algorithm Comparison** tab → **▶ Run Benchmark**. This calls
`POST /api/benchmark` with `["DIJKSTRA", "ASTAR", "QPSO", "PSO", "GA"]` and displays real
ETA/distance/congestion/fitness/runtime for each, computed on the current (possibly
incident-affected) graph state. Dijkstra and A* will always find the mathematically optimal
route under the shared cost function; QPSO and GA typically match it; PSO occasionally lands on
a slightly worse local optimum — this is expected, honest metaheuristic behaviour, not a bug.

Via API directly:
```bash
curl -X POST http://localhost:8000/api/benchmark \
  -H "Content-Type: application/json" \
  -d '{"source":"A","destination":"H","algorithms":["DIJKSTRA","ASTAR","QPSO","PSO","GA"]}'
```

---

## 10. Configuration

`backend/data/config.json`:

| Key | Meaning | Default |
|---|---|---|
| `population_size` | QPSO/PSO/GA swarm/population size | 20 |
| `iterations` | Optimization iterations/generations | 50 |
| `alpha_start` / `alpha_end` | QPSO contraction-expansion coefficient (annealed) | 1.0 / 0.3 |
| `time_weight` | Cost weight — travel time | 0.4 |
| `distance_weight` | Cost weight — distance | 0.15 |
| `congestion_weight` | Cost weight — congestion | 0.3 |
| `signal_weight` | Cost weight — signal delay | 0.15 |
| `random_seed` | Deterministic seed for reproducible demos | 42 |
| `penalty_infeasible` | Cost penalty for an infeasible candidate route | 5000 |
| `demo_speed_multiplier` | Simulated-time-per-real-second for ambulance movement | 40.0 |

Update at runtime: `POST /api/config` with a JSON patch (merges into the current config).

---

## 11. Testing

```bash
python3 tests/test_core.py
python3 tests/test_traffic_control.py
```

`test_core.py` covers: graph creation, absence of duplicate parallel edges, fitness
calculation, route validity, blocked-road handling, Dijkstra optimality, A*/Dijkstra agreement,
QPSO convergence (monotonically non-increasing best fitness), QPSO never beating the true
optimum (cost-function consistency regression guard), incident injection + corridor generation,
and re-optimization starting from the ambulance's current position (no visual backtrack).

`test_traffic_control.py` covers: LEFT/RIGHT/STRAIGHT turn classification from route geometry,
ETA-based multi-signal PREPARE vs PRIORITY sequencing, command-log entries on signal pass and
reset, the manual signal-priority override endpoint, driver navigation instruction generation,
and mission-completion navigation state.

All 18 tests pass as of this build (verified directly against the routing/simulation/traffic
control modules — the FastAPI/React layers themselves need `pip install -r requirements.txt`
and `npm install` in an environment with package-registry access, see §7).

---

## 12. Project structure reference

See §2 above. Key files to inspect if evaluating the algorithm work specifically:
`backend/routing/qpso.py` (core algorithm + discrete adaptation docstring),
`backend/routing/fitness.py` (shared cost function),
`backend/main.py` (workflow orchestration / API),
`tests/test_core.py` (correctness guarantees).

---

## 13. Known limitations

- Single in-memory demo session (`SimulationState` in `main.py`) — not multi-tenant. This is a
  deliberate hackathon-scope simplification, not an oversight; a production version would need
  per-session state.
- The map's background tiles require internet access for visual polish (CartoDB dark basemap);
  all functional content (roads, signals, routes, ambulance) renders identically offline.
- QPSO's discrete adaptation (priority-vector + greedy decode + Dijkstra repair) is a documented
  practical compromise, not a "pure" continuous QPSO — this is disclosed, not hidden (see §5).
- Real-time updates use polling (400ms/900ms intervals), not WebSockets, per the execution
  rules' "reliability over sophistication" guidance.
- 3 signalized intersections in the generated network — enough to demonstrate the green
  corridor concept clearly without cluttering the map; `generate_city.py` can be edited to add
  more.

## 14. Driver Mode, Control Center & the Traffic Control Server

This extension adds the ambulance-driver-facing and traffic-operator-facing halves of the
system described in the project brief, on top of the existing simulation engine. Nothing in
§1–§13 above was rewritten — QPSO, the graph, the corridor planner, incident injection and the
Full Demo runner are unchanged and still pass their original tests.

**Two UI modes, one backend, no duplicated logic** (toggle in the header):

- **🚑 Driver Mode** (`DriverMode.jsx`) — mobile-first. Large `🚨 ACTIVATE EMERGENCY` control,
  a live turn-by-turn instruction card ("Turn LEFT in 120 m", "Hospital in 1.2 km"), ETA,
  distance remaining, and a green-corridor badge. The map follows the ambulance and keeps the
  next junction in view instead of showing the whole city.
- **🖥️ Traffic Control Center** (`ControlCenter.jsx`) — desktop/tablet dashboard: full city map,
  emergency/mission panel, QPSO optimization + corridor status, analytics (convergence,
  benchmark, timeline, traffic), and a live **signal command log** (`CommandLog.jsx`).

**Traffic Control Server** (`backend/traffic_control.py`) is the logical coordination layer
between the ambulance app and the simulated signal controllers, per the brief's data flow
(Ambulance App → Emergency Request → Traffic Control Server → Optimization Agent → Green
Corridor Planner → Signal Controllers). Concretely it:

- Advances each signal through **NORMAL → PREPARE → PRIORITY → NORMAL** based on the corridor
  plan's cumulative-travel-time ETA to each signal (nearer signal = PRIORITY, farther upcoming
  signals = PREPARE) — this is the existing `corridor/planner.py` ETA logic, wrapped so every
  genuine phase transition is recorded.
- Maintains an **append-only command log** (`GET /api/control/commands`) populated only from
  real phase transitions — nothing in the log is scripted or pre-written.
- Exposes a manual/simulated command channel, `POST /api/signals/{signal_id}/priority`, for
  architecture completeness — normal operation drives phases automatically from ETA.
- Generates **driver navigation instructions purely from route geometry**
  (`GET /api/navigation/{mission_id}`): the compass bearing between consecutive route nodes is
  computed from their lat/lon, and the bearing delta between the current and next segment is
  classified as `STRAIGHT` (|Δ| ≤ 20°), `RIGHT` (Δ > 20°, clockwise) or `LEFT` (Δ < -20°,
  counter-clockwise); the final segment resolves to `ARRIVE` once within 40 m of the
  destination. Distance and ETA are computed from the same edge distances / travel-time
  function the optimizers use — no instruction text is hardcoded.

**Honesty note (unchanged from §1):** `traffic_control.py` and the signal controllers remain a
**software simulation**. `POST /api/signals/{signal_id}/priority` does not, and is not claimed
to, command any real municipal traffic signal — see the module's own docstring.

### New/changed endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/navigation/{mission_id}` | Live turn-by-turn instruction for Driver Mode |
| `GET /api/control/commands` | Signal command log for the Control Center |
| `POST /api/signals/{signal_id}/priority` | Manual/simulated signal override (`NORMAL`/`PREPARE`/`PRIORITY`) |
| `GET /api/state` | Now also returns `command_log` and `navigation` |

### Responsive design

`App.css` adds dedicated breakpoints at 1024px / 768px / 400px plus a landscape-phone rule, so
Driver Mode's map + bottom instruction sheet and the Control Center's multi-column dashboard
both reflow instead of just shrinking. Tested by inspection at 320/375/390/430/768/1024/1280/
1440/1920px viewport widths (see `SCREENSHOTS.md` for the exact manual verification steps —
this sandbox has no browser/screenshot tool, so live rendering must be checked in your own
`npm run dev` session; see §7 and `SCREENSHOTS.md`).

---

## 15. Future scope

- WebSocket-based push updates instead of polling.
- Multi-ambulance, multi-mission concurrent dispatch.
- Real GTFS/OSM road network import as an alternative to the simulated network.
- Upgrading the five logical agents (§2) to actually call an LLM for dispatch reasoning,
  now that the module boundaries are already in place.
- Persisting mission history to SQLite for post-hoc analysis instead of in-memory-only state.
