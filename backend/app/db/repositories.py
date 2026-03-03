"""
app/db/repositories.py
Repository layer for database persistence.
Bridges domain models (dataclasses) with ORM models.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ElevatorHistoryORM,
    ElevatorORM,
    MaintenanceLogORM,
    RequestORM,
)
from app.domain.models import Elevator, ElevatorRequest


class ElevatorRepository:
    """Persist and retrieve elevator state."""

    @staticmethod
    async def upsert(session: AsyncSession, elevator: Elevator) -> None:
        """Create or update elevator record."""
        result = await session.execute(
            select(ElevatorORM).where(ElevatorORM.id == elevator.id)
        )
        orm = result.scalar_one_or_none()
        
        if orm:
            orm.current_floor = elevator.current_floor
            orm.status = elevator.status.value
            orm.direction = elevator.direction.value
        else:
            orm = ElevatorORM(
                id=elevator.id,
                name=elevator.name,
                current_floor=elevator.current_floor,
                status=elevator.status.value,
                direction=elevator.direction.value,
                capacity=elevator.capacity,
                color=elevator.color,
            )
            session.add(orm)
        await session.commit()

    @staticmethod
    async def load_all(session: AsyncSession) -> List[ElevatorORM]:
        """Load all elevator records."""
        result = await session.execute(select(ElevatorORM))
        return list(result.scalars().all())


class RequestRepository:
    """Persist and retrieve elevator requests."""

    @staticmethod
    async def save(session: AsyncSession, request: ElevatorRequest) -> None:
        """Save a new request."""
        orm = RequestORM(
            id=request.id,
            source_floor=request.source_floor,
            target_floor=request.target_floor,
            direction=request.direction.value,
            request_type=request.request_type.value,
            assigned_elevator_id=request.assigned_elevator_id,
            status=request.status.value,
            created_at=request.created_at,
            completed_at=request.completed_at,
        )
        session.add(orm)
        await session.commit()

    @staticmethod
    async def update(session: AsyncSession, request: ElevatorRequest) -> None:
        """Update existing request."""
        result = await session.execute(
            select(RequestORM).where(RequestORM.id == request.id)
        )
        orm = result.scalar_one_or_none()
        if orm:
            orm.status = request.status.value
            orm.assigned_elevator_id = request.assigned_elevator_id
            orm.completed_at = request.completed_at
            await session.commit()

    @staticmethod
    async def get_pending(session: AsyncSession) -> List[RequestORM]:
        """Get all pending and assigned requests."""
        result = await session.execute(
            select(RequestORM).where(RequestORM.status.in_(["PENDING", "ASSIGNED"]))
        )
        return list(result.scalars().all())


class HistoryRepository:
    """Log elevator movement history."""

    @staticmethod
    async def log_floor_visit(
        session: AsyncSession,
        elevator_id: int,
        floor: int,
        status: str,
        direction: str,
    ) -> None:
        """Record elevator visiting a floor."""
        orm = ElevatorHistoryORM(
            elevator_id=elevator_id,
            floor=floor,
            status=status,
            direction=direction,
            timestamp=datetime.utcnow(),
        )
        session.add(orm)
        await session.commit()

    @staticmethod
    async def get_elevator_history(
        session: AsyncSession, elevator_id: int, limit: int = 100
    ) -> List[ElevatorHistoryORM]:
        """Get recent history for an elevator."""
        result = await session.execute(
            select(ElevatorHistoryORM)
            .where(ElevatorHistoryORM.elevator_id == elevator_id)
            .order_by(ElevatorHistoryORM.timestamp.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class MaintenanceRepository:
    """Track maintenance events."""

    @staticmethod
    async def start_maintenance(
        session: AsyncSession, elevator_id: int, description: str = ""
    ) -> None:
        """Log start of maintenance."""
        orm = MaintenanceLogORM(
            elevator_id=elevator_id,
            description=description,
            is_active=True,
            start_time=datetime.utcnow(),
        )
        session.add(orm)
        await session.commit()

    @staticmethod
    async def end_maintenance(session: AsyncSession, elevator_id: int) -> None:
        """Mark active maintenance as complete."""
        result = await session.execute(
            select(MaintenanceLogORM)
            .where(
                MaintenanceLogORM.elevator_id == elevator_id,
                MaintenanceLogORM.is_active == True,
            )
            .order_by(MaintenanceLogORM.start_time.desc())
        )
        orm = result.scalar_one_or_none()
        if orm:
            orm.is_active = False
            orm.end_time = datetime.utcnow()
            await session.commit()
