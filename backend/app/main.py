"""
app/main.py
FastAPI application entry point.

Startup sequence:
  1. Load config.yaml → Settings
  2. Create DB tables
  3. Seed elevator rows from config.yaml
  4. Start simulation tick loop
  5. Register REST + WebSocket routers
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.services.controller import ElevatorController
from app.services.simulator import SimulationService
from app.services.passenger_sim import PassengerSimulationService
from app.api import websocket as ws_module
from app.api.rest import router as rest_router
from app.api.analytics import router as analytics_router
from app.api.websocket import router as ws_router, manager as ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
)

settings = get_settings()

# ---------------------------------------------------------------------------
# Global singletons (imported by API modules via `from app.main import ...`)
# ---------------------------------------------------------------------------

controller = ElevatorController()
passenger_sim = PassengerSimulationService(controller=controller)
controller.passenger_sim = passenger_sim  # back-link for get_status()
simulator = SimulationService(
    controller=controller,
    broadcast=ws_manager.broadcast,
    passenger_sim=passenger_sim,
)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Elevator Control System",
    description="Production-grade multi-elevator control system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router)
app.include_router(analytics_router)
app.include_router(ws_router)


@app.on_event("startup")
async def startup() -> None:
    await init_db()
    
    # Restore state from database first
    await controller.load_state()
    
    # Only seed elevators that don't exist in DB
    from app.database import AsyncSessionLocal
    from app.db.repositories import ElevatorRepository
    async with AsyncSessionLocal() as session:
        existing = await ElevatorRepository.load_all(session)
        existing_ids = {e.id for e in existing}
        for elev in controller.elevators.values():
            if elev.id not in existing_ids:
                await ElevatorRepository.upsert(session, elev)
    
    simulator.start()
    passenger_sim.start()
    logging.getLogger(__name__).info(
        "Elevator Control System started — %s floors, %s elevators",
        settings.building.floors,
        len(settings.elevators),
    )


@app.on_event("shutdown")
async def shutdown() -> None:
    simulator.stop()
    passenger_sim.stop()


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "service": "Elevator Control System",
        "status": "running",
        "docs": "/docs",
    }
