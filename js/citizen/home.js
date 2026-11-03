/**
 * ClimateOS — Citizen Mode: Home Page Controller
 * Handles:
 *  - Geolocation with permission management & fallback
 *  - Localized risk status based on real backend API
 *  - One-click closest available shelter navigation with risk-aware routing
 *  - Real-time SSE alert streaming
 */

import {
  getZoneRisk,
  getZoneRiskByCoordinates,
  getShelters,
  getSafeRoute,
  getActiveEvacuations,
  getIncidentsStreamUrl,
} from "../api.js";

// ---------------------------------------------------------------------------
// In-Memory Citizen State (Never persisted / never leaked)
// ---------------------------------------------------------------------------
let _currentCitizenCoords = null; // { lat, lng }
let _currentCitizenZone = null;   // Zone object from actual backend response
let _citizenEventSource = null;

const ZONE_PRESETS = {
  "zone-a": { name: "Zone A — Riverside", coords: { lat: 18.5260, lng: 73.8580 } },
  "zone-b": { name: "Zone B — Downtown", coords: { lat: 18.5100, lng: 73.8650 } },
  "zone-c": { name: "Zone C — Westside", coords: { lat: 18.5180, lng: 73.8350 } },
  "zone-d": { name: "Zone D — North Hills", coords: { lat: 18.5420, lng: 73.8780 } },
  "zone-e": { name: "Zone E — Port Industrial", coords: { lat: 18.4950, lng: 73.8870 } },
};

// ---------------------------------------------------------------------------
// Active Evacuation Alert Banner (Human Authority Directive)
// ---------------------------------------------------------------------------
export async function loadActiveEvacuationAlert() {
  const banner = document.getElementById("citizen-emergency-alert");
  if (!banner) return;

  const evacuations = await getActiveEvacuations();
  const hasActiveEvac = evacuations && evacuations.length > 0;

  if (hasActiveEvac) {
    // Official government evacuation order active
    const evac = evacuations[0];
    banner.style.borderLeft = "4px solid var(--risk-severe)";
    banner.style.background = "linear-gradient(135deg, rgba(239,68,68,0.18), rgba(220,38,38,0.10))";
    banner.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span class="risk-badge risk-badge--severe pulse">🚨 MANDATORY EVACUATION ORDER</span>
        <span class="tag tag--danger">OFFICIAL DIRECTIVE</span>
      </div>
      <p style="font-size:14px;font-weight:700;color:var(--text-primary);line-height:1.5;">
        ${evac.title}: ${evac.description}
      </p>
      <div style="font-size:12px;color:var(--text-secondary);margin-top:4px;">
        Authorized by: <strong>${evac.approved_by || "Emergency Command"}</strong> &bull; Updated: ${new Date(evac.timestamp).toLocaleTimeString()}
      </div>
      <button id="btn-use-location" class="btn btn--cyan" style="margin-top:10px;width:100%;" aria-label="Use GPS to detect your zone">
        ${_currentCitizenCoords ? `📍 Location: ${_currentCitizenCoords.lat.toFixed(4)}, ${_currentCitizenCoords.lng.toFixed(4)}` : "📍 Use My Location"}
      </button>
    `;
  } else {
    // Advisory monitoring state (Unapproved AI recommendations are never treated as official orders)
    banner.style.borderLeft = "4px solid var(--risk-high)";
    banner.style.background = "linear-gradient(135deg,rgba(249,115,22,0.12),rgba(234,179,8,0.06))";
    banner.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
        <span class="risk-badge risk-badge--high">⚠️ FLOOD ADVISORY MONITORING</span>
        <span class="tag">NO ACTIVE EVACUATION ORDER</span>
      </div>
      <p style="font-size:14px;font-weight:600;color:var(--text-primary);line-height:1.5;">
        High water advisory active in low-lying sectors. No mandatory evacuation has been authorized.
        Stay alert, monitor official notifications, and check nearby shelter availability.
      </p>
      <button id="btn-use-location" class="btn btn--cyan" style="margin-top:10px;width:100%;" aria-label="Use GPS to detect your zone">
        ${_currentCitizenCoords ? `📍 Location: ${_currentCitizenCoords.lat.toFixed(4)}, ${_currentCitizenCoords.lng.toFixed(4)}` : "📍 Use My Location"}
      </button>
    `;
  }
  setupLocationButton();
}

