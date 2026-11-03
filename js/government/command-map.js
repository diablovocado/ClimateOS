/**
 * ClimateOS — Government Mode: Command Center Map Panel
 * File owner: Government Dashboard / Map team
 *
 * Full-screen command center map with all layers: risk zones, shelters, incidents.
 */

import { initMap, renderRiskZonesGeoJSON, addIncidentMarker, addShelterMarker, invalidateSize } from "../map.js";
import { getZonesRisk, getShelters, getIncidents, getIncidentsStreamUrl } from "../api.js";

let _mapInstance = null;
const _mappedIncidentIds = new Set();
let _mapEventSource = null;

export async function initCommandMap(containerId = "gov-map") {
  _mapInstance = initMap(containerId, { zoom: 13 });

  const [zones, shelters, incidents] = await Promise.all([
    getZonesRisk(),
    getShelters(),
    getIncidents(),
  ]);

  renderRiskZonesGeoJSON(zones || []);
  (shelters  || []).forEach(s => addShelterMarker(s));

  _mappedIncidentIds.clear();
  (incidents || []).forEach(inc => {
    if (inc && inc.id) {
      _mappedIncidentIds.add(String(inc.id));
      addIncidentMarker(inc);
    }
  });

  initCommandMapStream();
}

export function handleLiveMapIncident(rawIncident) {
  const inc = rawIncident.incident || rawIncident;
  if (!inc || !inc.id) return;
  const idStr = String(inc.id);
  if (_mappedIncidentIds.has(idStr)) return; // Avoid duplicate marker

  _mappedIncidentIds.add(idStr);
  addIncidentMarker(inc);
}

export function handleLiveShelterUpdate(rawShelter) {
  const s = rawShelter.shelter || rawShelter;
  if (!s || !s.lat || !s.lng) return;
  addShelterMarker(s);
}

export function initCommandMapStream() {
  if (typeof EventSource === "undefined") return;
  if (_mapEventSource) return;

  try {
    const sseUrl = getIncidentsStreamUrl();
    _mapEventSource = new EventSource(sseUrl);

    _mapEventSource.addEventListener("incident", (event) => {
      try {
        const data = JSON.parse(event.data);
        handleLiveMapIncident(data);
      } catch (e) {
        console.error("Error adding live incident to map:", e);
      }
    });

    _mapEventSource.addEventListener("shelter", (event) => {
      try {
        const data = JSON.parse(event.data);
        handleLiveShelterUpdate(data);
      } catch (e) {}
    });

    _mapEventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data && (data.id || data.incident)) {
          handleLiveMapIncident(data);
        }
      } catch (e) {}
    };

    _mapEventSource.onerror = () => {
      // Automatic reconnect by browser with Last-Event-ID
    };
  } catch (err) {
    console.warn("Could not initialize command map SSE stream:", err);
  }
}

export function refreshMapSize() {
  invalidateSize();
}

document.addEventListener("DOMContentLoaded", () => {
  initCommandMap("gov-map");
});

