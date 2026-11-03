/**
 * ClimateOS — Citizen Mode: Home Page Controller
 * File owner: Citizen Mode feature team
 *
 * Handles: Risk status card, nearest shelter card, geolocation
 */

import { getZoneRisk, getShelters, getActiveEvacuations, getIncidentsStreamUrl } from "../api.js";

// ---------------------------------------------------------------------------
// Active Evacuation Alert Banner (Human Authority Decision)
// ---------------------------------------------------------------------------
let _citizenEventSource = null;

export async function loadActiveEvacuationAlert() {
  const banner = document.getElementById("citizen-emergency-alert");
  if (!banner) return;

  const evacuations = await getActiveEvacuations();
  const hasActiveEvac = evacuations && evacuations.length > 0;

  if (hasActiveEvac) {
    // Authorized emergency evacuation order active
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
        📍 Use My Location
      </button>
    `;
  } else {
    // Normal watch / advisory state (Unapproved AI recommendations are never treated as official orders)
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
        📍 Use My Location
      </button>
    `;
  }
  setupLocationButton();
}

// ---------------------------------------------------------------------------
// Risk Status Card
// ---------------------------------------------------------------------------
export async function loadRiskStatus() {
  const card = document.getElementById("citizen-risk-card");
  if (!card) return;

  const zone = await getZoneRisk("zone-a");

  if (!zone) {
    // Fallback: display hardcoded demo values when backend is offline
    card.innerHTML = buildRiskCard({
      name: "Zone A — Riverside",
      status: "HIGH RISK",
      risk_score: 88,
      risk_level: "severe",
      advice: "Flash flood warning active. Move to high ground immediately.",
    });
    return;
  }

  card.innerHTML = buildRiskCard(zone);
}

function buildRiskCard(zone) {
  const colorMap = { severe: "#ef4444", high: "#f97316", moderate: "#f59e0b", low: "#22c55e" };
  const color = colorMap[zone.risk_level] || "#f59e0b";
  const pct = zone.risk_score;
  return `
    <div class="risk-card" style="border-left: 4px solid ${color};">
      <div class="risk-card__header">
        <span class="risk-badge risk-badge--${zone.risk_level}">${zone.status}</span>
        <span class="risk-card__zone">${zone.name}</span>
      </div>
      <div class="risk-card__score-row">
        <span class="risk-card__score" style="color:${color}">${pct}</span>
        <span class="risk-card__score-label">/ 100 Risk Score</span>
      </div>
      <div class="risk-card__bar">
        <div class="risk-card__bar-fill" style="width:${pct}%;background:${color};"></div>
      </div>
      <p class="risk-card__advice">${zone.advice || "Stay alert and monitor official updates."}</p>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Nearest Shelter Card
// ---------------------------------------------------------------------------
export async function loadNearestShelters() {
  const card = document.getElementById("citizen-shelter-card");
  if (!card) return;

  const shelters = await getShelters();

  const available = shelters
    ? shelters.filter(s => s.status !== "FULL" && s.status !== "STANDBY").slice(0, 2)
    : _fallbackShelters();

  card.innerHTML = `
    <div class="card-title">🏥 Nearest Safe Shelters</div>
    ${available.map(s => buildShelterRow(s)).join("")}
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
    { name: "Shelter B — Central School", status: "OPEN",         occupancy: 45,  capacity: 400, distance_km: 0.8 },
    { name: "Shelter A — Community Hall", status: "NEAR_CAPACITY", occupancy: 410, capacity: 500, distance_km: 1.5 },
  ];
}

// ---------------------------------------------------------------------------
// Use My Location button
// ---------------------------------------------------------------------------
function setupLocationButton() {
  const btn = document.getElementById("btn-use-location");
  if (!btn) return;

  btn.onclick = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser.");
      return;
    }
    btn.textContent = "📍 Getting location…";
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        btn.textContent = `📍 Location: ${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`;
      },
      () => {
        btn.textContent = "📍 Use My Location";
        alert("Unable to access location. Please enable location permissions.");
      }
    );
  };
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
  initCitizenStream();
});