// ---------------------------------------------------------------------------
// Geolocation & Localized Risk Information
// ---------------------------------------------------------------------------
export async function loadRiskStatus() {
  const card = document.getElementById("citizen-risk-card");
  if (!card) return;

  // If no zone or coordinates have been established yet, show prompt & manual option
  if (!_currentCitizenZone) {
    card.innerHTML = `
      <div class="risk-card" style="border-left: 4px solid var(--accent-cyan);">
        <div class="risk-card__header">
          <span class="risk-badge risk-badge--info">📍 Localized Flood Risk</span>
          <span class="risk-card__zone">Location Pending</span>
        </div>
        <p style="font-size:13px;color:var(--text-secondary);margin:8px 0;line-height:1.5;">
          Click <strong>"📍 Use My Location"</strong> above to identify your exact flood zone, current risk level, and official safety advice.
        </p>
        <div style="display:flex;align-items:center;gap:8px;margin-top:10px;flex-wrap:wrap;">
          <label for="select-manual-zone" style="font-size:12px;color:var(--text-muted);">Or select your zone manually:</label>
          <select id="select-manual-zone" class="form-control" style="width:auto;max-width:220px;padding:4px 8px;font-size:12px;" aria-label="Manually select your zone">
            <option value="">-- Choose Zone --</option>
            <option value="zone-a">Zone A — Riverside</option>
            <option value="zone-b">Zone B — Downtown</option>
            <option value="zone-c">Zone C — Westside</option>
            <option value="zone-d">Zone D — North Hills</option>
            <option value="zone-e">Zone E — Port Industrial</option>
          </select>
        </div>
      </div>
    `;
    attachManualZoneListener();
    return;
  }

  // Display actual backend response
  card.innerHTML = buildRiskCard(_currentCitizenZone, _currentCitizenCoords);
  attachManualZoneListener();
}

