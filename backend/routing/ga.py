"""
Genetic Algorithm baseline (benchmark comparison only). Chromosomes are the
same priority vectors used by qpso.py / pso.py, decoded via the identical
greedy + Dijkstra-repair scheme, so all optimizers are compared on equal
footing (only the search operator differs: GA uses selection/crossover/
mutation instead of a swarm update).
"""
import time
import numpy as np
from .fitness import route_metrics, fitness
from .qpso import _decode


def run_ga(city_graph, source, target, weights, config, seed=None):
    start_time = time.perf_counter()
    rng = np.random.default_rng(seed if seed is not None else config.get("random_seed", 42))

    node_ids = list(city_graph.nodes.keys())
    node_index = {n: i for i, n in enumerate(node_ids)}
    n_dims = len(node_ids)

    pop_size = config.get("population_size", 20)
    generations = config.get("iterations", 50)
    penalty = config.get("penalty_infeasible", 5000)
    mutation_rate = 0.15
    elite_count = max(1, pop_size // 10)

    population = rng.uniform(0, 1, size=(pop_size, n_dims))
    best_pos, best_fit, best_path = None, float("inf"), None

    def evaluate(pop):
        fits, paths = [], []
        for i in range(pop.shape[0]):
            decoded = _decode(city_graph, pop[i], node_index, source, target)
            f = fitness(city_graph, decoded, weights, penalty=penalty) if decoded else penalty
            fits.append(f)
            paths.append(decoded)
        return np.array(fits), paths

    for gen in range(generations):
        fits, paths = evaluate(population)
        gen_best_idx = int(np.argmin(fits))
        if fits[gen_best_idx] < best_fit:
            best_fit = fits[gen_best_idx]
            best_pos = population[gen_best_idx].copy()
            best_path = paths[gen_best_idx]

        order = np.argsort(fits)
        elites = population[order[:elite_count]]

        # tournament selection + uniform crossover + gaussian mutation
        new_pop = [e.copy() for e in elites]
        while len(new_pop) < pop_size:
            i1, i2 = rng.integers(0, pop_size, size=2)
            parent1 = population[i1] if fits[i1] < fits[i2] else population[i2]
            i3, i4 = rng.integers(0, pop_size, size=2)
            parent2 = population[i3] if fits[i3] < fits[i4] else population[i4]
            mask = rng.uniform(0, 1, size=n_dims) < 0.5
            child = np.where(mask, parent1, parent2)
            mutate_mask = rng.uniform(0, 1, size=n_dims) < mutation_rate
            child = child + mutate_mask * rng.normal(0, 0.3, size=n_dims)
            new_pop.append(child)
        population = np.array(new_pop[:pop_size])

    runtime = time.perf_counter() - start_time
    m = route_metrics(city_graph, best_path) if best_path else None
    return {
        "algorithm": "GA",
        "feasible": best_path is not None,
        "route": best_path or [],
        "fitness": round(best_fit, 4) if best_path else None,
        "metrics": m,
        "runtime_sec": round(runtime, 5),
    }
