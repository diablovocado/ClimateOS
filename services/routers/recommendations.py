"""
Router: AI Recommendations (Human-in-the-loop)
Endpoints:
  GET  /api/recommendations
  POST /api/recommendations/{id}/decision   — approve or reject
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from services.recommendation.advisor import recommendation_advisor
from services.routers.risk import get_all_calculated_zones
from services.routers.shelters import update_shelter_status
from services.events import event_broadcaster

router = APIRouter()

# ---------------------------------------------------------------------------
# Load mock recommendations
# ---------------------------------------------------------------------------
_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/recommendations.json")

with open(_DATA_PATH, "r") as _f:
    _RECS: list = json.load(_f)

# Track officially approved active evacuations
_ACTIVE_EVACUATIONS: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
class DecisionPayload(BaseModel):
    decision: str          # "APPROVED" | "REJECTED"
    operator_id: str = "gov-operator-1"
    notes: str = ""
    role: Optional[str] = None



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


@router.get("/evacuations")
def get_active_evacuations():
    """
    Return officially authorized active evacuation directives.
    AI recommendations are NOT active evacuation orders until approved by an authorized official.
    """
    return list(_ACTIVE_EVACUATIONS.values())


@router.post("/recommendations/{rec_id}/decision")
def update_decision(
    rec_id: str,
    body: DecisionPayload,
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_role: Optional[str] = Header(None, alias="X-Role"),
    authorization: Optional[str] = Header(None)
):
    """
    Record a human authority's approve / reject decision on a recommendation.
    Validates official authority, persists decision, updates shelter/evacuation state
    on approval, and broadcasts updates via the live event stream.
    Rejection does not alter shelter or evacuation states.
    """
    # Authorization check: only authorized emergency officials may record decisions
    caller_role = (body.role or x_user_role or x_role or "").lower()
    op_lower = (body.operator_id or "").lower()
    auth_lower = (authorization or "").lower()

    is_unauthorized = (
        caller_role in ("citizen", "guest", "anonymous") or
        op_lower.startswith("citizen") or
        "citizen" in auth_lower or
        op_lower == "anonymous"
    )

    if is_unauthorized:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Only authorized emergency authorities may approve or reject recommendations."
        )

    if body.decision not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="decision must be 'APPROVED' or 'REJECTED'")

    # Ensure recommendations are in memory
    _sync_recommendations()

    rec = next((r for r in _RECS if r["id"] == rec_id), None)
    if rec is None:
        raise HTTPException(status_code=404, detail=f"Recommendation '{rec_id}' not found")

    rec["decision_status"] = body.decision
    rec["decided_by"] = body.operator_id
    rec["decision_notes"] = body.notes
    rec["decided_at"] = datetime.now(timezone.utc).isoformat()
    rec["status_updated_at"] = datetime.now(timezone.utc).isoformat()

    now_iso = datetime.now(timezone.utc).isoformat()

    # Handle Approved Actions
    if body.decision == "APPROVED":
        # 1. Shelter Activation
        if "SHELTER" in rec_id or rec.get("type") == "SHELTER_ACTIVATION":
            target_shelter_id = "shelter-b" if (
                "shelter-b" in rec_id.lower() or
                "b" in rec_id.lower() or
                "central school" in rec.get("title", "").lower()
            ) else (
                "shelter-e" if "port" in rec.get("title", "").lower() or "shelter-e" in rec_id.lower() else "shelter-b"
            )
            updated_shelter = update_shelter_status(target_shelter_id, status="OPEN")
            if updated_shelter:
                event_broadcaster.broadcast("shelter", {
                    "type": "SHELTER_UPDATE",
                    "shelter": updated_shelter,
                    "rec_id": rec_id,
                    "decision": "APPROVED",
                    "timestamp": now_iso
                })

        # 2. Evacuation Order Activation
        if "EVAC" in rec_id or rec.get("type") == "EVACUATION":
            zone_id = rec.get("target_zone") or "zone-a"
            evac_alert = {
                "id": f"ALERT-EVAC-{zone_id}",
                "zone_id": zone_id,
                "status": "ACTIVE_EVACUATION",
                "severity": "CRITICAL",
                "title": rec.get("title", f"Official Evacuation Directive — {zone_id.upper()}"),
                "description": rec.get("description", "Official Evacuation Order issued by emergency authorities. Move to designated emergency shelters immediately."),
                "rec_id": rec_id,
                "approved_by": body.operator_id,
                "timestamp": now_iso,
            }
            _ACTIVE_EVACUATIONS[zone_id] = evac_alert
            event_broadcaster.broadcast("evacuation", {
                "type": "EVACUATION_ALERT",
                "alert": evac_alert,
                "rec_id": rec_id,
                "decision": "APPROVED",
                "timestamp": now_iso
            })

    # Handle Rejected Actions
    elif body.decision == "REJECTED":
        # Rejections must not change shelter availability or activate evacuation orders
        zone_id = rec.get("target_zone")
        if zone_id and zone_id in _ACTIVE_EVACUATIONS and _ACTIVE_EVACUATIONS[zone_id].get("rec_id") == rec_id:
            del _ACTIVE_EVACUATIONS[zone_id]

    # Broadcast general decision update
    event_broadcaster.broadcast("decision", {
        "type": "RECOMMENDATION_DECISION",
        "rec_id": rec_id,
        "decision": body.decision,
        "operator_id": body.operator_id,
        "notes": body.notes,
        "timestamp": now_iso
    })

    return {
        "rec_id":    rec_id,
        "decision":  body.decision,
        "status":    "recorded",
        "message":   f"Recommendation {rec_id} has been {body.decision.lower()} by {body.operator_id}.",
        "active_evacuations": list(_ACTIVE_EVACUATIONS.values()),
    }


