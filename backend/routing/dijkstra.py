"""Dijkstra baseline. Uses the exact same per-edge weighted cost (edge_cost,
shared with every other algorithm via fitness.py) so the benchmark
comparison is provably fair -- not raw distance."""
import time
import heapq
from .fitness import route_metrics, fitness, edge_cost as _edge_weight


def run_dijkstra(city_graph, source: str, target: str, weights: dict) -> dict:
    start = time.perf_counter()
    dist = {source: 0.0}
    prev = {}
    visited = set()
    pq = [(0.0, source)]
    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if u == target:
            break
        for e in city_graph.edges_out(u):
            if e["blocked"]:
                continue
            v = e["destination"]
            w = _edge_weight(e, weights)
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    runtime = time.perf_counter() - start
    if target not in prev and target != source:
        return {"algorithm": "DIJKSTRA", "feasible": False, "route": [], "runtime_sec": round(runtime, 5)}

    path = [target]
    while path[-1] != source:
        path.append(prev[path[-1]])
    path.reverse()

    m = route_metrics(city_graph, path)
    f = fitness(city_graph, path, weights)
    return {
        "algorithm": "DIJKSTRA",
        "feasible": True,
        "route": path,
        "fitness": f,
        "metrics": m,
        "runtime_sec": round(runtime, 5),
    }
