"""Ambulance entity + movement-along-route simulation."""
import time
from routing.graph import travel_time_minutes


class Ambulance:
    def __init__(self, ambulance_id="AMB-01", base_node="A"):
        self.ambulance_id = ambulance_id
        self.current_node = base_node
        self.status = "IDLE"  # IDLE | EN_ROUTE | ARRIVED
        self.speed_kmh = 60  # ambulances move faster than base traffic speed
        self.assigned_mission = None
        self.route = []
        self.route_progress_index = 0  # index of the node the ambulance is currently AT
        self.segment_progress = 0.0  # 0..1 fraction along the current edge
        self.eta_min = None
        self.last_tick = time.time()

    def assign(self, mission_id: str, route: list):
        self.assigned_mission = mission_id
        self.route = route
        self.route_progress_index = 0
        self.segment_progress = 0.0
        self.current_node = route[0] if route else self.current_node
        self.status = "EN_ROUTE"
        self.last_tick = time.time()

    def reroute(self, new_route: list):
        """Splice the ambulance onto a new route starting from its current
        node (used after re-optimization mid-mission)."""
        if self.current_node in new_route:
            idx = new_route.index(self.current_node)
            self.route = new_route[idx:]
        else:
            self.route = [self.current_node] + new_route
        self.route_progress_index = 0
        self.segment_progress = 0.0

    def reset(self, base_node="A"):
        self.current_node = base_node
        self.status = "IDLE"
        self.assigned_mission = None
        self.route = []
        self.route_progress_index = 0
        self.segment_progress = 0.0
        self.eta_min = None

    def tick(self, city_graph, dt_seconds: float):
        """Advance the ambulance along its route by dt_seconds of simulated
        time. Returns True if it just arrived at the final destination."""
        if self.status != "EN_ROUTE" or not self.route or self.route_progress_index >= len(self.route) - 1:
            return False

        u = self.route[self.route_progress_index]
        v = self.route[self.route_progress_index + 1]
        edge = city_graph.edge_between(u, v)
        if edge is None or edge["blocked"]:
            return False  # disrupted; caller should trigger re-optimization

        edge_time_min = travel_time_minutes(edge)
        if edge_time_min <= 0 or edge_time_min == float("inf"):
            edge_time_min = 0.5
        edge_time_sec = edge_time_min * 60

        self.segment_progress += dt_seconds / edge_time_sec
        if self.segment_progress >= 1.0:
            self.segment_progress = 0.0
            self.route_progress_index += 1
            self.current_node = self.route[self.route_progress_index]
            if self.route_progress_index >= len(self.route) - 1:
                self.status = "ARRIVED"
                return True
        return False

    def position(self, city_graph):
        """Interpolated lat/lon for smooth frontend animation."""
        if self.route_progress_index >= len(self.route) - 1:
            n = city_graph.nodes[self.current_node]
            return {"lat": n["lat"], "lon": n["lon"]}
        u = city_graph.nodes[self.route[self.route_progress_index]]
        v = city_graph.nodes[self.route[self.route_progress_index + 1]]
        t = self.segment_progress
        return {
            "lat": u["lat"] + (v["lat"] - u["lat"]) * t,
            "lon": u["lon"] + (v["lon"] - u["lon"]) * t,
        }

    def to_dict(self, city_graph):
        pos = self.position(city_graph)
        return {
            "ambulance_id": self.ambulance_id,
            "status": self.status,
            "current_node": self.current_node,
            "assigned_mission": self.assigned_mission,
            "route": self.route,
            "route_progress_index": self.route_progress_index,
            "segment_progress": round(self.segment_progress, 3),
            "position": pos,
            "eta_min": self.eta_min,
        }
