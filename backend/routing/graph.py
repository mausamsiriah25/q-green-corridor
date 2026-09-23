"""
Dynamic weighted graph for Q-GREEN CORRIDOR.

G = (V, E). Each edge carries live traffic state. Edge cost is NOT plain
distance -- it is a multi-factor cost combining travel time, distance,
congestion and signal delay (see fitness.py for the exact formula used
by the optimizers). This module owns the graph structure + mutation
(blocking roads, changing traffic) and exposes NetworkX-backed helpers.
"""
import json
import copy
import os
import networkx as nx

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CITY_FILE = os.path.join(DATA_DIR, "city_network.json")


def travel_time_minutes(edge: dict) -> float:
    """Travel time depends dynamically on traffic: higher traffic_level -> lower effective speed."""
    if edge["blocked"]:
        return float("inf")
    traffic = edge["traffic_level"]
    # effective speed degrades non-linearly as traffic approaches 1.0 (severe)
    speed_factor = max(0.12, 1 - (traffic ** 1.6))
    effective_speed = max(3.0, edge["base_speed"] * speed_factor)  # km/h, never fully zero
    time_hours = edge["distance"] / effective_speed
    minutes = time_hours * 60
    minutes += edge["signal_delay"] / 60.0  # signal_delay stored in seconds
    return minutes


class CityGraph:
    """Wraps the simulated city network as a live, mutable directed graph."""

    def __init__(self, network: dict = None):
        if network is None:
            with open(CITY_FILE) as f:
                network = json.load(f)
        self._original = copy.deepcopy(network)
        self.nodes = copy.deepcopy(network["nodes"])
        self.edges = {e["edge_id"]: copy.deepcopy(e) for e in network["edges"]}
        self.signals = copy.deepcopy(network["signals"])
        self.ambulance_base = network["ambulance_base"]
        self.hospital = network["hospital"]
        self._rebuild_nx()

    # ---------------------------------------------------------------- core
    def _rebuild_nx(self):
        g = nx.DiGraph()
        for n, data in self.nodes.items():
            g.add_node(n, **data)
        for e in self.edges.values():
            if e["blocked"]:
                continue
            g.add_edge(e["source"], e["destination"], **e, weight=travel_time_minutes(e))
        self.nx_graph = g

    def reset(self):
        self.nodes = copy.deepcopy(self._original["nodes"])
        self.edges = {e["edge_id"]: copy.deepcopy(e) for e in self._original["edges"]}
        self.signals = copy.deepcopy(self._original["signals"])
        self._rebuild_nx()

    # ------------------------------------------------------------ mutation
    def edges_out(self, node: str):
        return [e for e in self.edges.values() if e["source"] == node]

    def edge_between(self, u: str, v: str):
        for e in self.edges.values():
            if e["source"] == u and e["destination"] == v:
                return e
        return None

    def set_traffic(self, edge_id: str, level: float):
        level = max(0.0, min(1.0, level))
        e = self.edges[edge_id]
        e["traffic_level"] = level
        e["current_speed"] = round(e["base_speed"] * max(0.15, 1 - level), 1)
        self._rebuild_nx()

    def block_edge(self, edge_id: str):
        self.edges[edge_id]["blocked"] = True
        self.edges[edge_id]["traffic_level"] = 1.0
        self._rebuild_nx()

    def unblock_edge(self, edge_id: str):
        self.edges[edge_id]["blocked"] = False
        self._rebuild_nx()

    def is_path_valid(self, path: list) -> bool:
        """A path (list of node ids) is valid iff every consecutive pair has an
        unblocked edge -- used to check feasibility of any candidate route,
        including ones an optimizer proposes."""
        if len(path) < 2:
            return False
        for i in range(len(path) - 1):
            e = self.edge_between(path[i], path[i + 1])
            if e is None or e["blocked"]:
                return False
        return True

    def path_edges(self, path: list) -> list:
        return [self.edge_between(path[i], path[i + 1]) for i in range(len(path) - 1)]

    def neighbors(self, node: str):
        return [e["destination"] for e in self.edges_out(node) if not e["blocked"]]

    def to_public_dict(self):
        return {
            "nodes": self.nodes,
            "edges": list(self.edges.values()),
            "signals": self.signals,
        }
