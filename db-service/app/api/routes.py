from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.database import ElevatorORM, RequestORM, ElevatorHistoryORM, MaintenanceLogORM
from app.models.schemas import ElevatorSchema, RequestSchema, HistorySchema, MaintenanceSchema

router = APIRouter()


# Elevator endpoints
@router.post("/elevators")
async def upsert_elevator(elevator: ElevatorSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ElevatorORM).where(ElevatorORM.id == elevator.id))
    orm = result.scalar_one_or_none()
    
    if orm:
        orm.current_floor = elevator.current_floor
        orm.status = elevator.status
        orm.direction = elevator.direction
    else:
        orm = ElevatorORM(**elevator.model_dump())
        db.add(orm)
    
    await db.commit()
    return {"status": "success"}


@router.get("/elevators", response_model=List[ElevatorSchema])
async def get_elevators(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ElevatorORM))
    elevators = result.scalars().all()
    return [ElevatorSchema.model_validate(e.__dict__) for e in elevators]


# Request endpoints
@router.post("/requests")
async def create_request(request: RequestSchema, db: AsyncSession = Depends(get_db)):
    orm = RequestORM(**request.model_dump())
    db.add(orm)
    await db.commit()
    return {"status": "success"}


@router.put("/requests/{request_id}")
async def update_request(request_id: str, request: RequestSchema, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RequestORM).where(RequestORM.id == request_id))
    orm = result.scalar_one_or_none()
    
    if not orm:
        raise HTTPException(status_code=404, detail="Request not found")
    
    orm.status = request.status
    orm.assigned_elevator_id = request.assigned_elevator_id
    orm.completed_at = request.completed_at
    await db.commit()
    return {"status": "success"}


@router.delete("/requests/pending")
async def clear_pending_requests(db: AsyncSession = Depends(get_db)):
    """Cancel all pending/assigned requests."""
    result = await db.execute(select(RequestORM).where(RequestORM.status.in_(["PENDING", "ASSIGNED"])))
    requests = result.scalars().all()
    for req in requests:
        req.status = "CANCELLED"
    await db.commit()
    return {"status": "success", "cancelled": len(requests)}


@router.get("/requests/pending", response_model=List[RequestSchema])
async def get_pending_requests(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RequestORM).where(RequestORM.status.in_(["PENDING", "ASSIGNED"])))
    requests = result.scalars().all()
    return [RequestSchema.model_validate(r.__dict__) for r in requests]


# History endpoints
@router.post("/history")
async def log_history(history: HistorySchema, db: AsyncSession = Depends(get_db)):
    orm = ElevatorHistoryORM(**history.model_dump())
    db.add(orm)
    await db.commit()
    return {"status": "success"}


@router.get("/history/{elevator_id}", response_model=List[HistorySchema])
async def get_history(elevator_id: int, limit: int = 100, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ElevatorHistoryORM)
        .where(ElevatorHistoryORM.elevator_id == elevator_id)
        .order_by(ElevatorHistoryORM.timestamp.desc())
        .limit(limit)
    )
    history = result.scalars().all()
    return [HistorySchema.model_validate(h.__dict__) for h in history]


# Maintenance endpoints
@router.post("/maintenance/start")
async def start_maintenance(elevator_id: int, description: str = "", db: AsyncSession = Depends(get_db)):
    orm = MaintenanceLogORM(
        elevator_id=elevator_id,
        description=description,
        is_active=True,
        start_time=datetime.utcnow()
    )
    db.add(orm)
    await db.commit()
    return {"status": "success"}


@router.post("/maintenance/end/{elevator_id}")
async def end_maintenance(elevator_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MaintenanceLogORM)
        .where(MaintenanceLogORM.elevator_id == elevator_id, MaintenanceLogORM.is_active == True)
        .order_by(MaintenanceLogORM.start_time.desc())
    )
    orm = result.scalar_one_or_none()
    
    if orm:
        orm.is_active = False
        orm.end_time = datetime.utcnow()
        await db.commit()
    
    return {"status": "success"}