function buildRiskCard(zone, coords) {
  const colorMap = { severe: "#ef4444", high: "#f97316", moderate: "#f59e0b", low: "#22c55e" };
  const color = colorMap[zone.risk_level] || "#f59e0b";
  const pct = Math.round(zone.risk_score || 0);

  const riskLabel = zone.risk_level === "severe" ? "Severe" :
                    zone.risk_level === "high" ? "High" :
                    zone.risk_level === "moderate" ? "Moderate" : "Low";
  const shortName = zone.name.includes("—") ? zone.name.split("—")[0].trim() : zone.name;
  const currentZoneHeading = `You are currently in ${shortName} (${riskLabel} Flood Risk)`;

  const factorsHtml = (zone.factors || zone.contributing_factors || []).length > 0
    ? `<ul style="margin:8px 0 0 16px;padding:0;font-size:12px;color:var(--text-secondary);line-height:1.4;">
        ${(zone.factors || zone.contributing_factors).map(f => `<li>${f}</li>`).join("")}
       </ul>`
    : "";

  const coordsText = coords
    ? `<div style="font-size:11px;color:var(--text-muted);margin-top:8px;">📍 GPS: ${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)} &bull; Actual Real-Time Assessment</div>`
    : `<div style="font-size:11px;color:var(--text-muted);margin-top:8px;">📍 Manual Zone Selection (${zone.name})</div>`;

  return `
    <div class="risk-card" style="border-left: 4px solid ${color};">
      <div class="risk-card__header">
        <span class="risk-badge risk-badge--${zone.risk_level}">${zone.status || zone.category}</span>
        <span class="risk-card__zone" style="font-weight:700;">${currentZoneHeading}</span>
      </div>
      <div class="risk-card__score-row">
        <span class="risk-card__score" style="color:${color}">${pct}</span>
        <span class="risk-card__score-label">/ 100 Risk Score &bull; Category: ${zone.category || zone.severity || riskLabel}</span>
      </div>
      <div class="risk-card__bar">
        <div class="risk-card__bar-fill" style="width:${pct}%;background:${color};"></div>
      </div>
      <p class="risk-card__advice" style="margin-top:10px;"><strong>Action:</strong> ${zone.advice || "Stay alert and monitor official updates."}</p>
      ${factorsHtml}
      ${coordsText}
      <div style="margin-top:8px;display:flex;gap:8px;align-items:center;">
        <span style="font-size:11px;color:var(--text-muted);">Change zone:</span>
        <select id="select-manual-zone" class="form-control" style="width:auto;max-width:200px;padding:3px 8px;font-size:11px;" aria-label="Change Zone">
          <option value="zone-a" ${zone.id === 'zone-a' ? 'selected' : ''}>Zone A — Riverside</option>
          <option value="zone-b" ${zone.id === 'zone-b' ? 'selected' : ''}>Zone B — Downtown</option>
          <option value="zone-c" ${zone.id === 'zone-c' ? 'selected' : ''}>Zone C — Westside</option>
          <option value="zone-d" ${zone.id === 'zone-d' ? 'selected' : ''}>Zone D — North Hills</option>
          <option value="zone-e" ${zone.id === 'zone-e' ? 'selected' : ''}>Zone E — Port Industrial</option>
        </select>
      </div>
    </div>
  `;
}

export function renderUnavailableLocationState(errorMessage) {
  const card = document.getElementById("citizen-risk-card");
  if (!card) return;

  card.innerHTML = `
    <div class="risk-card" style="border-left: 4px solid var(--risk-moderate);background:rgba(245,158,11,0.06);">
      <div class="risk-card__header">
        <span class="risk-badge risk-badge--moderate">⚠️ Location Unavailable</span>
        <span class="risk-card__zone">Manual Selection Required</span>
      </div>
      <p style="font-size:13px;color:var(--text-secondary);margin:8px 0;line-height:1.5;">
        ${errorMessage}
      </p>
      <div style="margin-top:10px;display:flex;flex-direction:column;gap:6px;">
        <label for="select-manual-zone" style="font-size:12px;font-weight:600;color:var(--text-primary);">
          Select your neighborhood / zone manually:
        </label>
        <select id="select-manual-zone" class="form-control" style="max-width:280px;" aria-label="Select zone manually">
          <option value="">-- Choose Your Zone --</option>
          <option value="zone-a">Zone A — Riverside (Riverside Ave, River Basin)</option>
          <option value="zone-b">Zone B — Downtown (Central Park, Civic Plaza)</option>
          <option value="zone-c">Zone C — Westside (Stadium Road, Sports Arena)</option>
          <option value="zone-d">Zone D — North Hills (School Lane, Elevated)</option>
          <option value="zone-e">Zone E — Port Industrial (Port Gate, Coastal)</option>
        </select>
      </div>
    </div>
  `;
  attachManualZoneListener();
}

