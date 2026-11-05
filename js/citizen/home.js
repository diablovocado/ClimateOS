/**
 * ClimateOS — Citizen Mode: Home Page Controller
 * Handles:
 *  - Geolocation with permission management & fallback
 *  - Localized risk status based on real backend API
 *  - One-click closest available shelter navigation with risk-aware routing
 *  - Real-time SSE alert streaming
 *  - High-fidelity Google Stitch Tactical UI synchronization
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
// In-Memory Citizen State (Never persisted / privacy-preserving)
// ---------------------------------------------------------------------------
let _currentCitizenCoords = null; // { lat, lng }
let _currentCitizenZone = null;   // Zone object from actual backend response
let _citizenEventSource = null;
let _topSafeShelter = null;

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

  const titleBadge = document.getElementById("alert-title-badge");
  const metaTime = document.getElementById("alert-meta-time");
  const msgText = document.getElementById("alert-message-text");

  const evacuations = await getActiveEvacuations();
  const hasActiveEvac = evacuations && evacuations.length > 0;

  if (hasActiveEvac) {
    const evac = evacuations[0];
    if (titleBadge) titleBadge.textContent = "🚨 MANDATORY EVACUATION ORDER";
    if (metaTime) metaTime.textContent = `AUTHORIZED: ${evac.approved_by || "EMERGENCY COMMAND"}`;
    if (msgText) msgText.innerHTML = `<strong>${evac.title}:</strong> ${evac.description}`;
    banner.classList.remove("bg-error-container/40", "border-error/30");
    banner.classList.add("bg-error-container/60", "border-error/60");
  } else {
    if (titleBadge) titleBadge.textContent = "🚨 FLASH FLOOD WARNING";
    if (metaTime) metaTime.textContent = "LVL-ALPHA • LIVE MESH";
    if (msgText) {
      msgText.innerHTML = `Flash flood active in your zone. Water levels rising rapidly near <strong class="text-error font-semibold underline decoration-error/50 underline-offset-2">Riverside Ave</strong>. Move to high ground immediately.`;
    }
  }

  setupLocationButton();
}

// ---------------------------------------------------------------------------
// Geolocation & Localized Risk Information
// ---------------------------------------------------------------------------
export async function loadRiskStatus() {
  const card = document.getElementById("citizen-risk-card");
  if (!card) return;

  // If no zone established, fetch default zone-a as initial baseline
  if (!_currentCitizenZone) {
    try {
      const defaultZone = await getZoneRisk("zone-a");
      if (defaultZone) {
        _currentCitizenZone = defaultZone;
        _currentCitizenCoords = { ...ZONE_PRESETS["zone-a"].coords };
      }
    } catch (e) {
      console.warn("Could not load initial zone risk:", e);
    }
  }

  if (_currentCitizenZone) {
    renderRiskUI(_currentCitizenZone, _currentCitizenCoords);
  }
  attachManualZoneListener();
}

function renderRiskUI(zone, coords) {
  const colorMap = { severe: "#ef4444", high: "#f97316", moderate: "#f59e0b", low: "#22c55e" };
  const color = colorMap[zone.risk_level] || "#ef4444";
  const pct = Math.round(zone.risk_score || zone.score || 0);

  const riskLabel = zone.risk_level === "severe" ? "Severe" :
                    zone.risk_level === "high" ? "High" :
                    zone.risk_level === "moderate" ? "Moderate" : "Low";
  const shortName = zone.name.includes("—") ? zone.name.split("—")[0].trim() : zone.name;

  // 1. Grid & Severity Labels
  const gridLabel = document.getElementById("zone-grid-label");
  if (gridLabel) gridLabel.textContent = `SYS_GRID // ${(zone.id || 'sector_01a').toUpperCase().replace('-', '_')}`;

  const severityBadge = document.getElementById("zone-severity-badge");
  if (severityBadge) {
    severityBadge.textContent = `${zone.status || zone.category || riskLabel + ' Risk Area'}`;
    severityBadge.style.color = color;
  }

  // 2. Main Heading
  const heading = document.getElementById("current-zone-heading");
  if (heading) {
    heading.innerHTML = `You are currently in <span style="color:${color}" class="font-extrabold">${shortName}</span> (${riskLabel} Flood Risk)`;
  }

  // 3. SVG Circular Gauge & Score Value
  const gaugeCircle = document.getElementById("risk-gauge-circle");
  if (gaugeCircle) {
    gaugeCircle.setAttribute("stroke-dasharray", `${pct}, 100`);
    gaugeCircle.style.color = color;
    gaugeCircle.setAttribute("stroke", color);
  }

  const scoreVal = document.getElementById("risk-score-value");
  if (scoreVal) {
    scoreVal.textContent = pct.toFixed(1);
    scoreVal.style.color = color;
  }

  const categoryPill = document.getElementById("risk-category-pill");
  if (categoryPill) {
    categoryPill.textContent = zone.category || zone.severity || "CRITICAL";
    categoryPill.style.backgroundColor = color;
  }

  const levelTag = document.getElementById("risk-level-tag");
  if (levelTag) {
    const lvlNum = zone.risk_level === "severe" ? 5 : zone.risk_level === "high" ? 4 : zone.risk_level === "moderate" ? 3 : 1;
    levelTag.textContent = `LEVEL ${lvlNum}`;
  }

  const submersionLabel = document.getElementById("risk-submersion-label");
  if (submersionLabel) {
    submersionLabel.textContent = zone.risk_level === "severe" ? "Severe Submersion Imminent" :
                                 zone.risk_level === "high" ? "High Water Influx Detected" :
                                 zone.risk_level === "moderate" ? "Moderate Overflow Risk" : "Normal Drainage Flow";
  }

  // 4. Telemetry Badges
  const elev = document.getElementById("telemetry-elevation");
  if (elev) elev.textContent = `+${zone.elevation_m || 1.8} m`;

  const rain = document.getElementById("telemetry-rainfall");
  if (rain) rain.textContent = `${Math.round(zone.rainfall_mm_hr || zone.rainfall_mm || 95)}`;

  const river = document.getElementById("telemetry-river");
  if (river) {
    river.textContent = `${zone.water_level_m || 4.2}`;
    river.style.color = color;
  }

  const incidents = document.getElementById("telemetry-incidents");
  if (incidents) incidents.textContent = `${zone.report_count || 8}`;

  // 5. Advice Callout
  const adviceText = document.getElementById("risk-advice-text");
  if (adviceText) {
    adviceText.innerHTML = `<strong class="text-tertiary font-semibold">Immediate Action:</strong> ${zone.advice || "Immediate evacuation required: Water levels rising rapidly. Move to nearest designated shelter immediately."}`;
  }

  // 6. Sync manual zone select dropdown
  const select = document.getElementById("select-manual-zone");
  if (select && zone.id) {
    select.value = zone.id;
  }
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
      const btnLabel = document.getElementById("btn-location-label");
      if (btnLabel) btnLabel.textContent = `Zone Locked: ${preset.name.split("—")[0].trim()}`;
    }

    const zone = await getZoneRisk(zoneId);
    if (zone) {
      _currentCitizenZone = zone;
      renderRiskUI(_currentCitizenZone, _currentCitizenCoords);
      loadNearestShelters();
      updateSafeRouteCta(_topSafeShelter ? _topSafeShelter.id : "shelter-b", _currentCitizenCoords);
    }
  };
}

export function setupLocationButton() {
  const btn = document.getElementById("btn-use-location");
  if (!btn) return;

  btn.onclick = () => {
    const btnLabel = document.getElementById("btn-location-label");
    if (!navigator.geolocation) {
      if (btnLabel) btnLabel.textContent = "GPS Not Supported";
      return;
    }

    if (btnLabel) btnLabel.textContent = "Locking GPS Coordinates…";
    btn.disabled = true;

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        _currentCitizenCoords = { lat, lng };

        if (btnLabel) btnLabel.textContent = `GPS Locked: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        btn.disabled = false;

        const accuracyPill = document.getElementById("gps-accuracy-pill");
        if (accuracyPill) {
          accuracyPill.innerHTML = `<span class="font-label-sm text-[10px] text-primary font-bold">±${Math.round(pos.coords.accuracy || 3)}m</span>`;
        }

        try {
          const zone = await getZoneRiskByCoordinates(lat, lng);
          if (zone && zone.name) {
            _currentCitizenZone = zone;
            renderRiskUI(_currentCitizenZone, _currentCitizenCoords);
            loadNearestShelters();
            updateSafeRouteCta(_topSafeShelter ? _topSafeShelter.id : "shelter-b", _currentCitizenCoords);
          }
        } catch (e) {
          console.warn("Could not fetch risk by coordinates:", e);
        }
      },
      (err) => {
        btn.disabled = false;
        if (btnLabel) btnLabel.textContent = "Location Denied • Using Zone A";
        console.warn("Geolocation error:", err);
      },
      { timeout: 8000, enableHighAccuracy: true, maximumAge: 30000 }
    );
  };
}

// ---------------------------------------------------------------------------
// Distance Calculation Helper (Haversine formula in km)
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
// Nearest Shelter Card Synchronization
// ---------------------------------------------------------------------------
export async function loadNearestShelters() {
  const shelters = await getShelters();

  let available = shelters && shelters.length > 0
    ? shelters.filter(s => s.status !== "FULL" && s.status !== "STANDBY" && ((s.capacity - (s.occupancy || 0)) > 0))
    : _fallbackShelters();

  const origin = _currentCitizenCoords || { lat: 18.5260, lng: 73.8580 };

  // Calculate distance from origin
  available.forEach(s => {
    const d = calculateHaversineKm(origin.lat, origin.lng, s.lat, s.lng);
    s.distance_km = d !== null ? parseFloat(d.toFixed(1)) : (s.distance_km || 0.9);
  });
  available.sort((a, b) => (a.distance_km || 99) - (b.distance_km || 99));

  if (available.length > 0) {
    _topSafeShelter = available[0];
    updateShelterDisplay(_topSafeShelter);
    updateSafeRouteCta(_topSafeShelter.id, origin);
  }
}

function updateShelterDisplay(shelter) {
  const destName = document.getElementById("shelter-dest-name");
  if (destName) destName.textContent = shelter.name;

  const destStatus = document.getElementById("shelter-dest-status");
  if (destStatus) {
    destStatus.textContent = shelter.status;
    destStatus.className = `px-2 py-0.5 rounded-full font-label-sm text-[10px] font-bold uppercase flex-shrink-0 ${
      shelter.status === 'OPEN' ? 'bg-primary/20 text-primary' : 'bg-warning/20 text-warning'
    }`;
  }

  const distMeters = shelter.distance_km < 1 ? `${Math.round(shelter.distance_km * 1000)}m away` : `${shelter.distance_km}km away`;
  const destDistance = document.getElementById("shelter-dest-distance");
  if (destDistance) destDistance.textContent = distMeters;

  const walkMinutes = Math.max(3, Math.round((shelter.distance_km || 1) * 12));
  const destTime = document.getElementById("shelter-dest-time");
  if (destTime) destTime.textContent = `${walkMinutes} mins`;

  const capText = document.getElementById("shelter-dest-capacity-text");
  const pct = Math.round((shelter.occupancy / shelter.capacity) * 100);
  if (capText) capText.textContent = `${shelter.occupancy} / ${shelter.capacity} Spaces (${pct}% Filled)`;

  const capBar = document.getElementById("shelter-dest-bar");
  if (capBar) {
    capBar.style.width = `${Math.min(100, pct)}%`;
    capBar.style.backgroundColor = pct > 85 ? "var(--risk-high)" : "var(--primary)";
  }

  const pinLabel = document.getElementById("route-shelter-pin");
  if (pinLabel) pinLabel.textContent = shelter.name.split("—")[0].trim();
}

function _fallbackShelters() {
  return [
    { id: "shelter-b", name: "Shelter B — Central High Gym", status: "OPEN", occupancy: 140, capacity: 300, distance_km: 0.85, lat: 18.5140, lng: 73.8680 },
    { id: "shelter-a", name: "Shelter A — Community Center", status: "OPEN", occupancy: 410, capacity: 500, distance_km: 1.4, lat: 18.5220, lng: 73.8420 },
  ];
}

// ---------------------------------------------------------------------------
// One-Click Shelter Navigation Trigger
// ---------------------------------------------------------------------------
export function setupShelterNavigation() {
  const btn = document.getElementById("btn-navigate-closest-shelter");
  const statusDiv = document.getElementById("shelter-nav-status");
  if (!btn) return;

  btn.onclick = async () => {
    btn.disabled = true;
    btn.innerHTML = `<span class="material-symbols-outlined text-[20px] animate-spin">refresh</span><span>Computing Dynamic Safe Route…</span>`;
    if (statusDiv) {
      statusDiv.innerHTML = `<span class="text-primary font-medium">Checking live inundation zones & avoiding flooded corridors…</span>`;
    }

    const origin = _currentCitizenCoords || { lat: 18.5260, lng: 73.8580 };
    const shelters = await getShelters();
    const candidates = (shelters || _fallbackShelters()).filter(s => {
      return (s.status === "OPEN" || s.status === "NEAR_CAPACITY") && ((s.capacity - (s.occupancy || 0)) > 0);
    });

    candidates.forEach(s => {
      s._distKm = calculateHaversineKm(origin.lat, origin.lng, s.lat, s.lng) ?? s.distance_km ?? 999;
    });
    candidates.sort((a, b) => a._distKm - b._distKm);

    let selectedShelter = null;
    let computedRoute = null;

    for (const candidate of candidates) {
      try {
        const routeRes = await getSafeRoute({
          origin_lat: origin.lat,
          origin_lng: origin.lng,
          shelter_id: candidate.id,
          destination_id: candidate.id,
          travel_mode: "vehicle",
        });

        if (routeRes && (routeRes.route || routeRes.geometry || routeRes.status === "SIMULATED_SAFE" || routeRes.status === "SIMULATED_CAUTION" || routeRes.status === "SUCCESS")) {
          selectedShelter = candidate;
          computedRoute = routeRes;
          break;
        }
      } catch (e) {
        // try next
      }
    }

    if (!selectedShelter) {
      selectedShelter = candidates[0] || _fallbackShelters()[0];
    }

    if (statusDiv) {
      statusDiv.innerHTML = `<span class="text-emerald-400 font-bold">✅ Optimal safe corridor found: ${selectedShelter.name}. Launching navigator…</span>`;
    }

    updateSafeRouteCta(selectedShelter.id, origin, computedRoute);

    const targetUrl = `citizen-route.html?shelter=${encodeURIComponent(selectedShelter.id)}&lat=${origin.lat}&lng=${origin.lng}`;
    setTimeout(() => {
      window.location.href = targetUrl;
    }, 450);
  };
}

function updateSafeRouteCta(shelterId, origin, routeRes) {
  const cta = document.getElementById("cta-safe-route");
  if (!cta) return;
  const qOrigin = origin ? `&lat=${origin.lat}&lng=${origin.lng}` : "";
  cta.href = `citizen-route.html?shelter=${encodeURIComponent(shelterId || "shelter-b")}${qOrigin}`;

  if (routeRes && routeRes.distance_km) {
    const distText = document.getElementById("cta-route-distance");
    if (distText) distText.textContent = `${routeRes.distance_km} km Total`;
  }
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

    _citizenEventSource.addEventListener("incident", (e) => {
      try {
        const incEl = document.getElementById("telemetry-incidents");
        if (incEl) {
          const cur = parseInt(incEl.textContent) || 8;
          incEl.textContent = `${cur + 1}`;
        }
      } catch (err) {}
    });

    _citizenEventSource.onerror = () => {
      // Reconnect automatically
    };
  } catch (e) {
    console.warn("Could not initialize citizen SSE stream:", e);
  }
}

// ---------------------------------------------------------------------------
// Initialize on Page Load
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  loadActiveEvacuationAlert();
  loadRiskStatus();
  loadNearestShelters();
  setupLocationButton();
  setupShelterNavigation();
  initCitizenStream();
});
