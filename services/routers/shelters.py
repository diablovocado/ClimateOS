"""
Router: Shelters
Endpoint: GET /api/shelters
Returns shelter list loaded from data/shelters.json
"""

import json
import os
from fastapi import APIRouter, HTTPException

router = APIRouter()

# ---------------------------------------------------------------------------
# Load mock data
# ---------------------------------------------------------------------------
_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/shelters.json")

with open(_DATA_PATH, "r") as _f:
    _SHELTERS: list = json.load(_f)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/shelters")
def get_shelters():
    """
    Return all shelters with capacity, occupancy, and status.

    TODO (Shelter Intelligence): Connect to live shelter management system.
    Occupancy should update in real-time as evacuees check in/out.
    Add route_safe flag per shelter based on current road blockage data.
    """
    return _SHELTERS


@router.get("/shelters/{shelter_id}")
def get_shelter(shelter_id: str):
    """
    Return a single shelter by ID.
    """
    shelter = next((s for s in _SHELTERS if s["id"] == shelter_id), None)
    if shelter is None:
        raise HTTPException(status_code=404, detail=f"Shelter '{shelter_id}' not found")
    return shelter


def update_shelter_status(shelter_identifier: str, status: str = "OPEN", occupancy: int = None) -> dict:
    """
    Update status and occupancy of a shelter matching by ID, name, or zone.
    Returns the updated shelter dictionary if found.
    """
    ident_lower = shelter_identifier.lower().strip()
    target = None
    for s in _SHELTERS:
        if (s["id"].lower() == ident_lower or
            ident_lower in s["id"].lower() or
            ident_lower in s["name"].lower() or
            (s.get("zone_id") and ident_lower == s["zone_id"].lower())):
            target = s
            break

    if target:
        target["status"] = status
        if occupancy is not None:
            target["occupancy"] = occupancy
        return target
    return None

