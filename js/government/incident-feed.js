/**
 * ClimateOS — Government Mode: Incident Feed Panel
 * File owner: Government Dashboard / Incident team
 *
 * Renders ranked incidents with confidence badges (High Confidence / Needs Review / Low Confidence)
 */

import { getIncidents, getIncidentsStreamUrl } from "../api.js";

const CONFIDENCE_BADGE = {
  "High Confidence": { cls: "badge--high",   label: "High Confidence" },
  "Needs Review":    { cls: "badge--review", label: "Needs Review"    },
  "Low Confidence":  { cls: "badge--low",    label: "Low Confidence"  },
};

const CATEGORY_ICONS = {
  trapped:         "🆘",
  flood:           "🌊",
  fire:            "🔥",
  road:            "🚧",
  medical:         "🚑",
  power_failure:   "⚡",
  water_shortage:  "🚰",
  infrastructure:  "🏢",
};

const _renderedIncidentIds = new Set();
let _incidentEventSource = null;

export async function loadIncidentFeed() {
  const container = document.getElementById("incident-feed");
  if (!container) return;

  container.innerHTML = `<div class="loading-state">Loading incidents…</div>`;

  const incidents = await getIncidents();
  _renderedIncidentIds.clear();

  if (!incidents || incidents.length === 0) {
    container.innerHTML = `<div class="empty-state">No active incidents.</div>`;
    return;
  }

  incidents.forEach(inc => _renderedIncidentIds.add(String(inc.id)));
  container.innerHTML = incidents.map((inc, idx) => buildIncidentItem(inc, idx + 1)).join("");
}

export function handleLiveIncident(rawIncident) {
  const inc = rawIncident.incident || rawIncident;
  if (!inc || !inc.id) return;
  const idStr = String(inc.id);
  if (_renderedIncidentIds.has(idStr)) return; // Avoid duplicate incident display

  _renderedIncidentIds.add(idStr);

  const container = document.getElementById("incident-feed");
  if (!container) return;

  // Clear loading or empty state
  const placeholder = container.querySelector(".empty-state, .loading-state");
  if (placeholder) {
    placeholder.remove();
  }

  const html = buildIncidentItem(inc, 1);
  container.insertAdjacentHTML("afterbegin", html);

  // Re-number rank badges
  const items = container.querySelectorAll(".incident-item");
  items.forEach((item, idx) => {
    const rankSpan = item.querySelector(".incident-item__rank");
    if (rankSpan) rankSpan.textContent = `#${idx + 1}`;
  });

  // Micro-interaction highlight
  const newItem = document.getElementById(`incident-${inc.id}`);
  if (newItem) {
    newItem.style.animation = "pulse 1.5s ease-in-out";
  }
}

export function initIncidentFeedStream() {
  if (typeof EventSource === "undefined") return;
  if (_incidentEventSource) return;

  try {
    const sseUrl = getIncidentsStreamUrl();
    _incidentEventSource = new EventSource(sseUrl);

    _incidentEventSource.addEventListener("incident", (event) => {
      try {
        const data = JSON.parse(event.data);
        handleLiveIncident(data);
      } catch (e) {
        console.error("Error parsing live incident event:", e);
      }
    });

    _incidentEventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data && (data.id || data.incident)) {
          handleLiveIncident(data);
        }
      } catch (e) {}
    };

    _incidentEventSource.onerror = () => {
      // Browser EventSource automatically reconnects with Last-Event-ID
    };
  } catch (err) {
    console.warn("Could not initialize incident SSE stream:", err);
  }
}

function buildIncidentItem(inc, rank) {
  const badge = CONFIDENCE_BADGE[inc.confidence_label] || CONFIDENCE_BADGE["Needs Review"];
  const icon  = CATEGORY_ICONS[inc.category] || "⚠️";
  const priority = Number(inc.priority_score || 0);
  const priorityColor = priority >= 85 ? "var(--risk-severe)"
                      : priority >= 60 ? "var(--risk-high)"
                      : "var(--risk-moderate)";

  return `
    <div class="incident-item" id="incident-${inc.id}" data-id="${inc.id}">
      <div class="incident-item__header">
        <span class="incident-item__rank">#${rank}</span>
        <span class="incident-item__type">${icon} ${(inc.category || "emergency").replace("_", " ")}</span>
        <span class="badge ${badge.cls}">${badge.label}</span>
      </div>
      <div class="incident-item__location">📍 ${inc.location || "Unknown"}</div>
      <div class="incident-item__desc">${inc.description || ""}</div>
      <div class="incident-item__footer">
        <span style="color:${priorityColor};font-weight:700;">Priority: ${priority}/100</span>
        ${inc.trapped_count > 0 ? `<span class="tag tag--danger">🆘 ${inc.trapped_count} trapped</span>` : ""}
        ${inc.injured_count > 0 ? `<span class="tag tag--warning">🤕 ${inc.injured_count} injured</span>` : ""}
        <span style="color:var(--text-muted);font-size:11px;">AI: ${inc.confidence_score || 0}%</span>
      </div>
    </div>
  `;
}

document.addEventListener("DOMContentLoaded", () => {
  loadIncidentFeed();
  initIncidentFeedStream();
});

