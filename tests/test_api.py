"""
ClimateOS — API Skeleton Tests
Run: pytest tests/test_api.py -v

Tests cover the 7 stub API endpoints:
  GET  /api/zones/risk
  GET  /api/shelters
  GET  /api/incidents
  POST /api/reports
  GET  /api/recommendations
  POST /api/recommendations/{id}/decision
  POST /api/simulation
"""

import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.main import app

client = TestClient(app)



# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
def test_root_health():
    """Health check endpoint should return 200 and correct platform name."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "ClimateOS" in data["platform"]
    assert data["status"] == "online"


# ---------------------------------------------------------------------------
# GET /api/zones/risk
# ---------------------------------------------------------------------------
def test_get_zones_risk_returns_list():
    """Should return a non-empty list of zone objects."""
    response = client.get("/api/zones/risk")
    assert response.status_code == 200
    zones = response.json()
    assert isinstance(zones, list)
    assert len(zones) >= 1


def test_get_zones_risk_structure():
    """Each zone should have required fields including risk_score."""
    response = client.get("/api/zones/risk")
    zone = response.json()[0]
    assert "id"           in zone
    assert "name"         in zone
    assert "risk_score"   in zone
    assert "risk_level"   in zone
    assert "status"       in zone
    assert 0 <= zone["risk_score"] <= 100


def test_get_single_zone_risk():
    """GET /api/zones/risk/{zone_id} should return the specific zone."""
    response = client.get("/api/zones/risk/zone-a")
    assert response.status_code == 200
    zone = response.json()
    assert zone["id"] == "zone-a"


def test_get_unknown_zone_returns_404():
    """Requesting a non-existent zone should return 404."""
    response = client.get("/api/zones/risk/zone-xyz")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/shelters
# ---------------------------------------------------------------------------
def test_get_shelters_returns_list():
    """Should return a non-empty list of shelter objects."""
    response = client.get("/api/shelters")
    assert response.status_code == 200
    shelters = response.json()
    assert isinstance(shelters, list)
    assert len(shelters) >= 1


def test_get_shelters_structure():
    """Each shelter should include capacity, occupancy, and status."""
    response = client.get("/api/shelters")
    shelter = response.json()[0]
    assert "id"        in shelter
    assert "name"      in shelter
    assert "capacity"  in shelter
    assert "occupancy" in shelter
    assert "status"    in shelter
    assert shelter["status"] in ("OPEN", "NEAR_CAPACITY", "FULL", "STANDBY")


# ---------------------------------------------------------------------------
# GET /api/incidents
# ---------------------------------------------------------------------------
def test_get_incidents_returns_list():
    """Should return a list of incidents (may be empty before any reports)."""
    response = client.get("/api/incidents")
    assert response.status_code == 200
    incidents = response.json()
    assert isinstance(incidents, list)


def test_get_incidents_sorted_by_priority():
    """Incidents should be sorted by priority_score descending."""
    response = client.get("/api/incidents")
    incidents = response.json()
    if len(incidents) >= 2:
        assert incidents[0]["priority_score"] >= incidents[1]["priority_score"]


def test_incidents_have_confidence_label():
    """Each incident should have a confidence_label field."""
    response = client.get("/api/incidents")
    incidents = response.json()
    if incidents:
        label = incidents[0].get("confidence_label")
        assert label in ("High Confidence", "Needs Review", "Low Confidence")


# ---------------------------------------------------------------------------
# POST /api/reports
# ---------------------------------------------------------------------------
SAMPLE_REPORT = {
    "category":      "trapped",
    "description":   "Water rising up to 1.2m. 4 people trapped on 1st floor.",
    "location":      "142 Riverside Avenue",
    "lat":           18.526,
    "lng":           73.858,
    "zone_id":       "zone-a",
    "trapped_count": 4,
    "injured_count": 1,
    "photo_attached": True,
}

def test_submit_report_returns_200():
    """Submitting a valid report should return 200."""
    response = client.post("/api/reports", json=SAMPLE_REPORT)
    assert response.status_code == 200


def test_submit_report_returns_verification():
    """Response should include a verification object with confidence_score and status."""
    response = client.post("/api/reports", json=SAMPLE_REPORT)
    data = response.json()
    assert "verification" in data
    v = data["verification"]
    assert "confidence_score" in v
    assert "status"           in v
    assert v["status"] in ("HIGH_CONFIDENCE", "NEEDS_REVIEW", "LOW_CONFIDENCE", "High Confidence", "Needs Review", "Low Confidence")
    assert 0 <= v["confidence_score"] <= 100
    assert "factors" in v
    assert isinstance(v["factors"], list)



def test_submit_report_creates_incident():
    """Response should include a derived incident with the same trapped_count."""
    response = client.post("/api/reports", json=SAMPLE_REPORT)
    data = response.json()
    assert "incident" in data
    assert data["incident"]["trapped_count"] == SAMPLE_REPORT["trapped_count"]


# ---------------------------------------------------------------------------
# GET /api/recommendations
# ---------------------------------------------------------------------------
def test_get_recommendations_returns_list():
    """Should return a non-empty list of recommendations."""
    response = client.get("/api/recommendations")
    assert response.status_code == 200
    recs = response.json()
    assert isinstance(recs, list)
    assert len(recs) >= 1


def test_recommendations_have_decision_status():
    """Each recommendation should have a decision_status field."""
    response = client.get("/api/recommendations")
    rec = response.json()[0]
    assert "decision_status" in rec
    assert rec["decision_status"] in ("PENDING", "APPROVED", "REJECTED")


# ---------------------------------------------------------------------------
# POST /api/recommendations/{id}/decision
# ---------------------------------------------------------------------------
def test_approve_recommendation():
    """Approving a recommendation should succeed and return the decision."""
    recs = client.get("/api/recommendations").json()
    rec_id = recs[0]["id"]
    response = client.post(
        f"/api/recommendations/{rec_id}/decision",
        json={"decision": "APPROVED", "notes": "Authorized by operator."}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED"
    assert data["rec_id"]   == rec_id


def test_reject_recommendation():
    """Rejecting a recommendation should succeed."""
    recs = client.get("/api/recommendations").json()
    rec_id = recs[0]["id"]
    response = client.post(
        f"/api/recommendations/{rec_id}/decision",
        json={"decision": "REJECTED"}
    )
    assert response.status_code == 200
    assert response.json()["decision"] == "REJECTED"


def test_invalid_decision_returns_400():
    """Submitting an unknown decision value should return 400."""
    recs = client.get("/api/recommendations").json()
    rec_id = recs[0]["id"]
    response = client.post(
        f"/api/recommendations/{rec_id}/decision",
        json={"decision": "MAYBE"}
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/simulation
# ---------------------------------------------------------------------------
def test_simulation_returns_updated_zone_risk():
    """Simulation with rainfall and water level should return an updated zone risk."""
    response = client.post("/api/simulation", json={
        "rainfall_mm_hr": 120.0,
        "water_level_m":  5.0,
        "zone_id":        "zone-a"
    })
    assert response.status_code == 200
    data = response.json()
    assert "updated_zone_risk" in data
    risk = data["updated_zone_risk"]
    assert "risk_score"  in risk
    assert "risk_level"  in risk
    assert "status"      in risk
    assert 0 <= risk["risk_score"] <= 100


def test_simulation_low_values_return_lower_risk():
    """Simulation with very low rainfall should produce a lower risk than high rainfall."""
    low_response  = client.post("/api/simulation", json={"rainfall_mm_hr": 5.0,  "water_level_m": 0.2, "zone_id": "zone-a"})
    high_response = client.post("/api/simulation", json={"rainfall_mm_hr": 180.0, "water_level_m": 7.0, "zone_id": "zone-a"})

    low_risk  = low_response.json()["updated_zone_risk"]["risk_score"]
    high_risk = high_response.json()["updated_zone_risk"]["risk_score"]
    assert low_risk < high_risk


# ---------------------------------------------------------------------------
# POST & GET /api/routes/safe-route
# ---------------------------------------------------------------------------
def test_safe_route_vehicle_mode():
    """Valid request in vehicle mode should return 200 with GeoJSON LineString and simulation metadata."""
    payload = {
        "origin_lat": 18.526,
        "origin_lng": 73.858,
        "shelter_id": "shelter-b",
        "travel_mode": "vehicle"
    }
    response = client.post("/api/routes/safe-route", json=payload)
    assert response.status_code == 200
    data = response.json()

    # GeoJSON validation
    assert data["type"] == "Feature"
    assert "geometry" in data
    assert data["geometry"]["type"] == "LineString"
    assert isinstance(data["geometry"]["coordinates"], list)
    assert len(data["geometry"]["coordinates"]) >= 2
    # Verify longitude/latitude order in GeoJSON coordinates
    for pt in data["geometry"]["coordinates"]:
        assert len(pt) == 2
        assert 70.0 <= pt[0] <= 80.0  # lng
        assert 15.0 <= pt[1] <= 25.0  # lat

    # Route metadata
    assert data["travel_mode"] == "vehicle"
    assert data["distance_km"] > 0
    assert data["estimated_minutes"] > 0
    assert "Route C" in data["route_name"]
    assert data["is_simulated"] is True
    assert data["status"] in ("SIMULATED_SAFE", "SIMULATED_CAUTION")
    assert "safety_disclaimer" in data
    assert "not guaranteed safe" in data["safety_disclaimer"].lower()
    assert len(data["avoided_hazards"]) >= 1


def test_safe_route_pedestrian_mode():
    """Pedestrian mode should calculate longer travel duration than vehicle mode for the same route."""
    veh_res = client.post("/api/routes/safe-route", json={
        "origin_lat": 18.526,
        "origin_lng": 73.858,
        "shelter_id": "shelter-b",
        "travel_mode": "vehicle"
    })
    ped_res = client.post("/api/routes/safe-route", json={
        "origin_lat": 18.526,
        "origin_lng": 73.858,
        "shelter_id": "shelter-b",
        "travel_mode": "pedestrian"
    })
    assert veh_res.status_code == 200
    assert ped_res.status_code == 200

    veh_data = veh_res.json()
    ped_data = ped_res.json()

    assert ped_data["travel_mode"] == "pedestrian"
    # Walking duration should be significantly longer than driving
    assert ped_data["estimated_minutes"] > veh_data["estimated_minutes"]
    assert ped_data["geometry"]["type"] == "LineString"
    assert ped_data["is_simulated"] is True


def test_safe_route_invalid_coordinates():
    """Coordinates out of physical bounds [-90, 90] or outside service area should return 400."""
    # Out of physical latitude bounds
    res_lat_oob = client.post("/api/routes/safe-route", json={
        "origin_lat": 999.0,
        "origin_lng": 73.858,
        "shelter_id": "shelter-b"
    })
    assert res_lat_oob.status_code == 400
    assert "invalid coordinates" in res_lat_oob.json()["detail"].lower()

    # Out of operational service area (Null Island: 0, 0)
    res_outside = client.post("/api/routes/safe-route", json={
        "origin_lat": 0.0,
        "origin_lng": 0.0,
        "shelter_id": "shelter-b"
    })
    assert res_outside.status_code == 400
    assert "outside" in res_outside.json()["detail"].lower()


def test_safe_route_unknown_shelter():
    """Requesting an unknown shelter ID should return 404 with a helpful validation message."""
    response = client.post("/api/routes/safe-route", json={
        "origin_lat": 18.526,
        "origin_lng": 73.858,
        "shelter_id": "shelter-unknown-xyz"
    })
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_safe_route_blocked_roads_no_route():
    """When all connecting corridors are blocked, engine must return 404 and never fabricate a safe route."""
    payload = {
        "origin_lat": 18.526,
        "origin_lng": 73.858,
        "shelter_id": "shelter-b",
        "blocked_roads": [
            "Elevated Highway",
            "North Hills",
            "Riverside",
            "Highway Ramp",
            "East Ring"
        ]
    }
    response = client.post("/api/routes/safe-route", json=payload)
    assert response.status_code == 404
    assert "no safe route available" in response.json()["detail"].lower()


def test_safe_route_avoids_submerged_bridge():
    """Default route to shelter-b must avoid the submerged Riverside Bridge and list it as avoided."""
    response = client.post("/api/routes/safe-route", json={
        "origin_lat": 18.526,
        "origin_lng": 73.858,
        "shelter_id": "shelter-b"
    })
    assert response.status_code == 200
    data = response.json()
    assert any("riverside" in h.lower() and "bridge" in h.lower() for h in data["avoided_hazards"])
    assert "Route C" in data["route_name"]


def test_safe_route_get_endpoint():
    """GET /api/routes/safe-route query param interface should return 200 with valid route."""
    response = client.get(
        "/api/routes/safe-route?origin_lat=18.526&origin_lng=73.858&shelter_id=shelter-b&travel_mode=vehicle"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "Feature"
    assert data["geometry"]["type"] == "LineString"
    assert data["travel_mode"] == "vehicle"
    assert data["distance_km"] == 2.4


def test_safe_route_destination_id_compatibility():
    """Accepts destination_id as an alias for shelter_id."""
    response = client.post("/api/routes/safe-route", json={
        "origin_lat": 18.526,
        "origin_lng": 73.858,
        "destination_id": "shelter-b"
    })
    assert response.status_code == 200
    assert response.json()["geometry"]["type"] == "LineString"


# ---------------------------------------------------------------------------
# AI & Decision Engines Integration Tests
# ---------------------------------------------------------------------------
def test_spatial_risk_lookup_point_in_zone_a():
    """GET /api/zones/risk?lat=18.526&lng=73.858 returns Zone A with explainable contributing factors."""
    response = client.get("/api/zones/risk?lat=18.526&lng=73.858")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "zone-a"
    assert data["name"] == "Zone A — Riverside"
    assert "risk_score" in data
    assert data["risk_score"] >= 75.0
    assert data["severity"] == "CRITICAL"
    assert data["category"] == "CRITICAL"
    assert "confidence" in data
    assert "factors" in data
    assert isinstance(data["factors"], list)
    assert any("Rainfall intensity" in f for f in data["factors"])
    assert any("Water level gauge" in f for f in data["factors"])
    assert any("Terrain" in f for f in data["factors"])
    assert "contributing_factors" in data
    assert "xai_factors" in data
    assert "citizen_location" in data


def test_spatial_risk_lookup_point_in_zone_b():
    """GET /api/zones/risk?lat=18.51&lng=73.87 returns Zone B."""
    response = client.get("/api/zones/risk?lat=18.51&lng=73.87")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "zone-b"
    assert data["name"] == "Zone B — Downtown"


def test_spatial_risk_lookup_outside_all_zones():
    """GET /api/zones/risk with coordinates outside all monitored polygons returns 404."""
    response = client.get("/api/zones/risk?lat=0.0&lng=0.0")
    assert response.status_code == 404
    assert "No risk zone found" in response.json()["detail"]


def test_spatial_risk_lookup_missing_coordinate_returns_400():
    """GET /api/zones/risk with only lat or only lng returns 400 Bad Request."""
    res_lat_only = client.get("/api/zones/risk?lat=18.526")
    assert res_lat_only.status_code == 400
    res_lng_only = client.get("/api/zones/risk?lng=73.858")
    assert res_lng_only.status_code == 400


def test_all_zones_have_dynamic_risk_and_factors():
    """GET /api/zones/risk returns all zones enriched with dynamic scores and factors."""
    response = client.get("/api/zones/risk")
    assert response.status_code == 200
    zones = response.json()
    assert len(zones) >= 5
    for z in zones:
        assert "risk_score" in z
        assert "severity" in z
        assert "confidence" in z
        assert "factors" in z
        assert len(z["factors"]) >= 4


def test_ai_report_verification_and_priority_engine():
    """Submitting a report invokes ReportVerifier and PriorityRanker with transparent factors."""
    payload = {
        "category": "trapped",
        "description": "5 people trapped on rooftop due to rapid flooding",
        "location": "Sector 4 Flood Plain",
        "lat": 18.526,
        "lng": 73.858,
        "zone_id": "zone-a",
        "trapped_count": 5,
        "injured_count": 2,
        "photo_attached": True
    }
    response = client.post("/api/reports", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verification checks
    v = data["verification"]
    assert v["status"] == "HIGH_CONFIDENCE"
    assert v["confidence_score"] >= 85.0
    assert any("High-severity incident category match" in f for f in v["factors"])
    assert any("Verified visual photo evidence" in f for f in v["factors"])
    assert any("Multiple life-threat signals" in f for f in v["factors"])
    assert any("Valid GPS coordinate lock" in f for f in v["factors"])

    # Priority Ranker checks
    inc = data["incident"]
    assert inc["priority_score"] >= 80.0
    assert inc["severity"] == "CRITICAL"
    assert inc["trapped_count"] == 5
    assert inc["injured_count"] == 2
    assert "prediction_disclaimer" in inc


def test_incidents_strictly_ordered_by_priority():
    """Incidents returned by GET /api/incidents are ordered descending by priority_score."""
    # Submit low priority report
    client.post("/api/reports", json={
        "category": "water_shortage",
        "description": "Low water pressure in municipal pipe",
        "trapped_count": 0,
        "injured_count": 0,
        "photo_attached": False
    })
    # Submit high priority report
    client.post("/api/reports", json={
        "category": "trapped",
        "description": "Immediate life threat 8 people trapped",
        "trapped_count": 8,
        "injured_count": 3,
        "photo_attached": True,
        "lat": 18.526,
        "lng": 73.858
    })
    incidents = client.get("/api/incidents").json()
    assert len(incidents) >= 2
    scores = [i["priority_score"] for i in incidents]
    assert scores == sorted(scores, reverse=True)


def test_recommendation_advisor_dynamic_generation_and_deduplication():
    """Advisor triggers recommendations for high risk zones (>=75) and deduplicates pending ones."""
    res1 = client.get("/api/recommendations")
    assert res1.status_code == 200
    recs1 = res1.json()

    # Check high-risk evacuation recommendation exists
    evac_recs = [r for r in recs1 if "EVAC" in r["id"]]
    assert len(evac_recs) >= 1
    assert any(r["priority"] == "CRITICAL" for r in evac_recs)

    # Calling again must not duplicate pending recommendations
    res2 = client.get("/api/recommendations")
    recs2 = res2.json()
    assert len(recs1) == len(recs2)

    # All rec IDs must be unique
    ids = [r["id"] for r in recs2]
    assert len(ids) == len(set(ids))


def test_recommendation_human_decision_flow():
    """Human authority can approve or reject recommendations and status transitions cleanly."""
    recs = client.get("/api/recommendations").json()
    pending = next((r for r in recs if r["decision_status"] == "PENDING"), None)
    assert pending is not None
    target_id = pending["id"]

    # Approve
    app_res = client.post(
        f"/api/recommendations/{target_id}/decision",
        json={"decision": "APPROVED", "operator_id": "chief-officer-9", "notes": "Approved for dispatch."}
    )
    assert app_res.status_code == 200
    assert app_res.json()["decision"] == "APPROVED"

    # Verify decision persisted
    recs_after = client.get("/api/recommendations").json()
    decided = next(r for r in recs_after if r["id"] == target_id)
    assert decided["decision_status"] == "APPROVED"
    assert decided["decided_by"] == "chief-officer-9"

    # Reject another
    pending2 = next((r for r in recs_after if r["decision_status"] == "PENDING"), None)
    if pending2:
        rej_res = client.post(
            f"/api/recommendations/{pending2['id']}/decision",
            json={"decision": "REJECTED", "operator_id": "chief-officer-9", "notes": "Capacity insufficient."}
        )
        assert rej_res.status_code == 200
        assert rej_res.json()["decision"] == "REJECTED"


# ---------------------------------------------------------------------------
# Closed-Loop Citizen & Government Real-Time Interaction Tests
# ---------------------------------------------------------------------------
from services.events import event_broadcaster


def test_event_broadcaster_pub_sub_and_multi_client():
    """EventBroadcaster distributes events to multiple subscribers and cleans up on unsubscribe."""
    initial_subs = event_broadcaster.get_subscriber_count()
    q1 = event_broadcaster.subscribe()
    q2 = event_broadcaster.subscribe()
    assert event_broadcaster.get_subscriber_count() == initial_subs + 2

    eid = event_broadcaster.broadcast("test_event", {"msg": "broadcast-check"})
    assert eid > 0

    assert not q1.empty()
    assert not q2.empty()

    ev1 = q1.get_nowait()
    ev2 = q2.get_nowait()

    assert ev1[0] == eid
    assert ev1[1] == "test_event"
    assert ev1[2]["msg"] == "broadcast-check"
    assert ev2 == ev1

    # Unsubscribe q1; only q2 receives next event
    event_broadcaster.unsubscribe(q1)
    assert event_broadcaster.get_subscriber_count() == initial_subs + 1

    eid2 = event_broadcaster.broadcast("test_event_2", {"msg": "only-q2"})
    assert q1.empty()
    assert not q2.empty()
    assert q2.get_nowait()[0] == eid2

    event_broadcaster.unsubscribe(q2)


def test_event_broadcaster_reconnection_last_event_id():
    """Clients can retrieve missed events using Last-Event-ID for reconnection resilience."""
    event_broadcaster.clear()
    eid1 = event_broadcaster.broadcast("incident", {"num": 1})
    eid2 = event_broadcaster.broadcast("incident", {"num": 2})
    eid3 = event_broadcaster.broadcast("incident", {"num": 3})

    missed = event_broadcaster.get_events_since(eid1)
    assert len(missed) == 2
    assert missed[0][0] == eid2
    assert missed[1][0] == eid3
    assert missed[0][2]["num"] == 2
    assert missed[1][2]["num"] == 3


def test_citizen_report_submission_broadcasts_sanitized_event():
    """Submitting a citizen report broadcasts an incident event without exposing private reporter info."""
    q = event_broadcaster.subscribe()
    try:
        report_payload = {
            "category": "trapped",
            "description": "Family trapped in bungalow near riverside road",
            "location": "Riverside Bungalow 42",
            "lat": 18.5204,
            "lng": 73.8567,
            "trapped_count": 4,
            "injured_count": 1,
            "photo_attached": True,
            "reporter_id": "citizen-secret-aadhaar-1234",
        }
        res = client.post("/api/reports", json=report_payload)
        assert res.status_code == 200

        # Verify broadcast event received
        assert not q.empty()
        event_id, event_type, payload = q.get_nowait()

        assert event_type == "incident"
        assert payload["category"] == "trapped"
        assert payload["location"] == "Riverside Bungalow 42"
        assert payload["lat"] == 18.5204
        assert payload["lng"] == 73.8567
        assert payload["trapped_count"] == 4
        assert payload["injured_count"] == 1
        assert "severity" in payload
        assert "verification_status" in payload
        assert "timestamp" in payload

        # Privacy protection: reporter_id must NOT be exposed in the broadcast
        assert "reporter_id" not in payload
        assert "citizen-secret-aadhaar-1234" not in str(payload)
    finally:
        event_broadcaster.unsubscribe(q)


def test_unauthorized_recommendation_decision_forbidden():
    """Unauthorized callers (citizens, anonymous users) are blocked with 403 Forbidden."""
    recs = client.get("/api/recommendations").json()
    rec_id = recs[0]["id"]

    # Citizen role in payload
    res1 = client.post(
        f"/api/recommendations/{rec_id}/decision",
        json={"decision": "APPROVED", "role": "citizen", "operator_id": "citizen-101"}
    )
    assert res1.status_code == 403
    assert "Forbidden" in res1.json()["detail"]

    # Citizen prefix in operator_id
    res2 = client.post(
        f"/api/recommendations/{rec_id}/decision",
        json={"decision": "APPROVED", "operator_id": "citizen-jane"}
    )
    assert res2.status_code == 403

    # Anonymous operator
    res3 = client.post(
        f"/api/recommendations/{rec_id}/decision",
        json={"decision": "APPROVED", "operator_id": "anonymous"}
    )
    assert res3.status_code == 403

    # Citizen in X-User-Role header
    res4 = client.post(
        f"/api/recommendations/{rec_id}/decision",
        headers={"X-User-Role": "citizen"},
        json={"decision": "APPROVED", "operator_id": "unknown"}
    )
    assert res4.status_code == 403


def test_authorized_shelter_recommendation_approval():
    """Approving a shelter recommendation updates target shelter status to OPEN and broadcasts shelter event."""
    q = event_broadcaster.subscribe()
    try:
        # Find or use shelter recommendation
        recs = client.get("/api/recommendations").json()
        shelter_rec = next((r for r in recs if "SHELTER" in r["id"] or r.get("type") == "SHELTER_ACTIVATION"), None)
        assert shelter_rec is not None
        rec_id = shelter_rec["id"]

        res = client.post(
            f"/api/recommendations/{rec_id}/decision",
            headers={"X-User-Role": "official"},
            json={"decision": "APPROVED", "operator_id": "gov-commander-1", "notes": "Open shelter for overflow."}
        )
        assert res.status_code == 200
        assert res.json()["decision"] == "APPROVED"

        # Check shelter data in GET /api/shelters
        shelters = client.get("/api/shelters").json()
        shelter_b = next((s for s in shelters if s["id"] == "shelter-b"), None)
        assert shelter_b is not None
        assert shelter_b["status"] == "OPEN"

        # Verify broadcast event
        events = []
        while not q.empty():
            events.append(q.get_nowait())

        shelter_events = [e for e in events if e[1] == "shelter"]
        assert len(shelter_events) >= 1
        assert shelter_events[0][2]["decision"] == "APPROVED"
        assert shelter_events[0][2]["shelter"]["status"] == "OPEN"
    finally:
        event_broadcaster.unsubscribe(q)


def test_authorized_evacuation_recommendation_approval():
    """Approving an evacuation recommendation creates an active evacuation directive and broadcasts alert."""
    q = event_broadcaster.subscribe()
    try:
        recs = client.get("/api/recommendations").json()
        evac_rec = next((r for r in recs if "EVAC" in r["id"] or r.get("type") == "EVACUATION"), None)
        assert evac_rec is not None
        rec_id = evac_rec["id"]

        res = client.post(
            f"/api/recommendations/{rec_id}/decision",
            headers={"X-User-Role": "authority"},
            json={"decision": "APPROVED", "operator_id": "disaster-management-hq", "notes": "Mandatory evacuation authorized."}
        )
        assert res.status_code == 200

        # Verify active evacuations endpoint
        evacs = client.get("/api/evacuations").json()
        assert len(evacs) >= 1
        zone_evac = next((e for e in evacs if e["zone_id"] == (evac_rec.get("target_zone") or "zone-a")), None)
        assert zone_evac is not None
        assert zone_evac["status"] == "ACTIVE_EVACUATION"
        assert zone_evac["approved_by"] == "disaster-management-hq"

        # Verify broadcast event
        events = []
        while not q.empty():
            events.append(q.get_nowait())

        evac_events = [e for e in events if e[1] == "evacuation"]
        assert len(evac_events) >= 1
        assert evac_events[0][2]["decision"] == "APPROVED"
        assert evac_events[0][2]["alert"]["status"] == "ACTIVE_EVACUATION"
    finally:
        event_broadcaster.unsubscribe(q)


def test_rejected_recommendation_does_not_activate_evacuation():
    """Rejected recommendations must not activate evacuation orders or alter shelter status."""
    recs = client.get("/api/recommendations").json()
    rec = next((r for r in recs if "EVAC" in r["id"] or r.get("type") == "EVACUATION"), recs[0])
    rec_id = rec["id"]

    res = client.post(
        f"/api/recommendations/{rec_id}/decision",
        headers={"X-User-Role": "authority"},
        json={"decision": "REJECTED", "operator_id": "field-evaluator-2", "notes": "Dike holding; evacuation not warranted."}
    )
    assert res.status_code == 200
    assert res.json()["decision"] == "REJECTED"

    # Verify that this rejected rec is NOT in active evacuations
    evacs = client.get("/api/evacuations").json()
    assert not any(e.get("rec_id") == rec_id for e in evacs)


def test_unapproved_ai_recommendations_not_treated_as_active_orders():
    """Pending AI recommendations are advisory and must never be treated as active government orders."""
    recs = client.get("/api/recommendations").json()
    pending_recs = [r for r in recs if r.get("decision_status") == "PENDING"]
    assert len(pending_recs) >= 1

    evacs = client.get("/api/evacuations").json()
    for pending in pending_recs:
        assert not any(e.get("rec_id") == pending["id"] for e in evacs)


def test_incidents_stream_reconnection_and_handshake():
    """Directly test stream generator yields handshake and replays missed events."""
    import asyncio
    from services.routers.reports import stream_incidents

    event_broadcaster.clear()
    eid1 = event_broadcaster.broadcast("incident", {"id": "INC-TEST-1", "location": "Test Loc 1"})
    eid2 = event_broadcaster.broadcast("incident", {"id": "INC-TEST-2", "location": "Test Loc 2"})

    class MockRequest:
        async def is_disconnected(self):
            return True

    async def run_stream():
        streaming_resp = await stream_incidents(request=MockRequest(), last_event_id=str(eid1))
        chunks = []
        async for chunk in streaming_resp.body_iterator:
            chunks.append(chunk)
            if len(chunks) >= 2:
                break
        return chunks

    chunks = asyncio.run(run_stream())
    assert len(chunks) >= 2
    assert "event: connected" in chunks[0]
    assert "INC-TEST-2" in chunks[1]
    assert f"id: {eid2}" in chunks[1]


# ---------------------------------------------------------------------------
# Localized Risk & Shelter Navigation Tests
# ---------------------------------------------------------------------------
def test_citizen_geolocation_risk_lookup_returns_actual_backend_data():
    """Point-in-polygon lookup returns authentic zone risk, severity, and advice."""
    # Zone A centroid coordinates
    res = client.get("/api/zones/risk?lat=18.5260&lng=73.8580")
    assert res.status_code == 200
    data = res.json()

    assert data["id"] == "zone-a"
    assert "Zone A" in data["name"]
    assert data["risk_level"] == "severe"
    assert data["risk_score"] >= 75
    assert data["status"] in ("HIGH RISK", "CRITICAL")
    assert data["category"] in ("CRITICAL", "HIGH", "SEVERE")
    assert "advice" in data and len(data["advice"]) > 10
    assert "factors" in data and len(data["factors"]) >= 3
    assert data["citizen_location"]["lat"] == 18.5260
    assert data["citizen_location"]["lng"] == 73.8580


def test_citizen_geolocation_outside_tracked_zones_returns_404():
    """Coordinates outside monitored flood zones return 404 and never fabricate a zone."""
    res = client.get("/api/zones/risk?lat=18.1000&lng=73.2000")
    assert res.status_code == 404
    detail = res.json()["detail"]
    assert "No risk zone found containing coordinates" in detail


def test_shelter_capacity_and_availability_filtering():
    """Shelter API provides status and occupancy enabling client to filter out FULL and STANDBY shelters."""
    shelters = client.get("/api/shelters").json()
    assert len(shelters) >= 5

    # shelter-d is full
    shelter_d = next((s for s in shelters if s["id"] == "shelter-d"), None)
    assert shelter_d is not None
    assert shelter_d["status"] == "FULL"

    # shelter-e is standby
    shelter_e = next((s for s in shelters if s["id"] == "shelter-e"), None)
    assert shelter_e is not None
    assert shelter_e["status"] == "STANDBY"

    # Eligible shelters must be OPEN or NEAR_CAPACITY with capacity > occupancy
    eligible = [
        s for s in shelters
        if s["status"] in ("OPEN", "NEAR_CAPACITY") and (s["capacity"] - s["occupancy"]) > 0
    ]
    assert len(eligible) >= 2
    assert all(s["id"] not in ("shelter-d", "shelter-e") for s in eligible)


def test_safe_route_from_citizen_coordinates_to_closest_shelter():
    """Safe route is calculated from citizen origin to closest available shelter."""
    res = client.post("/api/routes/safe-route", json={
        "origin_lat": 18.5260,
        "origin_lng": 73.8580,
        "shelter_id": "shelter-b",
        "travel_mode": "vehicle"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("SIMULATED_SAFE", "SIMULATED_CAUTION")
    assert data["shelter"]["id"] == "shelter-b"
    assert data["distance_km"] > 0
    assert "geometry" in data and data["geometry"]["type"] == "LineString"
    assert len(data["geometry"]["coordinates"]) >= 2
    assert "avoided_hazards" in data


def test_safe_route_unknown_shelter_returns_404():
    """Attempting to route to a non-existent shelter returns 404."""
    res = client.post("/api/routes/safe-route", json={
        "origin_lat": 18.5260,
        "origin_lng": 73.8580,
        "shelter_id": "shelter-nonexistent-999",
        "travel_mode": "vehicle"
    })
    assert res.status_code == 404





