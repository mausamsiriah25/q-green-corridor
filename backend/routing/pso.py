"""
Classic velocity-based PSO, used purely as a benchmark comparison against
QPSO. Uses the identical priority-vector decode/repair scheme as qpso.py
(see that file's docstring) so the only difference measured in the
benchmark panel is the update rule itself (velocity-based vs
quantum/delta-potential-well), not the encoding.
"""
import time
import numpy as np
from .fitness import route_metrics, fitness
from .qpso import _decode


def run_pso(city_graph, source, target, weights, config, seed=None):
    start_time = time.perf_counter()
    np_rng = np.random.default_rng(seed if seed is not None else config.get("random_seed", 42))

    node_ids = list(city_graph.nodes.keys())
    node_index = {n: i for i, n in enumerate(node_ids)}
    n_dims = len(node_ids)

    pop_size = config.get("population_size", 20)
    iterations = config.get("iterations", 50)
    penalty = config.get("penalty_infeasible", 5000)
    w, c1, c2 = 0.7, 1.4, 1.4

    positions = np_rng.uniform(0, 1, size=(pop_size, n_dims))
    velocities = np_rng.uniform(-0.1, 0.1, size=(pop_size, n_dims))
    pbest_pos = positions.copy()
    pbest_fit = np.full(pop_size, float("inf"))
    gbest_pos, gbest_fit, gbest_path = None, float("inf"), None

    for it in range(iterations):
        for i in range(pop_size):
            decoded = _decode(city_graph, positions[i], node_index, source, target)
            f = fitness(city_graph, decoded, weights, penalty=penalty) if decoded else penalty
            if f < pbest_fit[i]:
                pbest_fit[i] = f
                pbest_pos[i] = positions[i].copy()
            if f < gbest_fit:
                gbest_fit, gbest_pos, gbest_path = f, positions[i].copy(), decoded

        r1, r2 = np_rng.uniform(0, 1, size=(pop_size, n_dims)), np_rng.uniform(0, 1, size=(pop_size, n_dims))
        velocities = w * velocities + c1 * r1 * (pbest_pos - positions) + c2 * r2 * (gbest_pos - positions)
        positions = positions + velocities

    runtime = time.perf_counter() - start_time
    m = route_metrics(city_graph, gbest_path) if gbest_path else None
    return {
        "algorithm": "PSO",
        "feasible": gbest_path is not None,
        "route": gbest_path or [],
        "fitness": round(gbest_fit, 4) if gbest_path else None,
        "metrics": m,
        "runtime_sec": round(runtime, 5),
    }
