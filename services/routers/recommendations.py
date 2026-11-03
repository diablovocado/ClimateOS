"""
Router: AI Recommendations (Human-in-the-loop)
Endpoints:
  GET  /api/recommendations
  POST /api/recommendations/{id}/decision   — approve or reject
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.recommendation.advisor import recommendation_advisor
from services.routers.risk import get_all_calculated_zones

router = APIRouter()

# ---------------------------------------------------------------------------
# Load mock recommendations
# ---------------------------------------------------------------------------
_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/recommendations.json")

with open(_DATA_PATH, "r") as _f:
    _RECS: list = json.load(_f)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
class DecisionPayload(BaseModel):
    decision: str          # "APPROVED" | "REJECTED"
    operator_id: str = "gov-operator-1"
    notes: str = ""


# ---------------------------------------------------------------------------
# Recommendation Generator & Deduplication Engine
# ---------------------------------------------------------------------------
def _sync_recommendations() -> List[Dict[str, Any]]:
    """
    Sync dynamic recommendations from RecommendationAdvisor with stored recommendations.
    Triggers when zone risk >= 75.0 or when verified life-threatening incidents occur.
    Prevents duplicate pending recommendations and preserves human approval/rejection decisions.
    """
    zones = get_all_calculated_zones()
    from services.routers.reports import _INCIDENTS

    generated = recommendation_advisor.generate(zones, _INCIDENTS)
    existing_ids = {r["id"] for r in _RECS}

    # Track pending conditions to prevent duplicates for the same condition/incident
    pending_evac_zones = {
        r.get("target_zone") for r in _RECS
        if r.get("decision_status") == "PENDING" and ("EVAC" in r.get("id", "") or r.get("type") == "EVACUATION")
    }
    pending_rescue_targets = {
        r.get("id") for r in _RECS
        if r.get("decision_status") == "PENDING" and ("RESCUE" in r.get("id", "") or r.get("type") == "RESCUE_DEPLOYMENT")
    }

    for gen in generated:
        rec_id = gen["id"]
        if rec_id in existing_ids:
            continue

        target_zone = gen.get("target_zone")
        is_evac = "EVAC" in rec_id
        is_rescue = "RESCUE" in rec_id

        # Prevent duplicate pending recommendations for the same zone evacuation or rescue incident
        if is_evac and target_zone in pending_evac_zones:
            continue
        if is_rescue and rec_id in pending_rescue_targets:
            continue

        priority = "CRITICAL" if gen.get("high_priority") else "HIGH"
        rec_type = "EVACUATION" if is_evac else (
            "RESCUE_DEPLOYMENT" if is_rescue else (
                "SHELTER_ACTIVATION" if "SHELTER" in rec_id else "ADVISORY"
            )
        )

        normalized_rec = {
            "id": rec_id,
            "type": rec_type,
            "priority": priority,
            "title": gen.get("title", ""),
            "description": gen.get("reason", ""),
            "reason": gen.get("reason", ""),
            "target_zone": target_zone,
            "affected_population": 14200 if target_zone == "zone-a" else 5000,
            "action_text": gen.get("action_text", "Review Action"),
            "decision_status": "PENDING",
            "confidence": 95 if gen.get("high_priority") else 88,
            "xai_factors": gen.get("xai_rationale", {}),
            "xai_rationale": gen.get("xai_rationale", {}),
            "high_priority": gen.get("high_priority", False),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        _RECS.append(normalized_rec)
        existing_ids.add(rec_id)
        if is_evac and target_zone:
            pending_evac_zones.add(target_zone)
        if is_rescue:
            pending_rescue_targets.add(rec_id)

    priority_order = {"CRITICAL": 0, "HIGH": 1, "MODERATE": 2, "LOW": 3}
    return sorted(_RECS, key=lambda r: priority_order.get(r.get("priority", "LOW"), 4))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/recommendations")
def get_recommendations():
    """
    Return all AI-generated recommendations sorted by priority (CRITICAL, HIGH, MODERATE, LOW).
    Dynamically generates recommendations from current zone risk scores and incident feed,
    while deduplicating pending recommendations and preserving human decisions.
    """
    return _sync_recommendations()


@router.post("/recommendations/{rec_id}/decision")
def update_decision(rec_id: str, body: DecisionPayload):
    """
    Record a human authority's approve / reject decision on a recommendation.
    Enforces the human-in-the-loop gate: AI recommends, humans decide.
    """
    # Ensure current recommendations are in memory
    _sync_recommendations()

    rec = next((r for r in _RECS if r["id"] == rec_id), None)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Recommendation '{rec_id}' not found")

    if body.decision not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="decision must be 'APPROVED' or 'REJECTED'")

    rec["decision_status"] = body.decision
    rec["decided_by"] = body.operator_id
    rec["decision_notes"] = body.notes
    rec["decided_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "rec_id":    rec_id,
        "decision":  body.decision,
        "status":    "recorded",
        "message":   f"Recommendation {rec_id} has been {body.decision.lower()} by {body.operator_id}.",
    }

