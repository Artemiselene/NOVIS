"""
NOVIS — Neural Onboard Vitality & Intelligence System
======================================================
Intelligent Crew Health. Adaptive Mission Readiness.
Coordinates core routers, astronaut records, missions, physiological telemetry,
PSI behavioral analytics, health intelligence dashboard, and real-time WebSockets.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import CORS_ORIGINS, API_PREFIX
from .db import Base, engine
from .routers import router as core_router
from .routers_astronauts import router as astronauts_router
from .routers_missions import router as missions_router
from .routers_telemetry import router as telemetry_router
from .routers_psi import router as psi_router
from .routers_dashboard import router as dashboard_router
from .routers_ws import router as ws_router
from .seed import seed

app = FastAPI(
    title="NOVIS — Neural Onboard Vitality & Intelligence System",
    description="NOVIS — Astronaut Behavioral Health Intelligence & Telemetry Platform",
    version="3.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
seed()

# Register core and Phase 3 feature routers
app.include_router(core_router, prefix=API_PREFIX)
app.include_router(astronauts_router, prefix=API_PREFIX)
app.include_router(missions_router, prefix=API_PREFIX)
app.include_router(telemetry_router, prefix=API_PREFIX)
app.include_router(psi_router, prefix=API_PREFIX)
app.include_router(dashboard_router, prefix=API_PREFIX)
app.include_router(ws_router, prefix=API_PREFIX)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "astra-mind-extension"}


@app.get(f"{API_PREFIX}/health")
def extension_health():
    return {"status": "ok", "extension": "health-monitoring"}
