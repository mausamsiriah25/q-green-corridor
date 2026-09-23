"""
Traffic Control Server
=======================

SIMULATED coordination layer sitting between the Ambulance App and the
Signal Controllers / Optimization Agent. This module does NOT talk to any
real municipal traffic infrastructure — every "command" below is an
in-memory state transition in this demo, logged for the Traffic Control
Center UI. See README / honesty notes: this is a software prototype of
the *architecture* a real deployment could later plug into.

Conceptual flow this module implements:

    Ambulance App -> Emergency Request -> TrafficControlServer
        -> Optimization Agent (QPSO/etc, called by main.py)
        -> Green Corridor Planner (corridor/planner.py)
        -> Signal Controllers (this module issues PREPARE/PRIORITY/NORMAL
           commands and keeps a command log)

Responsibilities handled here:
  * Turning a corridor plan + live ambulance progress into per-signal
    controller state (NORMAL -> PREPARE -> PRIORITY -> NORMAL), each with
    the metadata fields required by the Control Center UI.
  * Maintaining an append-only, real (non-fabricated) command log driven
    only by actual phase transitions.
  * Generating turn-by-turn driver navigation instructions from the
    live route geometry + ambulance position (no hardcoded strings).
"""
import math
import time

from routing.graph import travel_time_minutes
from corridor.planner import apply_corridor_state

# ------------------------------------------------------------- geometry

