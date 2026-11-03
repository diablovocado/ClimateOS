"""
Router: Risk Zones
Endpoints:
  GET /api/zones/risk              — all zones or spatial lookup with ?lat=X&lng=Y
  GET /api/zones/risk/{zone_id}     — single zone risk data
"""

import json
import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from services.risk_engine.engine import risk_engine

router = APIRouter()

# ---------------------------------------------------------------------------
# Load GeoJSON data
# ---------------------------------------------------------------------------
_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/zones.geojson")


def _load_geojson():
    with open(_DATA_PATH, "r") as f:
        return json.load(f)


_GEOJSON_DATA = _load_geojson()


# ---------------------------------------------------------------------------
# Point-in-Polygon spatial helpers (GeoJSON order: [lng, lat])
# ---------------------------------------------------------------------------
def point_in_polygon(lng: float, lat: float, ring: List[List[float]]) -> bool:
    """
    Ray-casting algorithm to determine if point (lng, lat) is inside polygon ring.
    GeoJSON coordinates are [longitude, latitude].
    """
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        intersect = ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / (yj - yi) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def is_point_in_geometry(lng: float, lat: float, geometry: Dict[str, Any]) -> bool:
    """Check if point falls within Polygon or MultiPolygon geometry."""
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if geom_type == "Polygon":
        if not coords:
            return False
        # Test outer ring
        if not point_in_polygon(lng, lat, coords[0]):
            return False
        # Check inner rings (holes)
        for hole in coords[1:]:
            if point_in_polygon(lng, lat, hole):
                return False
        return True
    elif geom_type == "MultiPolygon":
        for poly in coords:
            if poly and point_in_polygon(lng, lat, poly[0]):
                in_hole = any(point_in_polygon(lng, lat, hole) for hole in poly[1:])
                if not in_hole:
                    return True
        return False
    return False


def _get_active_reports_count(zone_id: str, geometry: Dict[str, Any]) -> int:
    """Count active citizen reports in the given zone by zone_id or coordinates."""
    try:
        from services.routers.reports import _INCIDENTS
        count = 0
        for inc in _INCIDENTS:
            if inc.get("status") == "RESOLVED":
                continue
            if inc.get("zone_id") == zone_id:
                count += 1
            elif geometry and inc.get("lat") is not None and inc.get("lng") is not None:
                if is_point_in_geometry(inc["lng"], inc["lat"], geometry):
                    count += 1
        return count
    except Exception:
        return 0


def _calculate_zone_data(feature: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate multi-factor dynamic risk using RiskEngine."""
    props = feature["properties"]
    geometry = feature["geometry"]
    zone_id = props["id"]
    name = props["name"]
    terrain = props.get("terrain", "Urban plain")
    rainfall_mm_hr = float(props.get("rainfall_mm_hr", 80.0))
    water_level_m = float(props.get("water_level_m", 2.0))
    pop_at_risk = int(props.get("population_at_risk", 10000))

    report_count = _get_active_reports_count(zone_id, geometry)

    risk_result = risk_engine.calculate_zone_risk(
        zone_id=zone_id,
        rainfall_mm_hr=rainfall_mm_hr,
        water_level_m=water_level_m,
        report_count=report_count,
        terrain=terrain
    )

    risk_score = risk_result["risk_score"]
    status = risk_result["status"]
    severity = risk_result["severity"]
    confidence = risk_result["confidence"]

    if risk_score >= 75.0:
        risk_level = "severe"
        color = "#ef4444"
        advice = "IMMEDIATE EVACUATION required. Water levels rising rapidly. Move to nearest designated shelter immediately."
    elif risk_score >= 45.0:
        risk_level = "high"
        color = "#f97316"
        advice = "High flood hazard. Evacuate low-lying areas. Avoid submerged roadways."
    elif risk_score >= 25.0:
        risk_level = "moderate"
        color = "#f59e0b"
        advice = "Stay alert and monitor water levels. Prepare emergency supplies."
    else:
        risk_level = "low"
        color = "#22c55e"
        advice = "Conditions currently stable. Continue monitoring official weather feeds."

    terrain_multiplier_desc = "1.35x basin multiplier" if ("basin" in terrain.lower() or zone_id == "zone-a") else (
        "0.65x hills reduction" if "hills" in terrain.lower() else "1.0x standard factor"
    )

    factors = [
        f"Rainfall intensity: {rainfall_mm_hr} mm/hr",
        f"Water level gauge: {water_level_m} m",
        f"Terrain classification: {terrain} ({terrain_multiplier_desc})",
        f"Active citizen disaster reports: {report_count}"
    ]

    xai_factors = {
        "rainfall_intensity": f"{rainfall_mm_hr} mm/hr",
        "river_gauge": f"{water_level_m} m",
        "terrain": terrain,
        "active_citizen_reports": f"{report_count} active reports",
        "model_confidence": f"{confidence}%"
    }

    return {
        "id": zone_id,
        "zone_id": zone_id,
        "name": name,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "score": risk_score,
        "category": severity,
        "severity": severity,
        "status": status,
        "confidence": confidence,
        "population_at_risk": pop_at_risk,
        "terrain": terrain,
        "rainfall_mm_hr": rainfall_mm_hr,
        "water_level_m": water_level_m,
        "report_count": report_count,
        "color": color,
        "advice": advice,
        "geometry": geometry,
        "factors": factors,
        "contributing_factors": factors,
        "xai_factors": xai_factors,
    }


def get_all_calculated_zones() -> List[Dict[str, Any]]:
    """Return all zones enriched with real-time risk scores."""
    features = _GEOJSON_DATA.get("features", [])
    return [_calculate_zone_data(f) for f in features]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/zones/risk")
def get_zones_risk(
    lat: Optional[float] = Query(None, description="Citizen latitude for point-in-polygon zone lookup"),
    lng: Optional[float] = Query(None, description="Citizen longitude for point-in-polygon zone lookup")
):
    """
    Return risk data for city zones.
    If lat and lng are provided, performs spatial point-in-polygon lookup
    and returns the citizen's current zone with explainable contributing factors.
    Otherwise returns risk data for all city zones.
    """
    if (lat is not None and lng is None) or (lat is None and lng is not None):
        raise HTTPException(
            status_code=400,
            detail="Both 'lat' and 'lng' query parameters must be provided for spatial zone lookup."
        )

    all_zones = get_all_calculated_zones()

    if lat is not None and lng is not None:
        for zone in all_zones:
            if is_point_in_geometry(lng, lat, zone["geometry"]):
                result = dict(zone)
                result["citizen_location"] = {"lat": lat, "lng": lng}
                return result
        raise HTTPException(
            status_code=404,
            detail=f"No risk zone found containing coordinates (lat={lat}, lng={lng})."
        )

    return all_zones


@router.get("/zones/risk/{zone_id}")
def get_zone_risk(zone_id: str):
    """
    Return risk data for a single zone by ID with explainable factors.
    """
    all_zones = get_all_calculated_zones()
    zone = next((z for z in all_zones if z["id"] == zone_id), None)
    if zone is None:
        raise HTTPException(status_code=404, detail=f"Zone '{zone_id}' not found")
    return zone

