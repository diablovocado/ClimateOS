"""
ClimateOS — FastAPI Backend Entry Point
Run with: uvicorn services.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.routers import risk, reports, shelters, recommendations, simulation, routing

app = FastAPI(
    title="ClimateOS API",
    description="AI-Powered Climate Disaster Intelligence & Response Platform — Skeleton API (MVP: Urban Flooding)",
    version="0.1.0-skeleton",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow frontend (file:// or localhost) during development
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(risk.router,            prefix="/api",  tags=["Risk Zones"])
app.include_router(reports.router,         prefix="/api",  tags=["Citizen Reports"])
app.include_router(shelters.router,        prefix="/api",  tags=["Shelters"])
app.include_router(recommendations.router, prefix="/api",  tags=["Recommendations"])
app.include_router(simulation.router,      prefix="/api",  tags=["Simulation"])
app.include_router(routing.router,         prefix="/api",  tags=["Safe Routing"])


# ---------------------------------------------------------------------------
# Health check / root
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "platform": "ClimateOS — Disaster Intelligence & Response Platform",
        "version": "0.1.0-skeleton",
        "docs": "/docs",
    }