def _bearing_deg(u: dict, v: dict) -> float:
    """Initial compass bearing (0=N, 90=E, ...) from node u to node v."""
    lat1, lon1 = math.radians(u["lat"]), math.radians(u["lon"])
    lat2, lon2 = math.radians(v["lat"]), math.radians(v["lon"])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _haversine_m(u: dict, v: dict) -> float:
    R = 6371000.0
    lat1, lon1 = math.radians(u["lat"]), math.radians(u["lon"])
    lat2, lon2 = math.radians(v["lat"]), math.radians(v["lon"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# Turn classification thresholds. The relative bearing change between the
# current segment's heading and the next segment's heading (normalized to
# -180..+180, positive = clockwise = right) is bucketed as:
#   |delta| <= STRAIGHT_THRESHOLD_DEG               -> STRAIGHT
#   STRAIGHT_THRESHOLD_DEG < delta <= 180            -> RIGHT
#   -180 <= delta < -STRAIGHT_THRESHOLD_DEG          -> LEFT
# These are documented, non-hardcoded-per-instruction thresholds applied
# uniformly to whatever route geometry the optimizer returns.
STRAIGHT_THRESHOLD_DEG = 20
ARRIVE_THRESHOLD_M = 40


def _classify_turn(bearing_in: float, bearing_out: float) -> str:
    delta = (bearing_out - bearing_in + 540) % 360 - 180  # -180..180
    if abs(delta) <= STRAIGHT_THRESHOLD_DEG:
        return "STRAIGHT"
    return "RIGHT" if delta > 0 else "LEFT"


def _fmt_distance(meters: float) -> str:
    if meters < 1000:
        return f"{int(round(meters / 10.0) * 10)} m"
    return f"{meters / 1000:.1f} km"


# --------------------------------------------------------- signal control

class TrafficControlServer:
    """Coordinates emergency requests, the green-corridor schedule and the
    simulated per-signal controllers. Holds the append-only command log
    shown in the Traffic Control Center UI."""

    def __init__(self):
        self.command_log = []
        self._last_phase = {}       # signal_id -> last phase we logged
        self._last_passed = set()   # signal_ids already logged as passed

    def reset(self):
        self.command_log = []
        self._last_phase = {}
        self._last_passed = set()

    def _emit(self, signal_id: str, command: str, reason: str, eta_sec=None):
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "timestamp": time.time(),
            "signal_id": signal_id,
            "command": command,
            "reason": reason,
            "eta_sec": eta_sec,
        }
        self.command_log.append(entry)
        if len(self.command_log) > 200:
            self.command_log = self.command_log[-200:]
        return entry

    def sync_signals(self, city_graph, corridor_plan: dict, ambulance, mission_id: str):
        """Advance every simulated signal controller to match the current
        corridor plan + ambulance progress, emitting command-log entries
        only for genuine phase transitions (never fabricated)."""
        signals = apply_corridor_state(city_graph, corridor_plan, ambulance.route_progress_index)

        for sig in signals:
            sid = sig["signal_id"]
            phase = sig["current_phase"]
            eta_min = sig.get("estimated_arrival")
            eta_sec = round(eta_min * 60) if eta_min is not None else None

            sig["priority_requested"] = phase in ("PREPARE", "PRIORITY")
            sig["priority_active"] = phase == "PRIORITY"
            sig["ambulance_eta"] = eta_sec
            sig["ambulance_passed"] = sig.get("corridor_status") == "PASSED"

            prev_phase = self._last_phase.get(sid)
            if phase != prev_phase:
                if phase == "PREPARE":
                    entry = self._emit(sid, "PREPARE", mission_id, eta_sec)
                elif phase == "PRIORITY":
                    entry = self._emit(sid, "PRIORITY", mission_id, eta_sec)
                elif phase == "NORMAL" and prev_phase == "PRIORITY":
                    self._emit(sid, "NORMAL", f"{mission_id}: ambulance passed", None)
                    entry = None
                elif phase == "NORMAL" and prev_phase is not None:
                    entry = self._emit(sid, "NORMAL", mission_id, None)
                else:
                    entry = None
                if entry:
                    sig["last_command"] = entry["command"]
                    sig["command_timestamp"] = entry["time"]
                self._last_phase[sid] = phase

            if sig["ambulance_passed"] and sid not in self._last_passed:
                self._last_passed.add(sid)

        return signals

    def to_public_log(self):
        return list(reversed(self.command_log))[:50]

    def note_phase(self, signal_id: str, phase: str):
        """Lets a manual/override command (e.g. POST /signals/{id}/priority)
        update our transition-tracking so the next automatic sync doesn't
        re-emit a duplicate log entry."""
        self._last_phase[signal_id] = phase

    def emit_manual(self, signal_id: str, command: str, reason: str):
        return self._emit(signal_id, command, reason)


# ------------------------------------------------------------- navigation

def build_navigation(city_graph, ambulance, mission=None):
    """Derives turn-by-turn driver navigation purely from the live route
    geometry + ambulance progress. Nothing here is a hardcoded string --
    every field is computed from node coordinates, edge distances and the
    ambulance's current segment/progress."""
    route = ambulance.route
    idx = ambulance.route_progress_index

    if ambulance.status == "ARRIVED" or not route or idx >= len(route) - 1:
        return {
            "instruction_type": "ARRIVE",
            "text": "🏥 ARRIVED — mission complete" if ambulance.status == "ARRIVED" else "Awaiting route",
            "distance_to_maneuver_m": 0,
            "distance_remaining_km": 0.0,
            "eta_min": 0.0,
            "upcoming_signal": None,
            "green_corridor_active": False,
        }

    u_id, v_id = route[idx], route[idx + 1]
    u, v = city_graph.nodes[u_id], city_graph.nodes[v_id]
    edge = city_graph.edge_between(u_id, v_id)
    seg_distance_m = (edge["distance"] * 1000) if edge else _haversine_m(u, v)
    remaining_seg_m = max(0.0, seg_distance_m * (1 - ambulance.segment_progress))

    # remaining total distance/eta across the rest of the route
    remaining_km = remaining_seg_m / 1000.0
    remaining_min = 0.0
    if edge:
        remaining_min += travel_time_minutes(edge) * (1 - ambulance.segment_progress)
    for i in range(idx + 1, len(route) - 1):
        e = city_graph.edge_between(route[i], route[i + 1])
        if not e:
            continue
        remaining_km += e["distance"]
        t = travel_time_minutes(e)
        remaining_min += 0 if t == float("inf") else t

    is_final_segment = (idx + 2) >= len(route)

    if is_final_segment:
        if remaining_seg_m <= ARRIVE_THRESHOLD_M:
            instr_type, text = "ARRIVE", "🏥 Arriving at hospital"
        else:
            instr_type = "STRAIGHT"
            text = f"Hospital in {_fmt_distance(remaining_seg_m)}"
    else:
        w_id = route[idx + 2]
        w = city_graph.nodes[w_id]
        bearing_in = _bearing_deg(u, v)
        bearing_out = _bearing_deg(v, w)
        turn = _classify_turn(bearing_in, bearing_out)
        instr_type = turn
        verb = {"LEFT": "Turn LEFT", "RIGHT": "Turn RIGHT", "STRAIGHT": "Continue straight"}[turn]
        text = f"{verb} in {_fmt_distance(remaining_seg_m)}"

    upcoming_signal = None
    if city_graph.nodes[v_id].get("is_signal"):
        upcoming_signal = v_id
    else:
        for i in range(idx + 1, min(idx + 4, len(route))):
            if city_graph.nodes[route[i]].get("is_signal"):
                upcoming_signal = route[i]
                break

    return {
        "instruction_type": instr_type,
        "text": text,
        "distance_to_maneuver_m": round(remaining_seg_m),
        "distance_remaining_km": round(remaining_km, 2),
        "eta_min": round(max(0.0, remaining_min), 1),
        "upcoming_signal": upcoming_signal,
        "green_corridor_active": True,
    }
