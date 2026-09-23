"""
Green Corridor planner.

IMPORTANT (see execution rules / honesty requirements): this is a
SIMULATION of a signal-priority schedule for demo purposes. It does not
connect to, and does not claim to control, real traffic infrastructure.

Given an optimized route, this module:
  1. Identifies which signalized intersections (S2, S5, S8, ...) lie on it.
  2. Estimates the ambulance's arrival time at each signal (cumulative
     travel time along the route up to that node).
  3. Builds a priority schedule: the signal the ambulance is currently
     approaching/at is PRIORITY (green), the next 1-2 signals are marked
     PREPARE, and signals already passed return to NORMAL.
"""
from routing.graph import travel_time_minutes


def build_corridor_plan(city_graph, route: list) -> dict:
    if not route or len(route) < 2:
        return {"active": False, "schedule": []}

    edges = city_graph.path_edges(route)
    cumulative_min = 0.0
    schedule = []
    for i, node in enumerate(route):
        if i > 0:
            cumulative_min += travel_time_minutes(edges[i - 1])
        if city_graph.nodes[node]["is_signal"]:
            schedule.append({
                "node": node,
                "signal_id": f"SIG-{node}",
                "estimated_arrival_min": round(cumulative_min, 2),
                "route_index": i,
            })

    return {"active": True, "schedule": schedule, "total_signals": len(schedule)}


def apply_corridor_state(city_graph, corridor_plan: dict, ambulance_route_index: int):
    """Updates each signal's current_phase based on how far along the route
    the ambulance currently is. Returns the updated signal list."""
    if not corridor_plan.get("active"):
        for sig in city_graph.signals:
            sig["current_phase"] = "NORMAL"
            sig["corridor_status"] = "INACTIVE"
            sig["estimated_arrival"] = None
        return city_graph.signals

    upcoming_indices = [s["route_index"] for s in corridor_plan["schedule"]]

    for sig in city_graph.signals:
        node = sig["node"]
        match = next((s for s in corridor_plan["schedule"] if s["node"] == node), None)
        if match is None:
            continue
        if match["route_index"] < ambulance_route_index:
            sig["current_phase"] = "NORMAL"
            sig["corridor_status"] = "PASSED"
            sig["estimated_arrival"] = None
        elif match["route_index"] == ambulance_route_index or (
            upcoming_indices and match["route_index"] == min(
                [idx for idx in upcoming_indices if idx >= ambulance_route_index], default=None
            )
        ):
            sig["current_phase"] = "PRIORITY"
            sig["corridor_status"] = "ACTIVE"
            sig["estimated_arrival"] = match["estimated_arrival_min"]
        else:
            sig["current_phase"] = "PREPARE"
            sig["corridor_status"] = "PENDING"
            sig["estimated_arrival"] = match["estimated_arrival_min"]

    return city_graph.signals
