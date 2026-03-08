from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ElevatorSchema(BaseModel):
    id: int
    name: str
    current_floor: int
    status: str
    direction: str
    capacity: int
    color: str


class RequestSchema(BaseModel):
    id: str
    source_floor: int
    target_floor: Optional[int]
    direction: str
    request_type: str
    assigned_elevator_id: Optional[int]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]


class HistorySchema(BaseModel):
    elevator_id: int
    floor: int
    status: str
    direction: str
    timestamp: datetime


class MaintenanceSchema(BaseModel):
    elevator_id: int
    description: str
    is_active: bool
    start_time: datetime
    end_time: Optional[datetime]
