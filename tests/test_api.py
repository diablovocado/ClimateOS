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