function renderOutsideZonesState(lat, lng) {
  const card = document.getElementById("citizen-risk-card");
  if (!card) return;

  card.innerHTML = `
    <div class="risk-card" style="border-left: 4px solid var(--risk-low);">
      <div class="risk-card__header">
        <span class="risk-badge risk-badge--low">ℹ️ Outside Monitored Flood Basin</span>
        <span class="risk-card__zone">No Direct Municipal Flood Risk</span>
      </div>
      <p style="font-size:13px;color:var(--text-secondary);margin:8px 0;line-height:1.5;">
        Coordinates detected: <strong>${lat.toFixed(4)}, ${lng.toFixed(4)}</strong>. You are currently outside monitored municipal flood risk zones. No active flood hazard detected for your position.
      </p>
      <div style="margin-top:8px;">
        <span style="font-size:11px;color:var(--text-muted);">View risk for another city zone:</span>
        <select id="select-manual-zone" class="form-control" style="width:auto;max-width:240px;margin-top:4px;" aria-label="Select zone">
          <option value="">-- Select Monitored Zone --</option>
          <option value="zone-a">Zone A — Riverside</option>
          <option value="zone-b">Zone B — Downtown</option>
          <option value="zone-c">Zone C — Westside</option>
          <option value="zone-d">Zone D — North Hills</option>
          <option value="zone-e">Zone E — Port Industrial</option>
        </select>
      </div>
    </div>
  `;
  attachManualZoneListener();
}

function attachManualZoneListener() {
  const select = document.getElementById("select-manual-zone");
  if (!select) return;

  select.onchange = async () => {
    const zoneId = select.value;
    if (!zoneId) return;

    const preset = ZONE_PRESETS[zoneId];
    if (preset) {
      _currentCitizenCoords = { ...preset.coords };
      const btn = document.getElementById("btn-use-location");
      if (btn) btn.textContent = `📍 Zone: ${preset.name.split("—")[0].trim()}`;
    }

    const zone = await getZoneRisk(zoneId);
    if (zone) {
      _currentCitizenZone = zone;
      loadRiskStatus();
      loadNearestShelters();
      updateSafeRouteCta(null, _currentCitizenCoords);
    }
  };
}

