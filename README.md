# 🌍 ClimateOS — AI-Powered Climate Disaster Intelligence & Response Platform

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.1--skeleton-orange.svg)](#)
[![MVP Focus](https://img.shields.io/badge/MVP%20Focus-Urban%20Flooding-blue.svg)](#)

> **ClimateOS** is an AI-powered disaster intelligence and response platform that transforms
> fragmented climate data and citizen observations into verified, localized, and actionable
> decisions before, during, and after climate-related disasters.

---

## ⚡ Quick Start

### 1. Clone & install Python dependencies

```bash
git clone <repo-url>
cd ClimateOS
pip install -r requirements.txt
```

### 2. Run the FastAPI backend

```bash
uvicorn services.main:app --reload
```

API docs available at: **http://localhost:8000/docs**

### 3. Open the frontend

Open any HTML file directly in your browser — **no build step required**:

| Page | File | Mode |
|---|---|---|
| Landing / Citizen Home | `citizen.html` | Citizen |
| Citizen Map | `citizen-map.html` | Citizen |
| Report Incident | `citizen-report.html` | Citizen |
| Shelter List | `citizen-shelters.html` | Citizen |
| Safe Route | `citizen-route.html` | Citizen |
| Government Dashboard | `government.html` | Government |
| Original Demo | `index.html` | Combined Demo |

> **Note:** The frontend works in offline/mock mode without the backend.
> When the FastAPI server is running, it fetches live data automatically.

### 4. Run tests

```bash
pytest tests/test_api.py -v
```

---

## 📁 Folder Overview

```
ClimateOS/
├── index.html              # Original combined demo page (preserved)
├── citizen.html            # Citizen Mode home
├── citizen-map.html        # Citizen Leaflet map view
├── citizen-report.html     # Incident report form
├── citizen-shelters.html   # Shelter list
├── citizen-route.html      # Safe route (placeholder)
├── government.html         # Government command center dashboard
│
├── css/
│   ├── base.css            # CSS variables, reset, animations — EDIT TO THEME
│   ├── layout.css          # Page layouts (navbar, citizen column, gov 3-col)
│   ├── components.css      # Reusable UI components
│   └── style.css           # Original demo CSS (preserved)
│
├── js/
│   ├── api.js              # ← ALL fetch() calls live here — one source of truth
│   ├── map.js              # Shared Leaflet map helpers (ES module)
│   ├── citizen/            # One JS file per citizen page
│   │   ├── home.js
│   │   ├── map-view.js
│   │   ├── report.js
│   │   ├── shelters.js
│   │   └── safe-route.js
│   ├── government/         # One JS file per government panel
│   │   ├── command-map.js
│   │   ├── incident-feed.js
│   │   ├── recommendations.js
│   │   ├── zone-table.js
│   │   └── simulation-panel.js
│   ├── components/         # Reusable UI components
│   │   ├── navbar.js
│   │   ├── badge.js
│   │   └── card.js
│   └── [ai-engine.js, app.js, simulation.js]  # Original demo JS (preserved)
│
├── services/
│   ├── main.py             # ← FastAPI entry point (uvicorn target)
│   ├── routers/            # One router file per feature domain
│   │   ├── risk.py         # GET /api/zones/risk
│   │   ├── reports.py      # POST /api/reports, GET /api/incidents
│   │   ├── shelters.py     # GET /api/shelters
│   │   ├── recommendations.py # GET/POST /api/recommendations
│   │   └── simulation.py   # POST /api/simulation
│   └── api/                # Original API service (preserved)
│       └── main.py
│
├── data/
│   ├── zones.geojson       # 5 zones with risk data & geometry
│   ├── shelters.json       # 5 shelters with capacity/occupancy
│   ├── incidents.json      # 5 mock incidents with confidence labels
│   ├── recommendations.json # 5 AI recommendations with XAI factors
│   └── [scenarios/, seed/] # Original seed data (preserved)
│
└── tests/
    └── test_api.py         # pytest test suite for all 7 API endpoints
```

---

## 🔌 API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/zones/risk` | All zone risk data (GeoJSON-backed) |
| `GET` | `/api/zones/risk/{zone_id}` | Single zone risk |
| `GET` | `/api/shelters` | All shelters with capacity/occupancy |
| `GET` | `/api/incidents` | Ranked incidents with confidence labels |
| `POST` | `/api/reports` | Submit a citizen report → returns AI confidence score |
| `GET` | `/api/recommendations` | AI-generated recommendations |
| `POST` | `/api/recommendations/{id}/decision` | Approve or reject a recommendation |
| `POST` | `/api/simulation` | Run scenario with rainfall + water level sliders |

Interactive Swagger docs: **http://localhost:8000/docs**

---

## 👥 Who Owns What

| Feature | Work in these files |
|---|---|
| **Risk Engine** | `services/routers/risk.py`, `js/government/zone-table.js` |
| **Citizen Report Form** | `citizen-report.html`, `js/citizen/report.js`, `services/routers/reports.py` |
| **AI Verification** | `services/routers/reports.py` → `_fake_confidence_score()` |
| **Map & GIS** | `js/map.js`, `js/citizen/map-view.js`, `js/government/command-map.js` |
| **Shelter Intelligence** | `services/routers/shelters.py`, `js/citizen/shelters.js` |
| **Safe Routing** | `js/citizen/safe-route.js` (placeholder — needs new router) |
| **Recommendations** | `services/routers/recommendations.py`, `js/government/recommendations.js` |
| **Simulation** | `services/routers/simulation.py`, `js/government/simulation-panel.js` |
| **Design / CSS** | `css/base.css` (change variables to theme the whole app) |

---

## 🎨 Theming

Edit **`css/base.css`** to change the visual theme for everyone:

```css
:root {
  --risk-low:      #22c55e;  /* green  */
  --risk-moderate: #f59e0b;  /* yellow */
  --risk-high:     #f97316;  /* orange */
  --risk-severe:   #ef4444;  /* red    */
  --accent-cyan:   #06b6d4;  /* brand  */
}
```

---

## 📄 License & References

- **License:** [GNU GPL v3](LICENSE)
- **Product Requirements Document (PRD):** [`PRD.md`](PRD.md) | Original Hackathon PDF: [`ClimateOS_PRD.pdf`](ClimateOS_PRD.pdf)
- **Tech Stack:** [`ClimateOS_Technical_Stack_Document.pdf`](ClimateOS_Technical_Stack_Document.pdf)

---

> ⚠️ **Disclaimer:** ClimateOS supports decisions; authorized emergency authorities make final calls.