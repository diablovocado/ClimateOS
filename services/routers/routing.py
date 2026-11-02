"""
Router: Safe Routing Engine
Endpoints:
  POST /api/routes/safe-route — calculate safe evacuation route avoiding flooded roads & bridges
  GET  /api/routes/safe-route — query-param accessible safe route calculation
  POST /api/routes/safe       — backwards-compatible route endpoint
"""

import os
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services.routing.safe_route import safe_route_engine

router = APIRouter()

# ---------------------------------------------------------------------------
# Load shelter list for validation
# ---------------------------------------------------------------------------
_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/shelters.json")
_SHELTERS: list = []
if os.path.exists(_DATA_PATH):
    with open(_DATA_PATH, "r", encoding="utf-8") as _f:
        _SHELTERS = json.load(_f)


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------
class SafeRouteIn(BaseModel):
    origin_lat: float = Field(..., description="Citizen origin latitude")
    origin_lng: float = Field(..., description="Citizen origin longitude")
    shelter_id: Optional[str] = Field(None, description="Target destination shelter ID")
    destination_id: Optional[str] = Field(None, description="Target destination shelter ID (alias)")
    travel_mode: Optional[str] = Field("vehicle", description="Travel mode: 'vehicle' or 'pedestrian'")
    mode: Optional[str] = Field(None, description="Travel mode alias")
    blocked_roads: Optional[List[str]] = Field(None, description="List of road names to avoid or mark blocked")


def _validate_and_compute_route(
    origin_lat: float,
    origin_lng: float,
    shelter_id: Optional[str],
    destination_id: Optional[str],
    travel_mode: Optional[str],
    mode: Optional[str],
    blocked_roads: Optional[List[str]] = None,
):
    # 1. Coordinate range validation
    if not (-90.0 <= origin_lat <= 90.0 and -180.0 <= origin_lng <= 180.0):
        raise HTTPException(
            status_code=400,
            detail="Invalid coordinates: latitude must be between -90 and 90, longitude between -180 and 180.",
        )

    # 2. Service area boundary check (Riverdale / Pune metropolitan area or Bangalore demo coordinates)
    in_riverdale = (18.2 <= origin_lat <= 18.8 and 73.6 <= origin_lng <= 74.1)
    in_demo_seed = (12.8 <= origin_lat <= 13.2 and 77.4 <= origin_lng <= 77.8)
    if not (in_riverdale or in_demo_seed):
        raise HTTPException(
            status_code=400,
            detail="Coordinates outside operational service area (Riverdale metropolitan region).",
        )

    # 3. Target shelter validation
    target_id = shelter_id or destination_id
    if not target_id:
        raise HTTPException(
            status_code=400,
            detail="Target shelter ID (shelter_id or destination_id) is required.",
        )

    shelter = next((s for s in _SHELTERS if s["id"] == target_id), None)
    if shelter is None and target_id not in safe_route_engine.shelter_node_map:
        raise HTTPException(
            status_code=404,
            detail=f"Shelter '{target_id}' not found",
        )

    # 4. Travel mode validation
    normalized_mode = (travel_mode or mode or "vehicle").lower().strip()
    if normalized_mode not in ("vehicle", "pedestrian", "walking", "driving", "car", "foot"):
        raise HTTPException(
            status_code=400,
            detail="Invalid travel mode. Supported modes are 'vehicle' and 'pedestrian'.",
        )
    if normalized_mode in ("walking", "foot"):
        normalized_mode = "pedestrian"
    elif normalized_mode in ("driving", "car"):
        normalized_mode = "vehicle"

    # 5. Route calculation with safe_route_engine
    route = safe_route_engine.calculate_safe_route(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        destination_id=target_id,
        blocked_roads=blocked_roads,
        travel_mode=normalized_mode,
    )

    # 6. Unavailable route check: NEVER fabricate a safe route
    if route is None:
        shelter_name = shelter["name"] if shelter else target_id
        raise HTTPException(
            status_code=404,
            detail=f"No safe route available to {shelter_name}. All connecting paths are impassable due to flood hazards and closures.",
        )

    return route


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/routes/safe-route")
def post_safe_route(payload: SafeRouteIn):
    """
    POST /api/routes/safe-route
    Calculate safest route to target shelter avoiding flooded zones & blocked bridges.
    Returns valid GeoJSON LineString Feature with distance, duration, risk score, and travel mode.
    """
    return _validate_and_compute_route(
        origin_lat=payload.origin_lat,
        origin_lng=payload.origin_lng,
        shelter_id=payload.shelter_id,
        destination_id=payload.destination_id,
        travel_mode=payload.travel_mode,
        mode=payload.mode,
        blocked_roads=payload.blocked_roads,
    )


@router.get("/routes/safe-route")
def get_safe_route(
    origin_lat: float = Query(..., description="Citizen origin latitude"),
    origin_lng: float = Query(..., description="Citizen origin longitude"),
    shelter_id: Optional[str] = Query(None, description="Target shelter ID"),
    destination_id: Optional[str] = Query(None, description="Target shelter ID alias"),
    travel_mode: Optional[str] = Query("vehicle", description="Travel mode: 'vehicle' or 'pedestrian'"),
    mode: Optional[str] = Query(None, description="Travel mode alias"),
):
    """
    GET /api/routes/safe-route
    Query-param accessible endpoint conforming to existing API conventions.
    """
    return _validate_and_compute_route(
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        shelter_id=shelter_id,
        destination_id=destination_id,
        travel_mode=travel_mode,
        mode=mode,
    )


@router.post("/routes/safe")
def post_safe_route_legacy(payload: SafeRouteIn):
    """
    POST /api/routes/safe (Backwards compatibility endpoint)
    """
    return post_safe_route(payload)
