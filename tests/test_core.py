"""
Basic automated tests for Q-GREEN CORRIDOR core workflow.
Run: pytest tests/test_core.py -v   (from project root, with backend on PYTHONPATH)
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from routing.graph import CityGraph
from routing.fitness import route_metrics, fitness, edge_cost
from routing.dijkstra import run_dijkstra
from routing.astar import run_astar
from routing.qpso import run_qpso
from simulation.traffic import inject_incident, pick_incident_edge
from corridor.planner import build_corridor_plan

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "config.json")
WEIGHTS = {"time_weight": 0.4, "distance_weight": 0.15, "congestion_weight": 0.3, "signal_weight": 0.15}


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def test_graph_creation():
    g = CityGraph()
    assert len(g.nodes) >= 20
    assert len(g.edges) > 0
    assert g.ambulance_base == "A"
    assert g.hospital == "H"


def test_no_duplicate_parallel_edges():
    g = CityGraph()
    pairs = {}
    for e in g.edges.values():
        key = (e["source"], e["destination"])
        pairs[key] = pairs.get(key, 0) + 1
    assert all(v == 1 for v in pairs.values()), "duplicate parallel edges detected"


def test_fitness_calculation():
    g = CityGraph()
    d = run_dijkstra(g, "A", "H", WEIGHTS)
    assert d["feasible"]
    m = route_metrics(g, d["route"])
    assert m is not None
    assert m["travel_time_min"] > 0
    assert m["distance_km"] > 0


def test_route_validity():
    g = CityGraph()
    d = run_dijkstra(g, "A", "H", WEIGHTS)
    assert g.is_path_valid(d["route"])
    assert d["route"][0] == "A"
    assert d["route"][-1] == "H"


def test_blocked_road_handling():
    g = CityGraph()
    d1 = run_dijkstra(g, "A", "H", WEIGHTS)
    edge = pick_incident_edge(g, d1["route"])
    inject_incident(g, edge["edge_id"], mode="block")
    assert not g.is_path_valid(d1["route"])
    d2 = run_dijkstra(g, "A", "H", WEIGHTS)
    assert d2["feasible"]
    assert edge["edge_id"] not in [e["edge_id"] for e in g.path_edges(d2["route"])]


def test_dijkstra_finds_optimum():
    g = CityGraph()
    d = run_dijkstra(g, "A", "H", WEIGHTS)
    assert d["feasible"]
    assert d["fitness"] < 5000  # not the infeasibility penalty


def test_astar_matches_dijkstra():
    g = CityGraph()
    d = run_dijkstra(g, "A", "H", WEIGHTS)
    a = run_astar(g, "A", "H", WEIGHTS)
    assert abs(d["fitness"] - a["fitness"]) < 1e-6, "A* and Dijkstra must agree on optimal cost"


def test_qpso_runs_and_converges():
    g = CityGraph()
    config = load_config()
    config["iterations"] = 30
    q = run_qpso(g, "A", "H", WEIGHTS, config, seed=1)
    assert q["feasible"]
    assert len(q["convergence_history"]) == 30
    first_fitness = q["convergence_history"][0]["best_fitness"]
    last_fitness = q["convergence_history"][-1]["best_fitness"]
    assert last_fitness <= first_fitness, "QPSO should never get worse over iterations (elitist gbest)"


def test_qpso_never_beats_true_optimum():
    """QPSO's cost function must be identical to Dijkstra's -- it should
    never report a lower fitness than the true shortest path (that would
    indicate a metric mismatch bug, not a better route)."""
    g = CityGraph()
    config = load_config()
    d = run_dijkstra(g, "A", "H", WEIGHTS)
    q = run_qpso(g, "A", "H", WEIGHTS, config, seed=7)
    assert q["fitness"] >= d["fitness"] - 1e-6


def test_incident_injection_and_corridor():
    g = CityGraph()
    config = load_config()
    q1 = run_qpso(g, "A", "H", WEIGHTS, config, seed=3)
    plan = build_corridor_plan(g, q1["route"])
    assert "active" in plan

    edge = pick_incident_edge(g, q1["route"])
    assert edge is not None
    inject_incident(g, edge["edge_id"], mode="block")
    assert not g.is_path_valid(q1["route"])

    q2 = run_qpso(g, "A", "H", WEIGHTS, config, seed=3)
    assert q2["feasible"]
    assert q2["route"] != q1["route"]


def test_reoptimize_from_current_position_no_backtrack():
    """Re-optimization should route from wherever the ambulance currently
    is, not the original pickup -- otherwise the ambulance visually
    backtracks to the start after a mid-route incident."""
    g = CityGraph()
    config = load_config()
    q1 = run_qpso(g, "A", "H", WEIGHTS, config, seed=5)
    # simulate the ambulance having progressed to the second node on its route
    current_node = q1["route"][1]
    edge = pick_incident_edge(g, q1["route"])
    inject_incident(g, edge["edge_id"], mode="block")
    q2 = run_qpso(g, current_node, "H", WEIGHTS, config, seed=5)
    assert q2["feasible"]
    assert q2["route"][0] == current_node, "re-optimized route must start at the ambulance's current node"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
