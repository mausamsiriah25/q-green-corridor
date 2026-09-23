"""
LocationMapper -- the ONLY place that translates between real-world
coordinates (as returned by Google Maps / Places / Geocoding, or by
browser GPS) and node ids in our simulated city graph.

This is deliberately kept out of routing/qpso.py and friends: QPSO
never sees latitude/longitude, it only ever sees graph node ids. This
module is the boundary between "real-world location" and "simulated
transportation network" described in the architecture notes.

Responsibilities (see also the frontend googleMaps.js service, which
owns the browser-side address search / geocoding UX):
  * coordinate -> nearest graph node
  * graph node -> coordinate
No network calls happen here -- this is pure geometry over the graph
that is already loaded in memory.
"""
import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


class LocationMapper:
    """Maps real-world coordinates onto the nearest node of a CityGraph,
    and vice versa. Constructed against a live CityGraph instance so it
    always reflects the current network (post-reset, etc.)."""

    def __init__(self, city_graph):
        self.city_graph = city_graph

    def nearest_node(self, lat: float, lon: float) -> dict:
        """Return the closest graph node to (lat, lon), plus how far away
        it actually is -- callers should surface snap_distance_km to the
        user for technical honesty when a real address is far from any
        node in the (necessarily smaller) simulated network."""
        best_id, best_dist = None, float("inf")
        for node_id, data in self.city_graph.nodes.items():
            d = haversine_km(lat, lon, data["lat"], data["lon"])
            if d < best_dist:
                best_id, best_dist = node_id, d
        if best_id is None:
            return None
        node = self.city_graph.nodes[best_id]
        return {
            "node_id": best_id,
            "lat": node["lat"],
            "lon": node["lon"],
            "type": node.get("type", "intersection"),
            "snap_distance_km": round(best_dist, 3),
        }

    def node_coord(self, node_id: str) -> dict:
        node = self.city_graph.nodes.get(node_id)
        if node is None:
            return None
        return {"node_id": node_id, "lat": node["lat"], "lon": node["lon"]}
