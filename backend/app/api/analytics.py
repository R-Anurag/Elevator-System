"""
app/api/analytics.py
Analytics endpoints for querying historical data from database.
"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.db.models import ElevatorHistoryORM, MaintenanceLogORM, RequestORM

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics")


@router.get("/requests/history", summary="Request history")
async def get_request_history(
    limit: int = 100, db: AsyncSession = Depends(get_db)
) -> dict:
    """Get recent request history."""
    result = await db.execute(
        select(RequestORM).order_by(RequestORM.created_at.desc()).limit(limit)
    )
    requests = result.scalars().all()
    
    return {
        "total": len(requests),
        "requests": [
            {
                "id": r.id,
                "source_floor": r.source_floor,
                "target_floor": r.target_floor,
                "direction": r.direction,
                "type": r.request_type,
                "status": r.status,
                "assigned_elevator_id": r.assigned_elevator_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in requests
        ],
    }


@router.get("/requests/stats", summary="Request statistics")
async def get_request_stats(db: AsyncSession = Depends(get_db)) -> dict:
    """Get aggregate request statistics."""
    total_result = await db.execute(select(func.count(RequestORM.id)))
    total = total_result.scalar()
    
    completed_result = await db.execute(
        select(func.count(RequestORM.id)).where(RequestORM.status == "COMPLETED")
    )
    completed = completed_result.scalar()
    
    pending_result = await db.execute(
        select(func.count(RequestORM.id)).where(RequestORM.status == "PENDING")
    )
    pending = pending_result.scalar()
    
    return {
        "total_requests": total,
        "completed": completed,
        "pending": pending,
        "completion_rate": round(completed / max(total, 1) * 100, 2),
    }


@router.get("/elevators/{elevator_id}/history", summary="Elevator movement history")
async def get_elevator_history(
    elevator_id: int, limit: int = 100, db: AsyncSession = Depends(get_db)
) -> dict:
    """Get movement history for a specific elevator."""
    result = await db.execute(
        select(ElevatorHistoryORM)
        .where(ElevatorHistoryORM.elevator_id == elevator_id)
        .order_by(ElevatorHistoryORM.timestamp.desc())
        .limit(limit)
    )
    history = result.scalars().all()
    
    return {
        "elevator_id": elevator_id,
        "total_visits": len(history),
        "history": [
            {
                "floor": h.floor,
                "status": h.status,
                "direction": h.direction,
                "timestamp": h.timestamp.isoformat() if h.timestamp else None,
            }
            for h in history
        ],
    }


@router.get("/elevators/{elevator_id}/maintenance", summary="Maintenance logs")
async def get_maintenance_logs(
    elevator_id: int, db: AsyncSession = Depends(get_db)
) -> dict:
    """Get maintenance history for an elevator."""
    result = await db.execute(
        select(MaintenanceLogORM)
        .where(MaintenanceLogORM.elevator_id == elevator_id)
        .order_by(MaintenanceLogORM.start_time.desc())
    )
    logs = result.scalars().all()
    
    return {
        "elevator_id": elevator_id,
        "total_maintenance_events": len(logs),
        "logs": [
            {
                "id": log.id,
                "description": log.description,
                "is_active": log.is_active,
                "start_time": log.start_time.isoformat() if log.start_time else None,
                "end_time": log.end_time.isoformat() if log.end_time else None,
                "duration_minutes": (
                    round((log.end_time - log.start_time).total_seconds() / 60, 2)
                    if log.end_time and log.start_time
                    else None
                ),
            }
            for log in logs
        ],
    }
