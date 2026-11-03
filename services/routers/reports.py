"""
Router: Citizen Reports & Incidents
Endpoints:
  POST /api/reports          — submit a citizen report; verified with ReportVerifier and ranked by PriorityRanker
  GET  /api/incidents        — return ranked incidents with confidence labels and priority scores
"""

import asyncio
import json
import os
import random
import string
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.verification.verifier import report_verifier
from services.priority_engine.ranker import priority_ranker
from services.events import event_broadcaster

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

    # Live Incident Propagation: Broadcast sanitized incident payload (omitting reporter personal data)
    broadcast_payload = {
        "id": incident["id"],
        "category": incident["category"],
        "severity": incident["severity"],
        "location": incident["location"],
        "lat": incident.get("lat"),
        "lng": incident.get("lng"),
        "description": incident["description"],
        "status": incident["status"],
        "confidence_score": incident["confidence_score"],
        "confidence_label": incident.get("confidence_label", "Needs Review"),
        "verification_status": incident.get("verification_status", "NEEDS_REVIEW"),
        "priority_score": incident["priority_score"],
        "trapped_count": incident.get("trapped_count", 0),
        "injured_count": incident.get("injured_count", 0),
        "zone_id": incident.get("zone_id"),
        "timestamp": incident["timestamp"],
        "verified": incident.get("verified", False),
        "type": "NEW_INCIDENT",
    }
    broadcast_payload["incident"] = dict(broadcast_payload)
    event_broadcaster.broadcast("incident", broadcast_payload)

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


@router.get("/incidents/stream")
async def stream_incidents(
    request: Request,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID")
):
    """
    Server-Sent Events (SSE) endpoint: GET /api/incidents/stream.
    Publishes live incidents, shelter updates, and official decisions to connected clients.
    Supports reconnection via Last-Event-ID and handles connection cleanup.
    """
    queue = event_broadcaster.subscribe()

    async def event_generator():
        try:
            # 1. Initial handshake
            yield "event: connected\ndata: {\"status\": \"connected\", \"message\": \"ClimateOS Live Incident Stream Active\"}\n\n"

            # 2. Replay missed events on reconnect
            if last_event_id:
                try:
                    lid = int(last_event_id)
                    missed = event_broadcaster.get_events_since(lid)
                    for eid, etype, payload in missed:
                        yield f"id: {eid}\nevent: {etype}\ndata: {json.dumps(payload)}\n\n"
                except (ValueError, TypeError):
                    pass

            # 3. Stream loop with keep-alive
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event_id, event_type, payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"id: {event_id}\nevent: {event_type}\ndata: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        break
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_broadcaster.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


