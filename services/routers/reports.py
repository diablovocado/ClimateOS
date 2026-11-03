"""
Router: Citizen Reports & Incidents
Endpoints:
  POST /api/reports          — submit a citizen report; verified with ReportVerifier and ranked by PriorityRanker
  GET  /api/incidents        — return ranked incidents with confidence labels and priority scores
"""

import json
import os
import random
import string
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

from services.verification.verifier import report_verifier
from services.priority_engine.ranker import priority_ranker

router = APIRouter()

# ---------------------------------------------------------------------------
# Load initial mock incidents
# ---------------------------------------------------------------------------
_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/incidents.json")

with open(_DATA_PATH, "r") as _f:
    _INCIDENTS: list = json.load(_f)

# Ensure incidents are sorted by priority_score descending initially
_INCIDENTS.sort(key=lambda i: i.get("priority_score", 0), reverse=True)

# In-memory store for submitted reports (resets on server restart)
_REPORTS: list = []


# ---------------------------------------------------------------------------
# Pydantic schema for incoming citizen reports
# ---------------------------------------------------------------------------
class CitizenReportIn(BaseModel):
    category: str          # flood | trapped | road | fire | medical | power_failure | water_shortage | infrastructure
    description: str
    location: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    zone_id: Optional[str] = None
    trapped_count: Optional[int] = 0
    injured_count: Optional[int] = 0
    photo_attached: Optional[bool] = False
    reporter_id: Optional[str] = "anonymous"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _random_id(prefix: str) -> str:
    suffix = "".join(random.choices(string.digits, k=4))
    return f"{prefix}-{suffix}"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/reports")
def submit_report(body: CitizenReportIn):
    """
    Accept a citizen disaster report.
    Cross-references report attributes with ReportVerifier and computes
    transparent impact priority score using PriorityRanker.
    """
    report_dict = body.model_dump()
    report_dict["id"] = _random_id("REP")
    report_dict["submitted_at"] = datetime.now(timezone.utc).isoformat()
    # Map photo_attached to has_photo for ReportVerifier
    report_dict["has_photo"] = bool(body.photo_attached)
    report_dict["photo_attached"] = bool(body.photo_attached)
    if body.photo_attached:
        report_dict["photo_url"] = f"https://storage.climateos.org/evidence/{report_dict['id']}.jpg"

    # AI Report Verification Engine
    verification = report_verifier.verify(report_dict)

    # Impact & Priority Ranking Engine
    priority_input = {
        "category": body.category,
        "trapped_count": body.trapped_count or 0,
        "injured_count": body.injured_count or 0,
        "confidence_score": verification["confidence_score"]
    }
    priority = priority_ranker.rank_incident(priority_input)

    raw_status = verification["status"]
    status_label = {
        "HIGH_CONFIDENCE": "High Confidence",
        "NEEDS_REVIEW": "Needs Review",
        "LOW_CONFIDENCE": "Low Confidence"
    }.get(raw_status, "Needs Review")
    verification["confidence_label"] = status_label
    verification["verification_status"] = raw_status

    severity = "CRITICAL" if priority >= 75.0 else ("HIGH" if priority >= 50.0 else "MODERATE")
    is_verified = bool(verification["confidence_score"] >= 85.0)

    # Derive incident and persist in priority order
    incident = {
        "id": _random_id("INC"),
        "category": body.category,
        "severity": severity,
        "location": body.location or "Unknown",
        "lat": body.lat,
        "lng": body.lng,
        "description": body.description,
        "status": "ACTIVE",
        "confidence_score": verification["confidence_score"],
        "confidence_label": status_label,
        "verification_status": raw_status,
        "verification_factors": verification.get("factors", []),
        "priority_score": priority,
        "trapped_count": body.trapped_count or 0,
        "injured_count": body.injured_count or 0,
        "zone_id": body.zone_id,
        "reported_by": body.reporter_id or "citizen-app",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verified": is_verified,
        "ranking_method": "Multi-factor heuristic impact scoring (trapped, injured, confidence, category weight)",
        "prediction_disclaimer": "Heuristic emergency triage priority calculation; not a machine-learned casualty forecast.",
    }

    _INCIDENTS.append(incident)
    _INCIDENTS.sort(key=lambda i: i.get("priority_score", 0), reverse=True)
    _REPORTS.append(report_dict)

    return {
        "report":       report_dict,
        "verification": verification,
        "incident":     incident,
    }


@router.get("/incidents")
def get_incidents():
    """
    Return all incidents ranked by priority_score (descending).
    Confidence labels: High Confidence | Needs Review | Low Confidence
    """
    sorted_incidents = sorted(_INCIDENTS, key=lambda i: i.get("priority_score", 0), reverse=True)
    return sorted_incidents

