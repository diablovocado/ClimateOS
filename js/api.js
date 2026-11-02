/**
 * ClimateOS — Centralized API Client
 * ALL fetch calls to the backend live here.
 * Feature owners: import from this file; do NOT write fetch() calls elsewhere.
 *
 * When running via `npm run dev` (Vite), API_BASE is empty ("") — Vite's dev
 * server proxies /api/* → http://localhost:8000 automatically (see vite.config.js).
 *
 * When opening HTML files directly without Vite, set API_BASE to:
 *   export const API_BASE = "http://localhost:8000";
 */

export const API_BASE = (typeof window !== "undefined" && window.location.port === "5173") ? "" : "http://localhost:8000";

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------
async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  try {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    if (!res.ok) {
      console.warn(`[API] ${options.method || "GET"} ${path} → ${res.status}`);
      return null;
    }
    return await res.json();
  } catch (err) {
    console.warn(`[API] Backend unreachable at ${url}. Running in offline/mock mode.`);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------
export async function checkHealth() {
  return apiFetch("/");
}

// ---------------------------------------------------------------------------
// Risk Zones  →  GET /api/zones/risk
// ---------------------------------------------------------------------------
export async function getZonesRisk() {
  // TODO (Risk Engine): This will return real-time calculated zone risk once
  // the risk prediction engine is connected to weather/sensor data feeds.
  return apiFetch("/api/zones/risk");
}

export async function getZoneRisk(zoneId) {
  return apiFetch(`/api/zones/risk/${zoneId}`);
}

// ---------------------------------------------------------------------------
// Shelters  →  GET /api/shelters
// ---------------------------------------------------------------------------
export async function getShelters() {
  // TODO (Shelter Intelligence): Add user lat/lng query param for sorted-by-distance results.
  return apiFetch("/api/shelters");
}

export async function getShelter(shelterId) {
  return apiFetch(`/api/shelters/${shelterId}`);
}

// ---------------------------------------------------------------------------
// Incidents  →  GET /api/incidents
// ---------------------------------------------------------------------------
export async function getIncidents() {
  // Returns incidents sorted by priority_score (highest first).
  return apiFetch("/api/incidents");
}

// ---------------------------------------------------------------------------
// Reports  →  POST /api/reports
// ---------------------------------------------------------------------------
export async function submitReport(reportPayload) {
  /**
   * @param {Object} reportPayload
   * @param {string} reportPayload.category     - flood | trapped | road | fire | medical | power_failure | water_shortage | infrastructure
   * @param {string} reportPayload.description
   * @param {number} [reportPayload.lat]
   * @param {number} [reportPayload.lng]
   * @param {string} [reportPayload.location]
   * @param {string} [reportPayload.zone_id]
   * @param {number} [reportPayload.trapped_count]
   * @param {number} [reportPayload.injured_count]
   * @param {boolean}[reportPayload.photo_attached]
   *
   * TODO (Offline Cache): Queue this POST in a service worker IndexedDB when
   * navigator.onLine === false, and replay when connectivity is restored.
   */
  return apiFetch("/api/reports", {
    method: "POST",
    body: JSON.stringify(reportPayload),
  });
}

// ---------------------------------------------------------------------------
// Recommendations  →  GET /api/recommendations
// ---------------------------------------------------------------------------
export async function getRecommendations() {
  return apiFetch("/api/recommendations");
}

// ---------------------------------------------------------------------------
// Recommendation Decision  →  POST /api/recommendations/{id}/decision
// ---------------------------------------------------------------------------
export async function postRecommendationDecision(recId, decision, notes = "") {
  /**
   * @param {string} recId     - recommendation ID
   * @param {string} decision  - "APPROVED" | "REJECTED"
   * @param {string} notes     - optional operator notes
   */
  return apiFetch(`/api/recommendations/${recId}/decision`, {
    method: "POST",
    body: JSON.stringify({ decision, notes }),
  });
}

// ---------------------------------------------------------------------------
// Simulation  →  POST /api/simulation
// ---------------------------------------------------------------------------
export async function runSimulation(rainfallMmHr, waterLevelM, zoneId = "zone-a") {
  /**
   * @param {number} rainfallMmHr  - slider value from Simulation Panel
   * @param {number} waterLevelM   - slider value from Simulation Panel
   * @param {string} zoneId        - zone to simulate
   *
   * TODO (Simulation Engine): After real risk engine is wired, this should
   * trigger a full map re-render with updated GeoJSON risk polygons.
   */
  return apiFetch("/api/simulation", {
    method: "POST",
    body: JSON.stringify({
      rainfall_mm_hr: rainfallMmHr,
      water_level_m:  waterLevelM,
      zone_id:        zoneId,
    }),
  });
}

// ---------------------------------------------------------------------------
// Safe Routes  →  POST /api/routes/safe-route
// ---------------------------------------------------------------------------
export async function getSafeRoute(optionsOrLat, lng, shelterId, travelMode = "vehicle") {
  /**
   * Calculate safest evacuation route avoiding flooded roads and blocked bridges.
   * Supports both object payload and positional arguments.
   * @param {Object|number} optionsOrLat - Payload object or origin latitude
   * @param {number} [lng]               - Origin longitude
   * @param {string} [shelterId]         - Target shelter ID
   * @param {string} [travelMode]        - "vehicle" | "pedestrian"
   */
  let payload;
  if (typeof optionsOrLat === "object" && optionsOrLat !== null) {
    payload = optionsOrLat;
  } else {
    payload = {
      origin_lat: optionsOrLat,
      origin_lng: lng,
      shelter_id: shelterId,
      destination_id: shelterId,
      travel_mode: travelMode,
      mode: travelMode,
    };
  }

  const url = `${API_BASE}/api/routes/safe-route`;
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      console.warn(`[API] POST /api/routes/safe-route → ${res.status}`, data);
      return {
        ok: false,
        status: res.status,
        error: data?.detail || `HTTP ${res.status}: Failed to calculate safe route`,
      };
    }
    return { ok: true, ...data };
  } catch (err) {
    console.warn(`[API] Safe route calculation failed:`, err);
    return {
      ok: false,
      status: 0,
      error: "Routing service is unreachable. Please check backend connection.",
    };
  }
}

