"""
app/api/rest.py
REST API router for the elevator system.

All endpoints return JSON.  Request/response shapes are validated by Pydantic.
Functional parameters (floors, elevator count) come from config.yaml — not
hard-coded here.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.config import get_settings
from app.domain.models import Direction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
_settings = get_settings()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ExternalRequestBody(BaseModel):
    """POST /api/request — press a call button on a floor."""
    floor: int
    direction: str  # "UP" | "DOWN"

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        v = v.upper()
        if v not in ("UP", "DOWN"):
            raise ValueError("direction must be UP or DOWN")
        return v

    @field_validator("floor")
    @classmethod
    def validate_floor(cls, v: int) -> int:
        max_f = _settings.building.floors
        if not (1 <= v <= max_f):
            raise ValueError(f"floor must be between 1 and {max_f}")
        return v


class InternalRequestBody(BaseModel):
    """POST /api/elevators/{id}/select-floor — press a button inside the cab."""
    floor: int

    @field_validator("floor")
    @classmethod
    def validate_floor(cls, v: int) -> int:
        max_f = _settings.building.floors
        if not (1 <= v <= max_f):
            raise ValueError(f"floor must be between 1 and {max_f}")
        return v


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/request", summary="External floor request")
async def external_request(body: ExternalRequestBody) -> dict:
    """
    Called when someone presses UP or DOWN on a floor panel.

    Example:
    ```
    POST /api/request
    { "floor": 3, "direction": "UP" }
    ```
    """
    from app.main import controller
    try:
        req = await controller.handle_external_request(
            floor=body.floor,
            direction=Direction(body.direction),
        )
        return {
            "request_id": req.id,
            "status": req.status.value,
            "assigned_elevator": req.assigned_elevator_id,
            "message": f"Elevator dispatched to floor {body.floor}",
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/elevators/{elevator_id}/select-floor", summary="Internal cabin request")
async def internal_request(elevator_id: int, body: InternalRequestBody) -> dict:
    """
    Called when a passenger presses a floor button inside the elevator cab.

    Example:
    ```
    POST /api/elevators/1/select-floor
    { "floor": 7 }
    ```
    """
    from app.main import controller
    try:
        req = await controller.handle_internal_request(
            elevator_id=elevator_id,
            target_floor=body.floor,
        )
        return {
            "request_id": req.id,
            "elevator_id": elevator_id,
            "target_floor": body.floor,
            "status": req.status.value,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/status", summary="Full system snapshot")
async def get_status() -> dict:
    """
    Returns the complete state of all elevators, pending requests,
    and system-wide statistics.
    """
    from app.main import controller
    return controller.get_status()


@router.get("/elevators/{elevator_id}", summary="Single elevator detail")
async def get_elevator(elevator_id: int) -> dict:
    """Return the current state of a single elevator."""
    from app.main import controller
    elevator = controller.elevators.get(elevator_id)
    if not elevator:
        raise HTTPException(status_code=404, detail=f"Elevator {elevator_id} not found")
    return elevator.to_dict()


@router.post("/emergency", summary="Trigger fire/emergency mode")
async def trigger_emergency() -> dict:
    """Send all available elevators to the emergency floor (config: modes.emergency_floor)."""
    from app.main import controller
    await controller.trigger_emergency()
    return {"message": "Emergency mode activated", "floor": _settings.modes.emergency_floor}


@router.post("/emergency/clear", summary="Clear emergency mode")
async def clear_emergency() -> dict:
    """Restore elevators from emergency mode."""
    from app.main import controller
    await controller.clear_emergency()
    return {"message": "Emergency cleared"}


@router.post("/elevators/{elevator_id}/maintenance", summary="Toggle maintenance mode")
async def set_maintenance(elevator_id: int, active: bool = True) -> dict:
    """Put an elevator into (active=true) or out of (active=false) maintenance."""
    from app.main import controller
    try:
        await controller.set_maintenance(elevator_id, active)
        state = "MAINTENANCE" if active else "ACTIVE"
        return {"elevator_id": elevator_id, "state": state}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/config", summary="Current config snapshot")
async def get_config() -> dict:
    """Return the effective configuration for the frontend."""
    s = _settings
    return {
        "building": s.building.model_dump(),
        "simulation": s.simulation.model_dump(),
        "elevators": [e.model_dump() for e in s.elevators],
        "modes": s.modes.model_dump(),
    }


@router.post("/simulation/restart", summary="Restart simulation")
async def restart_simulation() -> dict:
    """Restart the simulation, resetting time to 0."""
    from app.main import simulator
    import asyncio
    try:
        await asyncio.sleep(0.1)
        await simulator._async_restart()
        await asyncio.sleep(0.1)
        return {"message": "Simulation restarted", "elapsed_seconds": 0}
    except Exception as e:
        logger.error(f"Restart failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
