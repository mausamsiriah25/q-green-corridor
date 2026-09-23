"""Local traffic simulator. No external APIs -- everything is generated and
mutated in-process so the app works fully offline."""
import random


def traffic_state(level: float) -> str:
    if level >= 0.8:
        return "SEVERE"
    if level >= 0.55:
        return "HEAVY"
    if level >= 0.3:
        return "MODERATE"
    return "LOW"


def drift_traffic(city_graph, rng: random.Random = None, magnitude: float = 0.06):
    """Small random walk applied to every edge's traffic_level, simulating
    organic traffic evolution between optimization calls."""
    rng = rng or random
    for edge_id, e in city_graph.edges.items():
        if e["blocked"]:
            continue
        delta = rng.uniform(-magnitude, magnitude)
        new_level = max(0.05, min(0.95, e["traffic_level"] + delta))
        city_graph.set_traffic(edge_id, new_level)


def inject_incident(city_graph, edge_id: str, mode: str = "block"):
    """mode='block' fully blocks the road; mode='congest' pushes it to
    95-100% congestion without fully blocking it (still usable as a very
    costly last resort by the optimizer's repair step)."""
    if mode == "block":
        city_graph.block_edge(edge_id)
    else:
        city_graph.set_traffic(edge_id, random.uniform(0.95, 1.0))
    e = city_graph.edges[edge_id]
    return {
        "edge_id": edge_id,
        "source": e["source"],
        "destination": e["destination"],
        "road_name": e["road_name"],
        "mode": mode,
        "blocked": e["blocked"],
        "traffic_level": e["traffic_level"],
    }


def pick_incident_edge(city_graph, route: list, rng: random.Random = None):
    """Choose an edge belonging to the currently active route so the
    incident is guaranteed to disrupt the ambulance's current path
    (execution rule F)."""
    rng = rng or random
    if not route or len(route) < 2:
        return None
    edges = city_graph.path_edges(route)
    edges = [e for e in edges if e is not None]
    if not edges:
        return None
    # prefer an edge roughly in the first half of the remaining route so
    # there's a visible re-route rather than blocking the very last hop
    cut = max(1, len(edges) // 2)
    return rng.choice(edges[:cut] or edges)
