/**
 * ClimateOS — Citizen Mode: Safe Route Page Controller
 * Calculates and visualizes the safest evacuation route to emergency shelters.
 * Integrates with FastAPI routing engine and Leaflet GIS mapping.
 */

import { getSafeRoute, getShelters } from "../api.js";

// Citizen origin coordinates: Zone A (Riverside Avenue) default
const DEFAULT_ORIGIN = {
  lat: 18.5260,
  lng: 73.8580,
  name: "142 Riverside Avenue, Zone A"
};

class SafeRouteController {
  constructor() {
    this.map = null;
    this.routeLayer = null;
    this.markersLayer = null;
    this.shelters = [];
    this.selectedShelterId = "shelter-b";
    this.travelMode = "vehicle"; // "vehicle" | "pedestrian"
    this.origin = { ...DEFAULT_ORIGIN };
  }

  async init() {
    const container = document.getElementById("safe-route-content");
    if (!container) return;

    // Parse shelter from query parameter (?shelter=shelter-b or ?shelter_id=shelter-b)
    const urlParams = new URLSearchParams(window.location.search);
    const queryShelter = urlParams.get("shelter") || urlParams.get("shelter_id") || urlParams.get("destination");
    if (queryShelter) {
      this.selectedShelterId = queryShelter;
    }

    // Load available shelters
    try {
      const shelterData = await getShelters();
      if (Array.isArray(shelterData) && shelterData.length > 0) {
        this.shelters = shelterData;
        // Verify selected shelter exists, else default to first available open shelter
        const exists = this.shelters.some(s => s.id === this.selectedShelterId);
        if (!exists) {
          const firstOpen = this.shelters.find(s => s.status === "OPEN") || this.shelters[0];
          this.selectedShelterId = firstOpen.id;
        }
      }
    } catch (err) {
      console.warn("[SafeRoute] Could not load shelters list:", err);
    }

    // Render page layout
    this.renderLayout(container);

    // Initialize Leaflet map
    this.initMap();

    // Setup event listeners
    this.setupListeners();

    // Fetch and render initial route
    await this.fetchRoute();
  }

  renderLayout(container) {
    container.innerHTML = `
      <div class="route-nav-header">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <h1 class="route-nav-title">🛡️ Safe Evacuation Route</h1>
          <span class="route-sim-badge">⚡ SIMULATED ROUTE</span>
        </div>
        <p style="font-size:13px;color:var(--text-secondary);margin-top:2px;">
          Dynamic routing avoiding submerged bridges, high-risk flood zones, and blocked corridors.
        </p>
      </div>

      <!-- Route Settings Card -->
      <div class="glass-card route-controls-card">
        <div class="route-control-row">
          <label class="route-control-label" for="shelter-select">📍 Destination Shelter</label>
          <select id="shelter-select" class="route-select" aria-label="Select Destination Shelter">
            ${this.shelters.map(s => `
              <option value="${s.id}" ${s.id === this.selectedShelterId ? 'selected' : ''}>
                ${s.name} (${s.status} — ${s.occupancy}/${s.capacity})
              </option>
            `).join('')}
          </select>
        </div>

        <div class="route-control-row">
          <label class="route-control-label">🚶 Travel Mode</label>
          <div class="route-mode-group" role="group" aria-label="Travel mode selection">
            <button id="btn-mode-vehicle" class="route-mode-btn ${this.travelMode === 'vehicle' ? 'route-mode-btn--active' : ''}" type="button">
              🚗 Vehicle
            </button>
            <button id="btn-mode-pedestrian" class="route-mode-btn ${this.travelMode === 'pedestrian' ? 'route-mode-btn--active' : ''}" type="button">
              🚶 Walking
            </button>
          </div>
        </div>

        <div style="font-size:11px;color:var(--text-muted);display:flex;align-items:center;gap:6px;margin-top:2px;">
          <span>📍 Origin:</span>
          <strong style="color:var(--text-primary);">${this.origin.name}</strong>
        </div>
      </div>

      <!-- Leaflet Map Container -->
      <div id="route-map" class="route-map-container" role="application" aria-label="Safe evacuation route map"></div>

      <!-- Dynamic Route Results / Feedback Container -->
      <div id="route-results-container" aria-live="polite">
        <div class="loading-state">🔄 Calculating safe evacuation route…</div>
      </div>
    `;
  }