export function setupLocationButton() {
  const btn = document.getElementById("btn-use-location");
  if (!btn) return;

  btn.onclick = () => {
    if (!navigator.geolocation) {
      renderUnavailableLocationState("Geolocation is not supported by your browser. Please select your zone manually.");
      return;
    }

    btn.textContent = "📍 Detecting location…";
    btn.disabled = true;

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        _currentCitizenCoords = { lat, lng };

        btn.textContent = `📍 Location: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        btn.disabled = false;

        try {
          const zone = await getZoneRiskByCoordinates(lat, lng);
          if (zone && zone.name) {
            _currentCitizenZone = zone;
            loadRiskStatus();
            loadNearestShelters();
            updateSafeRouteCta(null, _currentCitizenCoords);
          } else {
            renderOutsideZonesState(lat, lng);
          }
        } catch (e) {
          renderUnavailableLocationState("Unable to retrieve risk data for your coordinates. Please choose a zone manually.");
        }
      },
      (err) => {
        btn.textContent = "📍 Use My Location";
        btn.disabled = false;

        let message = "Unable to retrieve location. Please select a zone manually.";
        if (err.code === 1) { // PERMISSION_DENIED
          message = "Location permission was denied. Please enable location permissions in browser settings or select your zone manually.";
        } else if (err.code === 2) { // POSITION_UNAVAILABLE
          message = "Location information is currently unavailable from your device or network. Please select your zone manually.";
        } else if (err.code === 3) { // TIMEOUT
          message = "Location request timed out. Please try again or select your zone manually.";
        }

        renderUnavailableLocationState(message);
      },
      { timeout: 10000, enableHighAccuracy: true, maximumAge: 30000 }
    );
  };
}

// ---------------------------------------------------------------------------
// Distance Calculation Helper (Haversine formula)
// ---------------------------------------------------------------------------
function calculateHaversineKm(lat1, lon1, lat2, lon2) {
  if (lat1 == null || lon1 == null || lat2 == null || lon2 == null) return null;
  const R = 6371; // Earth radius in km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// ---------------------------------------------------------------------------
// Nearest Shelter Card
// ---------------------------------------------------------------------------
export async function loadNearestShelters() {
  const card = document.getElementById("citizen-shelter-card");
  if (!card) return;

  const shelters = await getShelters();

  let available = shelters
    ? shelters.filter(s => s.status !== "FULL" && s.status !== "STANDBY" && ((s.capacity - (s.occupancy || 0)) > 0))
    : _fallbackShelters();

  // If user coordinates are known, sort by actual distance from user
  if (_currentCitizenCoords) {
    available.forEach(s => {
      const d = calculateHaversineKm(_currentCitizenCoords.lat, _currentCitizenCoords.lng, s.lat, s.lng);
      if (d !== null) {
        s.distance_km = parseFloat(d.toFixed(1));
      }
    });
    available.sort((a, b) => (a.distance_km || 99) - (b.distance_km || 99));
  }

  const topAvailable = available.slice(0, 2);

  card.innerHTML = `
    <div class="card-title">🏥 Nearest Safe Shelters</div>
    ${topAvailable.length > 0 ? topAvailable.map(s => buildShelterRow(s)).join("") : '<div class="empty-state">No open shelters available nearby.</div>'}
    <a href="citizen-shelters.html" class="view-all-link">View all shelters →</a>
  `;
}

function buildShelterRow(shelter) {
  const pct = Math.round((shelter.occupancy / shelter.capacity) * 100);
  const statusColor = { OPEN: "var(--risk-low)", NEAR_CAPACITY: "var(--risk-moderate)", STANDBY: "var(--text-muted)" };
  return `
    <div class="shelter-row">
      <div class="shelter-row__name">${shelter.name}</div>
      <div class="shelter-row__meta">
        ${shelter.distance_km} km away &bull;
        <span style="color:${statusColor[shelter.status] || 'var(--risk-moderate)'};font-weight:600;">${shelter.status}</span> &bull;
        ${shelter.occupancy}/${shelter.capacity} occupied (${pct}%)
      </div>
    </div>
  `;
}

function _fallbackShelters() {
  return [
    { id: "shelter-b", name: "Shelter B — Central School", status: "OPEN", occupancy: 45, capacity: 400, distance_km: 0.8 },
    { id: "shelter-a", name: "Shelter A — Community Hall", status: "NEAR_CAPACITY", occupancy: 410, capacity: 500, distance_km: 1.5 },
  ];
}

// ---------------------------------------------------------------------------
// One-Click Shelter Navigation
// ---------------------------------------------------------------------------
export function setupShelterNavigation() {
  const btn = document.getElementById("btn-navigate-closest-shelter");
  const statusDiv = document.getElementById("shelter-nav-status");
  if (!btn) return;

  btn.onclick = async () => {
    btn.disabled = true;
    btn.textContent = "🔄 Finding safest available shelter…";
    if (statusDiv) {
      statusDiv.innerHTML = `<span style="color:var(--text-muted);">Checking shelter availability and computing risk-aware route…</span>`;
    }

    // 1. Origin coordinates: use citizen's detected or chosen location, or default origin
    const origin = _currentCitizenCoords || { lat: 18.5260, lng: 73.8580 };

    // 2. Fetch live shelters
    const shelters = await getShelters();
    if (!shelters || shelters.length === 0) {
      if (statusDiv) {
        statusDiv.innerHTML = `<div class="alert alert--danger">⚠️ Unable to load shelter data from emergency services.</div>`;
      }
      btn.disabled = false;
      btn.textContent = "🧭 Navigate to Closest Available Shelter";
      return;
    }

    // 3. Filter candidates: must be OPEN or NEAR_CAPACITY, with available capacity
    const candidates = shelters.filter(s => {
      const isOpenOrNear = s.status === "OPEN" || s.status === "NEAR_CAPACITY";
      const hasCapacity = (s.capacity - (s.occupancy || 0)) > 0;
      return isOpenOrNear && hasCapacity;
    });

    if (candidates.length === 0) {
      if (statusDiv) {
        statusDiv.innerHTML = `
          <div class="alert alert--danger">
            ⚠️ All emergency shelters are currently at maximum capacity or on standby. No open shelter available.
            Move to high ground and await official emergency dispatch.
          </div>
        `;
      }
      btn.disabled = false;
      btn.textContent = "🧭 Navigate to Closest Available Shelter";
      return;
    }

    // 4. Sort candidates by distance from origin
    candidates.forEach(s => {
      s._distKm = calculateHaversineKm(origin.lat, origin.lng, s.lat, s.lng) ?? s.distance_km ?? 999;
    });
    candidates.sort((a, b) => a._distKm - b._distKm);

    // 5. Test route with risk-aware routing API for each candidate in order of proximity
    let selectedShelter = null;
    let bestRoute = null;

    for (const candidate of candidates) {
      try {
        const routeRes = await getSafeRoute({
          origin_lat: origin.lat,
          origin_lng: origin.lng,
          shelter_id: candidate.id,
          destination_id: candidate.id,
          travel_mode: "vehicle",
        });

        if (
          routeRes &&
          routeRes.ok !== false &&
          (routeRes.route || routeRes.geometry || routeRes.status === "SIMULATED_SAFE" || routeRes.status === "SIMULATED_CAUTION" || routeRes.status === "SUCCESS")
        ) {
          selectedShelter = candidate;
          bestRoute = routeRes;
          break;
        }
      } catch (e) {
        // Try next candidate
      }
    }

    // 6. Handle case where no safe route is available
    if (!selectedShelter) {
      if (statusDiv) {
        statusDiv.innerHTML = `
          <div class="alert alert--danger">
            ⚠️ No safe evacuation route could be found to open shelters due to flooded corridors or submerged bridges.
            Do not risk driving through water. Seek high ground immediately and call emergency services (112 / 108).
          </div>
        `;
      }
      btn.disabled = false;
      btn.textContent = "🧭 Navigate to Closest Available Shelter";
      return;
    }

    // 7. Successful selection: Navigate to citizen-route.html with shelter query param
    if (statusDiv) {
      statusDiv.innerHTML = `
        <div class="alert alert--success">
          ✅ Closest safe shelter found: <strong>${selectedShelter.name}</strong> (${selectedShelter.status}).
          Redirecting to Safe Route Navigator…
        </div>
      `;
    }

    updateSafeRouteCta(selectedShelter.id, origin);

    const targetUrl = `citizen-route.html?shelter=${encodeURIComponent(selectedShelter.id)}&lat=${origin.lat}&lng=${origin.lng}`;
    setTimeout(() => {
      window.location.href = targetUrl;
    }, 400);
  };
}

function updateSafeRouteCta(shelterId, origin) {
  const cta = document.getElementById("cta-safe-route");
  if (!cta) return;
  const qOrigin = origin ? `&lat=${origin.lat}&lng=${origin.lng}` : "";
  cta.href = `citizen-route.html?shelter=${encodeURIComponent(shelterId || "shelter-b")}${qOrigin}`;
}

// ---------------------------------------------------------------------------
// Real-Time SSE Stream for Citizen UI
// ---------------------------------------------------------------------------
export function initCitizenStream() {
  if (typeof EventSource === "undefined") return;
  if (_citizenEventSource) return;

  try {
    const sseUrl = getIncidentsStreamUrl();
    _citizenEventSource = new EventSource(sseUrl);

    _citizenEventSource.addEventListener("evacuation", () => {
      loadActiveEvacuationAlert();
    });

    _citizenEventSource.addEventListener("shelter", () => {
      loadNearestShelters();
    });

    _citizenEventSource.addEventListener("decision", () => {
      loadActiveEvacuationAlert();
      loadNearestShelters();
    });

    _citizenEventSource.onerror = () => {
      // Automatic reconnect
    };
  } catch (e) {
    console.warn("Could not initialize citizen SSE stream:", e);
  }
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  loadActiveEvacuationAlert();
  loadRiskStatus();
  loadNearestShelters();
  setupLocationButton();
  setupShelterNavigation();
  initCitizenStream();
});


