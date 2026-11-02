from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class User(BaseModel):
    id: str
    role: str = "citizen"  # "citizen", "responder", "authority"
    location: Optional[Dict[str, float]] = None
    preferences: Optional[Dict[str, Any]] = None

class CitizenReport(BaseModel):
    id: Optional[str] = None
    reporter_id: str = "citizen-anon"
    category: str  # "flood", "trapped", "road", "fire", "medical"
    location: str
    lat: float
    lng: float
    description: str
    trapped_count: int = 0
    injured_count: int = 0
    photo_url: Optional[str] = None
    voice_url: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class Verification(BaseModel):
    report_id: str
    status: str  # "HIGH_CONFIDENCE", "NEEDS_REVIEW", "LOW_CONFIDENCE"
    confidence_score: float
    factors: List[str]
    model_version: str = "v1.0.0"

class Incident(BaseModel):
    id: str
    category: str
    severity: str
    location: str
    lat: float
    lng: float
    description: str
    status: str = "ACTIVE"  # "ACTIVE", "RESOLVED"
    confidence_score: float
    priority_score: float
    trapped_count: int = 0
    injured_count: int = 0

class RiskZone(BaseModel):
    id: str
    name: str
    score: float
    status: str  # "HIGH RISK", "MEDIUM RISK", "MODERATE RISK", "LOW RISK"
    severity: str
    confidence: float
    pop_at_risk: int
    terrain: str
    bounds: List[List[float]]

class Shelter(BaseModel):
    id: str
    name: str
    location: str
    lat: float
    lng: float
    capacity: int
    occupancy: int
    accessibility: str
    status: str  # "OPEN", "NEAR_CAPACITY", "FULL"

class Resource(BaseModel):
    id: str
    type: str
    name: str
    quantity: int
    lat: float
    lng: float
    availability: str  # "AVAILABLE", "DEPLOYED"

class Recommendation(BaseModel):
    id: str
    high_priority: bool
    title: str
    reason: str
    action_text: str
    target_zone: str
    decision_status: str = "PENDING"  # "PENDING", "ACCEPTED", "REJECTED"
    xai_rationale: Dict[str, Any]

class SafeRouteRequest(BaseModel):
    origin_lat: float
    origin_lng: float
    destination_id: Optional[str] = None
    shelter_id: Optional[str] = None
    travel_mode: Optional[str] = "vehicle"
    mode: Optional[str] = None
    blocked_roads: List[str] = []

class SafeRouteResponse(BaseModel):
    route_name: str
    distance_km: float
    estimated_minutes: int
    risk_level: str
    status_color: str
    avoided_hazards: List[str]
    type: Optional[str] = "Feature"
    geometry: Optional[Dict[str, Any]] = None
    duration_minutes: Optional[int] = None
    risk_score: Optional[float] = None
    travel_mode: Optional[str] = "vehicle"
    status: Optional[str] = None
    is_simulated: Optional[bool] = True
    warnings: Optional[List[str]] = []
    safety_disclaimer: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    shelter: Optional[Dict[str, Any]] = None

class SimulationEvent(BaseModel):
    step: int
    title: str
    description: str
    rainfall_mm_hr: float
    water_level_m: float
    new_report: Optional[Dict[str, Any]] = None
    blocked_road: Optional[str] = None