  initMap() {
    const mapEl = document.getElementById("route-map");
    if (!mapEl || typeof L === "undefined") return;

    this.map = L.map("route-map", {
      center: [this.origin.lat, this.origin.lng],
      zoom: 13,
      zoomControl: false,
    });

    // Dark Tile Layer (CartoDB Dark Matter)
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: "&copy; <a href='https://carto.com/'>CARTO</a> &copy; OpenStreetMap",
      maxZoom: 19,
      subdomains: "abcd",
    }).addTo(this.map);

    L.control.zoom({ position: "bottomright" }).addTo(this.map);

    this.markersLayer = L.layerGroup().addTo(this.map);
  }

  setupListeners() {
    // Shelter Dropdown change
    const select = document.getElementById("shelter-select");
    if (select) {
      select.addEventListener("change", (e) => {
        this.selectedShelterId = e.target.value;
        // Update URL query param without reload
        const url = new URL(window.location);
        url.searchParams.set("shelter", this.selectedShelterId);
        window.history.replaceState({}, "", url);
        this.fetchRoute();
      });
    }

    // Vehicle mode switch
    const btnVehicle = document.getElementById("btn-mode-vehicle");
    const btnPedestrian = document.getElementById("btn-mode-pedestrian");

    if (btnVehicle && btnPedestrian) {
      btnVehicle.addEventListener("click", () => {
        if (this.travelMode === "vehicle") return;
        this.travelMode = "vehicle";
        btnVehicle.classList.add("route-mode-btn--active");
        btnPedestrian.classList.remove("route-mode-btn--active");
        this.fetchRoute();
      });

      btnPedestrian.addEventListener("click", () => {
        if (this.travelMode === "pedestrian") return;
        this.travelMode = "pedestrian";
        btnPedestrian.classList.add("route-mode-btn--active");
        btnVehicle.classList.remove("route-mode-btn--active");
        this.fetchRoute();
      });
    }
  }

  async fetchRoute() {
    const resultsContainer = document.getElementById("route-results-container");
    if (resultsContainer) {
      resultsContainer.innerHTML = `
        <div class="loading-state">
          🔄 Calculating safest route to shelter via <strong>${this.travelMode}</strong> mode…
        </div>
      `;
    }

    // Remove any previous route layer from map while calculating
    if (this.map && this.routeLayer) {
      this.map.removeLayer(this.routeLayer);
      this.routeLayer = null;
    }

    const payload = {
      origin_lat: this.origin.lat,
      origin_lng: this.origin.lng,
      shelter_id: this.selectedShelterId,
      destination_id: this.selectedShelterId,
      travel_mode: this.travelMode,
    };

    const res = await getSafeRoute(payload);

    // 1. Error state / No-Route state
    if (!res || res.ok === false) {
      const isNoRoute = res?.status === 404 && res?.error?.toLowerCase().includes("no safe route");
      this.renderErrorState(resultsContainer, res?.error, isNoRoute);
      return;
    }

    // 2. Successful route state
    this.renderSuccessState(resultsContainer, res);
    this.renderMapRoute(res);
  }

  renderSuccessState(container, data) {
    if (!container) return;

    const statusColor = data.status_color || (data.status === "SIMULATED_SAFE" ? "#10b981" : "#f59e0b");
    const shelter = this.shelters.find(s => s.id === this.selectedShelterId) || data.shelter || data.destination_shelter || {};
    const duration = data.estimated_minutes || data.duration_minutes || 12;
    const distance = data.distance_km || 2.4;
    const riskScore = data.risk_score || 18;
    const avoidedHazards = data.avoided_hazards || [];
    const warnings = data.warnings || [];

    container.innerHTML = `
      <div class="glass-card" style="border-left: 4px solid ${statusColor};">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:8px;">
          <div>
            <div style="font-size:16px;font-weight:700;color:var(--text-primary);">
              ${data.route_name || "Safe Evacuation Route"}
            </div>
            <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">
              Destination: <strong style="color:var(--text-secondary);">${shelter.name || "Relief Shelter"}</strong>
            </div>
          </div>
          <span class="badge" style="color:${statusColor};border-color:${statusColor};background:${statusColor}18;font-size:11px;font-weight:700;padding:3px 8px;border-radius:var(--radius-pill);">
            ${data.risk_level || "SIMULATED SAFE"}
          </span>
        </div>

        <!-- Route Stats Grid -->
        <div class="route-stats-grid">
          <div class="route-stat-box">
            <div class="route-stat-val">${distance} km</div>
            <div class="route-stat-lbl">Distance</div>
          </div>
          <div class="route-stat-box">
            <div class="route-stat-val">~${duration} min</div>
            <div class="route-stat-lbl">${this.travelMode === 'pedestrian' ? 'Walking Time' : 'Drive Time'}</div>
          </div>
          <div class="route-stat-box">
            <div class="route-stat-val" style="color:${statusColor};">${riskScore}/100</div>
            <div class="route-stat-lbl">Risk Index</div>
          </div>
        </div>

        <!-- Avoided Hazards -->
        ${avoidedHazards.length > 0 ? `
          <div style="margin-top:12px;">
            <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:var(--risk-moderate);margin-bottom:4px;">
              ⚠️ Hazards Avoided By Router
            </div>
            <div class="route-hazards-list">
              ${avoidedHazards.map(h => `
                <div class="route-hazard-badge">
                  🚧 Avoided: ${h}
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- Warnings & Advisories -->
        ${warnings.length > 0 ? `
          <div style="margin-top:10px;font-size:12px;line-height:1.5;color:var(--text-secondary);">
            ${warnings.map(w => `<div>• ${w}</div>`).join('')}
          </div>
        ` : ''}

        <!-- Safety Disclaimer -->
        <div class="route-advisory">
          ⚠️ <strong>Safety Disclaimer:</strong> Routes are calculated using AI simulation models and are <em>never guaranteed safe</em>. Road conditions evolve rapidly during flood emergencies. Do not attempt to evacuate without official government directive.
        </div>
      </div>
    `;
  }

  renderErrorState(container, errorMessage, isNoRoute = false) {
    if (!container) return;

    if (isNoRoute) {
      container.innerHTML = `
        <div class="alert alert--danger" style="text-align:left;">
          <div style="font-weight:700;font-size:14px;margin-bottom:4px;">⛔ No Safe Route Available</div>
          <p style="font-size:12px;margin-bottom:8px;">
            ${errorMessage || 'All connecting routes to this shelter are currently impassable due to severe flood hazards, submerged roads, or emergency closures.'}
          </p>
          <div style="font-size:11px;color:var(--text-primary);background:rgba(0,0,0,0.3);padding:8px;border-radius:6px;">
            <strong>Immediate Guidance:</strong> Do not attempt to cross flooded roads. Move to the highest accessible floor and contact emergency services, or select a different shelter from the menu above.
          </div>
        </div>
      `;
    } else {
      container.innerHTML = `
        <div class="alert alert--danger">
          <div style="font-weight:700;font-size:14px;margin-bottom:4px;">⚠️ Route Calculation Error</div>
          <p style="font-size:12px;margin-bottom:8px;">${errorMessage || 'Failed to compute route from server.'}</p>
          <button id="btn-retry-route" class="btn btn--cyan" style="padding:6px 14px;font-size:12px;" type="button">
            🔄 Retry Calculation
          </button>
        </div>
      `;

      const retryBtn = document.getElementById("btn-retry-route");
      if (retryBtn) {
        retryBtn.addEventListener("click", () => this.fetchRoute());
      }
    }
  }

  renderMapRoute(data) {
    if (!this.map || typeof L === "undefined") return;

    // Clear previous markers & route layer
    this.markersLayer.clearLayers();
    if (this.routeLayer) {
      this.map.removeLayer(this.routeLayer);
      this.routeLayer = null;
    }

    // 1. Add Origin Marker
    const originIcon = L.divIcon({
      className: "climate-map-icon",
      html: `<div style="background:#06b6d4;color:#000;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-size:15px;box-shadow:0 0 14px #06b6d4;font-weight:bold;" title="Origin">📍</div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });
    L.marker([this.origin.lat, this.origin.lng], { icon: originIcon })
      .bindPopup(`<b>Your Origin</b><br>${this.origin.name}`)
      .addTo(this.markersLayer);

    // 2. Add Destination Shelter Marker
    const shelter = this.shelters.find(s => s.id === this.selectedShelterId) || data.shelter || data.destination_shelter;
    if (shelter && shelter.lat && shelter.lng) {
      const shelterIcon = L.divIcon({
        className: "climate-map-icon",
        html: `<div style="background:#10b981;color:#000;border-radius:50%;width:34px;height:34px;display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 0 16px #10b981;" title="${shelter.name}">🏥</div>`,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
      });
      L.marker([shelter.lat, shelter.lng], { icon: shelterIcon })
        .bindPopup(`<b>${shelter.name}</b><br>Status: ${shelter.status}<br>Capacity: ${shelter.occupancy || 0}/${shelter.capacity || 0}`)
        .addTo(this.markersLayer);
    }

    // 3. Add Submerged Bridge Hazard Marker for context
    const hazardIcon = L.divIcon({
      className: "climate-map-icon",
      html: `<div style="background:#ef4444;color:#fff;border-radius:50%;width:28px;height:28px;display:flex;align-items:center;justify-content:center;font-size:13px;box-shadow:0 0 12px #ef4444;" title="Flooded Hazard">🚧</div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 14],
    });
    L.marker([18.5230, 73.8520], { icon: hazardIcon })
      .bindPopup(`<b>Riverside Drive Bridge</b><br><span style="color:#ef4444;">Flooded under 1.4m water (Submerged)</span><br>Avoided by safe routing engine.`)
      .addTo(this.markersLayer);

    // 4. Render GeoJSON LineString Route
    const geojson = data.geometry ? data : { type: "Feature", geometry: data.geometry, properties: data };
    const routeColor = data.status_color || (data.status === "SIMULATED_SAFE" ? "#10b981" : "#f59e0b");

    this.routeLayer = L.geoJSON(geojson, {
      style: () => ({
        color: routeColor,
        weight: 6,
        opacity: 0.9,
        lineCap: "round",
        lineJoin: "round",
        dashArray: this.travelMode === "pedestrian" ? "6, 8" : undefined,
      }),
    }).addTo(this.map);

    // Auto-fit bounds to the calculated route
    if (this.routeLayer.getBounds && this.routeLayer.getBounds().isValid()) {
      this.map.fitBounds(this.routeLayer.getBounds(), { padding: [35, 35] });
    }
  }
}

// Instantiate on DOM load
document.addEventListener("DOMContentLoaded", () => {
  window.safeRouteController = new SafeRouteController();
  window.safeRouteController.init();
});
