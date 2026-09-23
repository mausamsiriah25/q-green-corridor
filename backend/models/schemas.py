from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class StartEmergencyRequest(BaseModel):
    severity: str = "CRITICAL"
    pickup: str = "A"
    destination: str = "H"
    ambulance_id: str = "AMB-01"


class IncidentRequest(BaseModel):
    mission_id: str
    edge_id: Optional[str] = None  # if omitted, an edge on the current route is auto-selected


class OptimizeRequest(BaseModel):
    mission_id: str
    algorithm: str = "QPSO"


class BenchmarkRequest(BaseModel):
    mission_id: Optional[str] = None
    source: str = "A"
    destination: str = "H"
    algorithms: List[str] = ["DIJKSTRA", "ASTAR", "QPSO", "PSO", "GA"]


class CorridorRequest(BaseModel):
    mission_id: str


class SignalCommandRequest(BaseModel):
    command: str = "PRIORITY"  # NORMAL | PREPARE | PRIORITY
    reason: Optional[str] = None
