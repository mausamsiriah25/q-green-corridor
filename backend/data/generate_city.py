"""
Generates the simulated city network for Q-GREEN CORRIDOR.
Deterministic (fixed seed) so the demo is reproducible.

Run: python generate_city.py
Writes: city_network.json
"""
import json
import random
import math

random.seed(42)

# 26 nodes laid out in a rough grid with jitter, using lat/lon-like coords
# centered arbitrarily around a fictional city (not a real place)
BASE_LAT, BASE_LON = 21.1458, 79.0882  # Nagpur-ish, purely for realistic map feel
GRID_COLS = 6
GRID_ROWS = 5

NODE_NAMES = [
    "A",  "N2",  "N3",  "N4",  "N5",  "N6",
    "N7", "S2",  "N9",  "S5",  "N11", "N12",
    "N13","N14", "S8",  "N16", "N17", "N18",
    "N19","N20", "N21", "N22", "N23", "N24",
    "N25", "H",
]

SIGNAL_NODES = {"S2", "S5", "S8"}  # signalized intersections used by the primary demo route


def build_nodes():
    nodes = {}
    idx = 0
    for r in range(GRID_ROWS):
        for c in range(GRID_COLS):
            if idx >= len(NODE_NAMES):
                break
            name = NODE_NAMES[idx]
            jitter_lat = random.uniform(-0.003, 0.003)
            jitter_lon = random.uniform(-0.003, 0.003)
            lat = BASE_LAT + r * 0.012 + jitter_lat
            lon = BASE_LON + c * 0.014 + jitter_lon
            nodes[name] = {
                "id": name,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "type": "hospital" if name == "H" else ("ambulance_base" if name == "A" else
                        ("signal" if name in SIGNAL_NODES else "intersection")),
                "is_signal": name in SIGNAL_NODES,
            }
            idx += 1
    return nodes


def haversine_km(a, b):
    R = 6371.0
    lat1, lon1 = math.radians(a["lat"]), math.radians(a["lon"])
    lat2, lon2 = math.radians(b["lat"]), math.radians(b["lon"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


ROAD_NAME_POOL = [
    "MG Road", "Ring Road", "Central Ave", "Lake View Road", "Station Road",
    "Hospital Link", "Civil Lines Road", "Market Street", "Highway Bypass",
    "College Road", "Park Avenue", "River Road", "Old City Road", "New Colony Road",
    "Junction Street", "Green Belt Road", "Industrial Road", "Airport Road",
]


def build_edges(nodes):
    """
    Build a connected, redundant road network: a grid backbone plus extra
    cross-links so multiple distinct paths exist between A and H (needed so
    an injected incident always has a real alternative).
    """
    edges = []
    edge_id = 0
    names = list(nodes.keys())
    grid = [names[i:i + GRID_COLS] for i in range(0, len(names), GRID_COLS)]

    existing_pairs = set()

    def add_edge(u, v, road_name=None, one_way=False):
        nonlocal edge_id
        if u not in nodes or v not in nodes:
            return
        if (u, v) in existing_pairs or (v, u) in existing_pairs:
            return  # never create parallel duplicate roads between the same pair
        existing_pairs.add((u, v))
        dist = round(haversine_km(nodes[u], nodes[v]) * random.uniform(1.15, 1.35), 3)  # road != straight line
        base_speed = random.choice([30, 35, 40, 45, 50])  # km/h
        traffic_level = round(random.uniform(0.1, 0.5), 2)
        signal_delay = 25 if (nodes[u]["is_signal"] or nodes[v]["is_signal"]) else 0
        edge = {
            "edge_id": f"E{edge_id:03d}",
            "source": u,
            "destination": v,
            "distance": dist,
            "base_speed": base_speed,
            "current_speed": base_speed,
            "traffic_level": traffic_level,
            "signal_delay": signal_delay,
            "blocked": False,
            "one_way": one_way,
            "road_name": road_name or random.choice(ROAD_NAME_POOL),
        }
        edges.append(edge)
        edge_id += 1
        # reverse direction (two-way road) unless explicitly one-way
        if not one_way:
            rev = dict(edge)
            rev["edge_id"] = f"E{edge_id:03d}"
            rev["source"], rev["destination"] = v, u
            edges.append(rev)
            edge_id += 1

    # Grid backbone: horizontal + vertical links
    for r, row in enumerate(grid):
        for c in range(len(row) - 1):
            add_edge(row[c], row[c + 1])
    for c in range(GRID_COLS):
        col_nodes = [grid[r][c] for r in range(len(grid)) if c < len(grid[r])]
        for r in range(len(col_nodes) - 1):
            add_edge(col_nodes[r], col_nodes[r + 1])

    # Diagonal shortcuts / redundant cross-links for alternative routes
    extra_links = [
        ("A", "S2"), ("A", "N7"), ("S2", "N9"), ("N9", "S5"),
        ("S5", "N14"), ("N14", "S8"), ("S8", "H"), ("N6", "S5"),
        ("N4", "N11"), ("N12", "S8"), ("N17", "N24"), ("N13", "N20"),
        ("N16", "N23"), ("N3", "N9"), ("N18", "N25"), ("N20", "H"),
        ("S2", "N4"), ("N11", "S5"), ("S5", "N18"), ("S8", "N21"),
        ("N22", "H"), ("N9", "N16"),
    ]
    for u, v in extra_links:
        add_edge(u, v)

    return edges


def main():
    nodes = build_nodes()
    edges = build_edges(nodes)
    signals = [
        {
            "signal_id": f"SIG-{n}",
            "node": n,
            "current_phase": "NORMAL",
            "normal_state": "NORMAL",
            "priority_state": "PRIORITY",
            "estimated_arrival": None,
            "corridor_status": "INACTIVE",
        }
        for n in nodes if nodes[n]["is_signal"]
    ]

    network = {
        "nodes": nodes,
        "edges": edges,
        "signals": signals,
        "ambulance_base": "A",
        "hospital": "H",
        "meta": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "seed": 42,
        },
    }

    with open("city_network.json", "w") as f:
        json.dump(network, f, indent=2)

    print(f"Generated {len(nodes)} nodes, {len(edges)} directed edges, {len(signals)} signals -> city_network.json")


if __name__ == "__main__":
    main()
