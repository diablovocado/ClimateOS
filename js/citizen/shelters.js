/**
 * ClimateOS — Citizen Mode: Shelters List Page Controller
 * File owner: Citizen Mode / Shelter Intelligence team
 */

import { getShelters, getIncidentsStreamUrl } from "../api.js";

const STATUS_META = {
  OPEN:          { label: "Open",         color: "var(--risk-low)",      icon: "✅" },
  NEAR_CAPACITY: { label: "Near Capacity", color: "var(--risk-moderate)", icon: "⚠️" },
  FULL:          { label: "Full",          color: "var(--risk-severe)",   icon: "🔴" },
  STANDBY:       { label: "Standby",       color: "var(--text-muted)",    icon: "⏸️" },
};

let _shelterEventSource = null;

export async function loadShelters() {
  const listEl = document.getElementById("shelter-list");
  if (!listEl) return;

  const shelters = await getShelters();
  if (!shelters || shelters.length === 0) {
    listEl.innerHTML = `<div class="empty-state">No shelter data available.</div>`;
    return;
  }

  listEl.innerHTML = shelters.map(s => buildShelterCard(s)).join("");
}

export function initSheltersStream() {
  if (typeof EventSource === "undefined") return;
  if (_shelterEventSource) return;

  try {
    const sseUrl = getIncidentsStreamUrl();
    _shelterEventSource = new EventSource(sseUrl);

    _shelterEventSource.addEventListener("shelter", () => {
      loadShelters();
    });

    _shelterEventSource.addEventListener("decision", () => {
      loadShelters();
    });

    _shelterEventSource.onerror = () => {
      // Automatic reconnect
    };
  } catch (e) {
    console.warn("Could not initialize shelters SSE stream:", e);
  }
}

function buildShelterCard(s) {
  const meta   = STATUS_META[s.status] || STATUS_META.STANDBY;
  const pct    = Math.round((s.occupancy / s.capacity) * 100);
  const barColor = meta.color;

  return `
    <div class="shelter-card glass-card" id="shelter-${s.id}">
      <div class="shelter-card__header">
        <h3 class="shelter-card__name">${s.name}</h3>
        <span class="badge badge--status" style="color:${barColor};border-color:${barColor};">
          ${meta.icon} ${meta.label}
        </span>
      </div>
      <p class="shelter-card__address">📍 ${s.address}</p>
      <div class="shelter-card__capacity">
        <span>${s.occupancy} / ${s.capacity} occupied</span>
        <span>${pct}%</span>
      </div>
      <div class="progress-bar">
        <div class="progress-bar__fill" style="width:${pct}%;background:${barColor};"></div>
      </div>
      <div class="shelter-card__tags">
        ${(s.accessibility || []).map(a => `<span class="tag">${a}</span>`).join("")}
        ${(s.facilities || []).map(f => `<span class="tag tag--facility">${f}</span>`).join("")}
      </div>
      <div class="shelter-card__footer">
        <a href="tel:${s.contact}" class="btn-link">📞 ${s.contact}</a>
        <span class="shelter-card__dist">${s.distance_km} km away</span>
      </div>
    </div>
  `;
}

document.addEventListener("DOMContentLoaded", () => {
  loadShelters();
  initSheltersStream();
});

