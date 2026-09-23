"""
Tests for the Traffic Control Server / driver navigation extensions
(Part 4-6, 13, 16). Same dependency-light style as test_core.py so it can
run with `python tests/test_traffic_control.py` even without pytest.
"""
import os
import sys
import networkx as nx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from routing.graph import CityGraph
from corridor.planner import build_corridor_plan
from simulation.ambulance import Ambulance
from traffic_control import TrafficControlServer, build_navigation, _classify_turn, _bearing_deg


def _route_via(g, *nodes):
    route = [nodes[0]]
    for a, b in zip(nodes, nodes[1:]):
        seg = nx.shortest_path(g.nx_graph, a, b, weight="weight")
        route += seg[1:]
    return route


def test_turn_classification_straight():
    assert _classify_turn(90, 95) == "STRAIGHT"
    assert _classify_turn(0, 10) == "STRAIGHT"


def test_turn_classification_left_right():
    assert _classify_turn(90, 150) == "RIGHT"   # bearing increases clockwise
    assert _classify_turn(90, 30) == "LEFT"      # bearing decreases


def test_signal_eta_based_prepare_and_priority():
    """With two signals on the route at different ETAs, the nearer one
    should be PRIORITY while the farther one is PREPARE (Part 6)."""
    g = CityGraph()
    route = _route_via(g, g.ambulance_base, "S2", "S5", g.hospital)
    amb = Ambulance(base_node=g.ambulance_base)
    amb.assign("MSN-T1", route)
    plan = build_corridor_plan(g, route)
    assert plan["total_signals"] == 2

    tcs = TrafficControlServer()
    signals = tcs.sync_signals(g, plan, amb, "MSN-T1")
    by_id = {s["signal_id"]: s for s in signals}
    assert by_id["SIG-S2"]["current_phase"] == "PRIORITY"
    assert by_id["SIG-S5"]["current_phase"] == "PREPARE"
    assert by_id["SIG-S2"]["priority_active"] is True
    assert by_id["SIG-S5"]["priority_requested"] is True
    assert by_id["SIG-S5"]["priority_active"] is False


def test_signal_command_log_on_pass_and_reset():
    g = CityGraph()
    route = _route_via(g, g.ambulance_base, "S2", g.hospital)
    amb = Ambulance(base_node=g.ambulance_base)
    amb.assign("MSN-T2", route)
    plan = build_corridor_plan(g, route)
    tcs = TrafficControlServer()

    tcs.sync_signals(g, plan, amb, "MSN-T2")
    assert any(c["command"] == "PRIORITY" for c in tcs.command_log)

    s2_index = route.index("S2")
    amb.route_progress_index = s2_index + 1  # ambulance has passed S2
    tcs.sync_signals(g, plan, amb, "MSN-T2")
    assert any(c["command"] == "NORMAL" and "passed" in c["reason"] for c in tcs.command_log)


def test_manual_signal_priority_command_and_log():
    tcs = TrafficControlServer()
    entry = tcs.emit_manual("SIG-S2", "PRIORITY", "manual override")
    assert entry["command"] == "PRIORITY"
    assert tcs.to_public_log()[0]["signal_id"] == "SIG-S2"


def test_navigation_instruction_generation():
    g = CityGraph()
    route = _route_via(g, g.ambulance_base, "S2", g.hospital)
    amb = Ambulance(base_node=g.ambulance_base)
    amb.assign("MSN-T3", route)

    nav = build_navigation(g, amb, None)
    assert nav["instruction_type"] in ("LEFT", "RIGHT", "STRAIGHT", "ARRIVE")
    assert nav["distance_remaining_km"] > 0
    assert nav["eta_min"] >= 0
    assert nav["green_corridor_active"] is True


def test_navigation_mission_completion():
    g = CityGraph()
    route = _route_via(g, g.ambulance_base, g.hospital)
    amb = Ambulance(base_node=g.ambulance_base)
    amb.assign("MSN-T4", route)
    amb.route_progress_index = len(route) - 1
    amb.status = "ARRIVED"

    nav = build_navigation(g, amb, None)
    assert nav["instruction_type"] == "ARRIVE"
    assert nav["green_corridor_active"] is False


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
        except Exception as e:
            print(f"ERROR {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
