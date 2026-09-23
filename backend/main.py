"""
Q-GREEN CORRIDOR backend.

Quantum-Inspired Intelligent Emergency Traffic Route Optimization &
Green Corridor Simulation -- SIH Problem Statement 26137.

Everything here runs locally against a simulated city network with no
external API dependencies. Run with:

    uvicorn main:app --reload --port 8000
"""
import json
import os
import time
import uuid
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models.schemas import (
    StartEmergencyRequest, IncidentRequest, OptimizeRequest,
    BenchmarkRequest, CorridorRequest, SignalCommandRequest,
)
from routing.graph import CityGraph
from routing.dijkstra import run_dijkstra
from routing.astar import run_astar
from routing.qpso import run_qpso
from routing.pso import run_pso
from routing.ga import run_ga
from simulation.ambulance import Ambulance
from simulation.traffic import drift_traffic, inject_incident, pick_incident_edge, traffic_state
from simulation.events import EventLog
from corridor.planner import build_corridor_plan, apply_corridor_state
from traffic_control import TrafficControlServer, build_navigation

APP_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(APP_DIR, "data", "config.json")

app = FastAPI(title="Q-GREEN CORRIDOR API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


WEIGHT_KEYS = ["time_weight", "distance_weight", "congestion_weight", "signal_weight"]


class SimulationState:
    """Single in-memory demo session -- deliberately not multi-tenant; this
    is a hackathon prototype meant to run one live demo at a time."""

    def __init__(self):
        self.config = load_config()
        self.city_graph = CityGraph()
        self.ambulance = Ambulance(base_node=self.city_graph.ambulance_base)
        self.events = EventLog()
        self.missions = {}
        self.active_mission_id = None
        self.corridor_plan = {"active": False, "schedule": []}
        self.benchmark_results = []
        self.convergence_history = []
        self.last_incident = None
        self.rng = random.Random(self.config.get("random_seed", 42))
        self.tcs = TrafficControlServer()

    def weights(self):
        return {k: self.config[k] for k in WEIGHT_KEYS}

    def reset(self):
        self.__init__()


state = SimulationState()


def _mission_or_404(mission_id: str):
    m = state.missions.get(mission_id)
    if not m:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    return m


def _run_optimization(mission, algorithm="QPSO", source_override=None):
    weights = state.weights()
    source = source_override or mission["pickup"]
    if algorithm == "QPSO":
        result = run_qpso(state.city_graph, source, mission["destination"], weights, state.config)
    elif algorithm == "DIJKSTRA":
        result = run_dijkstra(state.city_graph, source, mission["destination"], weights)
    elif algorithm == "ASTAR":
        result = run_astar(state.city_graph, source, mission["destination"], weights)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown algorithm {algorithm}")
    return result


def _activate_corridor_for_route(route):
    state.corridor_plan = build_corridor_plan(state.city_graph, route)
    mission_id = state.active_mission_id or "MISSION"
    state.tcs.sync_signals(state.city_graph, state.corridor_plan, state.ambulance, mission_id)


# --------------------------------------------------------------------- API

@app.get("/api/health")
def health():
    return {"status": "ONLINE", "app": "Q-GREEN CORRIDOR"}


@app.get("/api/network")
def get_network():
    return state.city_graph.to_public_dict()


@app.get("/api/config")
def get_config():
    return state.config


@app.post("/api/config")
def update_config(patch: dict):
    state.config.update(patch)
    return state.config


@app.post("/api/emergency/start")
def start_emergency(req: StartEmergencyRequest):
    mission_id = f"MSN-{uuid.uuid4().hex[:6].upper()}"
    mission = {
        "mission_id": mission_id,
        "severity": req.severity,
        "pickup": req.pickup,
        "destination": req.destination,
        "assigned_ambulance": req.ambulance_id,
        "status": "CREATED",
        "route": [],
        "eta_min": None,
        "created_at": time.time(),
    }
    state.missions[mission_id] = mission
    state.active_mission_id = mission_id
    state.events.log("🚨", f"Emergency created ({req.severity}) — mission {mission_id}")

    # auto-assign ambulance
    state.ambulance = Ambulance(ambulance_id=req.ambulance_id, base_node=req.pickup)
    mission["status"] = "ASSIGNED"
    state.events.log("🚑", f"Ambulance {req.ambulance_id} assigned to {mission_id}")

    return mission


@app.post("/api/emergency/{mission_id}/assign")
def assign_ambulance(mission_id: str, ambulance_id: str = "AMB-01"):
    mission = _mission_or_404(mission_id)
    mission["assigned_ambulance"] = ambulance_id
    mission["status"] = "ASSIGNED"
    state.events.log("🚑", f"Ambulance {ambulance_id} assigned to {mission_id}")
    return mission


@app.post("/api/optimize")
def optimize(req: OptimizeRequest):
    mission = _mission_or_404(req.mission_id)
    state.events.log("🧠", f"{req.algorithm} optimization started for {req.mission_id}")

    # simulate a small organic traffic drift before optimizing, for realism
    drift_traffic(state.city_graph, state.rng, magnitude=0.03)

    result = _run_optimization(mission, req.algorithm)
    if not result["feasible"]:
        raise HTTPException(status_code=422, detail="No feasible route found")

    mission["route"] = result["route"]
    mission["status"] = "ROUTE_OPTIMIZED"
    mission["eta_min"] = result["metrics"]["travel_time_min"] if result.get("metrics") else None

    if req.algorithm == "QPSO":
        state.convergence_history = result.get("convergence_history", [])

    state.ambulance.assign(mission["mission_id"], result["route"])
    state.ambulance.eta_min = mission["eta_min"]

    _activate_corridor_for_route(result["route"])

    state.events.log("✓", f"Route optimized ({result.get('label', result['algorithm'])}) — fitness {result['fitness']}")
    state.events.log("🟢", "Green corridor activated")

    return {"mission": mission, "optimization": result, "corridor": state.corridor_plan}


@app.post("/api/reoptimize")
def reoptimize(req: OptimizeRequest):
    mission = _mission_or_404(req.mission_id)
    state.events.log("🔄", f"Re-optimization started for {req.mission_id}")

    current_node = state.ambulance.current_node
    result = _run_optimization(mission, req.algorithm, source_override=current_node)
    if not result["feasible"]:
        raise HTTPException(status_code=422, detail="No feasible route found during re-optimization")

    mission["route"] = result["route"]
    mission["eta_min"] = result["metrics"]["travel_time_min"] if result.get("metrics") else None

    if req.algorithm == "QPSO":
        state.convergence_history = result.get("convergence_history", [])

    state.ambulance.reroute(result["route"])
    state.ambulance.status = "EN_ROUTE"
    state.ambulance.eta_min = mission["eta_min"]

    _activate_corridor_for_route(state.ambulance.route)

    state.events.log("✓", f"New route found ({result.get('label', result['algorithm'])}) — fitness {result['fitness']}")
    state.events.log("🟢", "New green corridor activated")

    return {"mission": mission, "optimization": result, "corridor": state.corridor_plan}


@app.post("/api/traffic/incident")
def traffic_incident(req: IncidentRequest):
    mission = _mission_or_404(req.mission_id)
    route = state.ambulance.route or mission.get("route")
    edge_id = req.edge_id
    if not edge_id:
        edge = pick_incident_edge(state.city_graph, route, state.rng)
        if edge is None:
            raise HTTPException(status_code=422, detail="No route edge available to disrupt")
        edge_id = edge["edge_id"]

    incident = inject_incident(state.city_graph, edge_id, mode="block")
    state.last_incident = incident
    state.events.log("⚠️", f"Traffic incident detected on {incident['road_name']} ({edge_id})")

    disrupted = not state.city_graph.is_path_valid(state.ambulance.route)
    if disrupted:
        state.events.log("🔴", "Current route disrupted — re-optimization required")

    return {"incident": incident, "route_disrupted": disrupted, "mission_id": mission["mission_id"]}


@app.get("/api/ambulance")
def get_ambulance():
    now = time.time()
    dt = now - state.ambulance.last_tick
    state.ambulance.last_tick = now
    just_arrived = state.ambulance.tick(state.city_graph, dt * state.config.get("demo_speed_multiplier", 1.0))

    if just_arrived and state.active_mission_id:
        mission = state.missions.get(state.active_mission_id)
        if mission and mission["status"] != "COMPLETED":
            mission["status"] = "COMPLETED"
            state.events.log("🏥", "Hospital reached")
            state.events.log("✅", f"Mission {mission['mission_id']} completed")

    mission_id = state.active_mission_id or "MISSION"
    if state.corridor_plan.get("active"):
        state.tcs.sync_signals(state.city_graph, state.corridor_plan, state.ambulance, mission_id)
    else:
        apply_corridor_state(state.city_graph, state.corridor_plan, 0)

    return state.ambulance.to_dict(state.city_graph)


@app.get("/api/signals")
def get_signals():
    return state.city_graph.signals


@app.get("/api/route/{mission_id}")
def get_route(mission_id: str):
    mission = _mission_or_404(mission_id)
    return {"mission_id": mission_id, "route": mission.get("route", [])}


@app.post("/api/corridor/activate")
def activate_corridor(req: CorridorRequest):
    mission = _mission_or_404(req.mission_id)
    _activate_corridor_for_route(mission["route"])
    state.events.log("🟢", "Green corridor activated")
    return state.corridor_plan


@app.post("/api/corridor/deactivate")
def deactivate_corridor(req: CorridorRequest):
    state.corridor_plan = {"active": False, "schedule": []}
    apply_corridor_state(state.city_graph, state.corridor_plan, 0)
    for sig in state.city_graph.signals:
        state.tcs.note_phase(sig["signal_id"], "NORMAL")
    state.events.log("⚪", "Green corridor deactivated")
    return state.corridor_plan


# ------------------------------------------------------- traffic control server

@app.get("/api/navigation/{mission_id}")
def get_navigation(mission_id: str):
    """Driver-app turn-by-turn instruction, computed live from route
    geometry + ambulance position (see traffic_control.build_navigation).
    Not hardcoded."""
    mission = _mission_or_404(mission_id)
    return build_navigation(state.city_graph, state.ambulance, mission)


@app.get("/api/control/commands")
def get_command_log():
    """Command log for the Traffic Control Center UI -- populated only
    from real signal phase transitions, never fabricated."""
    return {"commands": state.tcs.to_public_log()}


@app.post("/api/signals/{signal_id}/priority")
def issue_signal_command(signal_id: str, req: SignalCommandRequest):
    """Manual/simulated signal command channel exposed for architecture
    completeness (Part 5). In the live demo, signal phases are normally
    driven automatically by the green-corridor ETA schedule; this endpoint
    lets the Traffic Control Server (or an operator) issue an explicit
    override command, which is recorded in the same command log.

    IMPORTANT: this is a SIMULATED signal controller command -- it does
    not control any real municipal traffic signal."""
    sig = next((s for s in state.city_graph.signals if s["signal_id"] == signal_id), None)
    if sig is None:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
    if req.command not in ("NORMAL", "PREPARE", "PRIORITY"):
        raise HTTPException(status_code=400, detail="command must be NORMAL, PREPARE or PRIORITY")

    sig["current_phase"] = req.command
    sig["priority_requested"] = req.command in ("PREPARE", "PRIORITY")
    sig["priority_active"] = req.command == "PRIORITY"
    entry = state.tcs.emit_manual(signal_id, req.command, req.reason or "manual override")
    sig["last_command"] = entry["command"]
    sig["command_timestamp"] = entry["time"]
    state.tcs.note_phase(signal_id, req.command)
    state.events.log("🚦", f"SIGNAL {signal_id} COMMAND: {req.command} (reason: {req.reason or 'manual'})")
    return sig


@app.post("/api/benchmark")
def run_benchmark(req: BenchmarkRequest):
    weights = state.weights()
    source = req.source
    destination = req.destination
    results = []
    for algo in req.algorithms:
        if algo == "DIJKSTRA":
            results.append(run_dijkstra(state.city_graph, source, destination, weights))
        elif algo == "ASTAR":
            results.append(run_astar(state.city_graph, source, destination, weights))
        elif algo == "QPSO":
            results.append(run_qpso(state.city_graph, source, destination, weights, state.config))
        elif algo == "PSO":
            results.append(run_pso(state.city_graph, source, destination, weights, state.config))
        elif algo == "GA":
            results.append(run_ga(state.city_graph, source, destination, weights, state.config))
    state.benchmark_results = results
    state.events.log("📊", f"Benchmark executed across {len(results)} algorithms")
    return {"results": results}


@app.get("/api/benchmark/results")
def get_benchmark_results():
    return {"results": state.benchmark_results}


@app.get("/api/convergence/{mission_id}")
def get_convergence(mission_id: str):
    _mission_or_404(mission_id)
    return {"mission_id": mission_id, "history": state.convergence_history}


@app.get("/api/timeline")
def get_timeline():
    return {"events": state.events.to_list()}


@app.get("/api/state")
def get_full_state():
    """Convenience aggregate endpoint the frontend polls."""
    return {
        "mission": state.missions.get(state.active_mission_id) if state.active_mission_id else None,
        "ambulance": state.ambulance.to_dict(state.city_graph),
        "signals": state.city_graph.signals,
        "corridor": state.corridor_plan,
        "timeline": state.events.to_list()[-30:],
        "network_meta": {
            "edges_blocked": [e["edge_id"] for e in state.city_graph.edges.values() if e["blocked"]],
        },
        "last_incident": state.last_incident,
        "command_log": state.tcs.to_public_log(),
        "navigation": (
            build_navigation(state.city_graph, state.ambulance, state.missions.get(state.active_mission_id))
            if state.active_mission_id else None
        ),
    }


@app.post("/api/reset")
def reset_simulation():
    state.reset()
    state.events.log("🔁", "Simulation reset")
    return {"status": "RESET_OK"}
