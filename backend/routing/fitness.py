"""
Multi-objective route cost function used by every algorithm (Dijkstra, A*,
PSO, GA, QPSO) so comparisons in the benchmark panel are apples-to-apples.

Cost(R) = w_t * TravelTime(R) + w_d * Distance(R) + w_c * Congestion(R)
          + w_s * SignalDelay(R) + Penalty(R)

TravelTime(R): sum of per-edge travel time in minutes (traffic-adjusted).
Distance(R):   sum of per-edge distance in km.
Congestion(R): mean traffic_level along the route, scaled to a comparable
               magnitude (x10) so it isn't swamped by travel time.
SignalDelay(R): total signal delay in minutes.
Penalty(R): large constant added if the route is infeasible (blocked edge,
            disconnected, or does not reach the destination).

For emergency ambulance routing, travel time and congestion are weighted
most heavily (see config.json: time_weight=0.4, congestion_weight=0.3).
"""
from .graph import travel_time_minutes


def route_metrics(city_graph, path: list) -> dict:
    """Raw (unweighted) metrics for a path. Returns None if infeasible."""
    if not city_graph.is_path_valid(path):
        return None
    edges = city_graph.path_edges(path)
    travel_time = sum(travel_time_minutes(e) for e in edges)
    distance = sum(e["distance"] for e in edges)
    congestion = sum(e["traffic_level"] for e in edges) / len(edges)
    signal_delay = sum(e["signal_delay"] for e in edges) / 60.0  # minutes
    return {
        "travel_time_min": round(travel_time, 3),
        "distance_km": round(distance, 3),
        "congestion": round(congestion, 4),
        "signal_delay_min": round(signal_delay, 3),
        "hops": len(edges),
    }


def edge_cost(edge: dict, weights: dict) -> float:
    """Weighted cost of a single edge. This is the SAME function Dijkstra
    and A* use internally (see dijkstra.py), and fitness() below just sums
    it over a path -- guaranteeing every algorithm in the benchmark
    optimizes over an identical, additive cost surface. (Previously this
    averaged congestion at the route level while Dijkstra summed it per
    edge, which let QPSO appear to 'beat' the true shortest path purely
    from a metric mismatch -- fixed here.)"""
    if edge["blocked"]:
        return float("inf")
    t = travel_time_minutes(edge)
    return (
        weights.get("time_weight", 0.4) * t
        + weights.get("distance_weight", 0.15) * edge["distance"]
        + weights.get("congestion_weight", 0.3) * (edge["traffic_level"] * 10)
        + weights.get("signal_weight", 0.15) * (edge["signal_delay"] / 60.0)
    )


def fitness(city_graph, path: list, weights: dict, penalty: float = 5000.0) -> float:
    """Lower is better. Sum of edge_cost() over the path. Infeasible /
    disconnected candidates get a large penalty so optimizers are steered
    away from them without crashing."""
    if not city_graph.is_path_valid(path):
        return penalty
    edges = city_graph.path_edges(path)
    cost = sum(edge_cost(e, weights) for e in edges)
    return round(cost, 4)
