"""A* baseline. Heuristic = straight-line distance to target converted to an
optimistic minutes estimate at the fastest possible road speed, so it never
overestimates the true weighted cost (admissible for the distance component)."""
import time
import heapq
import math
from .fitness import route_metrics, fitness, edge_cost as _edge_weight

FASTEST_SPEED_KMH = 50.0


def _heuristic(city_graph, node, target, weights):
    a, b = city_graph.nodes[node], city_graph.nodes[target]
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [a["lat"], a["lon"], b["lat"], b["lon"]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    straight_km = 2 * R * math.asin(math.sqrt(h))
    optimistic_minutes = (straight_km / FASTEST_SPEED_KMH) * 60
    return weights.get("time_weight", 0.4) * optimistic_minutes + weights.get("distance_weight", 0.15) * straight_km


def run_astar(city_graph, source: str, target: str, weights: dict) -> dict:
    start = time.perf_counter()
    g_score = {source: 0.0}
    prev = {}
    open_set = [(_heuristic(city_graph, source, target, weights), source)]
    visited = set()

    while open_set:
        _, u = heapq.heappop(open_set)
        if u in visited:
            continue
        visited.add(u)
        if u == target:
            break
        for e in city_graph.edges_out(u):
            if e["blocked"]:
                continue
            v = e["destination"]
            tentative = g_score[u] + _edge_weight(e, weights)
            if tentative < g_score.get(v, float("inf")):
                g_score[v] = tentative
                prev[v] = u
                f = tentative + _heuristic(city_graph, v, target, weights)
                heapq.heappush(open_set, (f, v))

    runtime = time.perf_counter() - start
    if target not in prev and target != source:
        return {"algorithm": "ASTAR", "feasible": False, "route": [], "runtime_sec": round(runtime, 5)}

    path = [target]
    while path[-1] != source:
        path.append(prev[path[-1]])
    path.reverse()

    m = route_metrics(city_graph, path)
    f = fitness(city_graph, path, weights)
    return {
        "algorithm": "ASTAR",
        "feasible": True,
        "route": path,
        "fitness": f,
        "metrics": m,
        "runtime_sec": round(runtime, 5),
    }
