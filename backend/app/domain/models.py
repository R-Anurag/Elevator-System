"""
app/domain/models.py
Pure domain models — no framework dependencies.
These are the core entities of the elevator system.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Direction(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    IDLE = "IDLE"


class ElevatorStatus(str, Enum):
    IDLE = "IDLE"
    MOVING_UP = "MOVING_UP"
    MOVING_DOWN = "MOVING_DOWN"
    DOORS_OPEN = "DOORS_OPEN"
    MAINTENANCE = "MAINTENANCE"
    EMERGENCY = "EMERGENCY"


class RequestStatus(str, Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RequestType(str, Enum):
    EXTERNAL = "EXTERNAL"   # Pressed from a floor panel (outside cab)
    INTERNAL = "INTERNAL"   # Pressed from inside the elevator cab


class PassengerGroupState(str, Enum):
    WAITING   = "WAITING"    # On the floor, waiting for an elevator
    BOARDING  = "BOARDING"   # Currently boarding the elevator
    RIDING    = "RIDING"     # Boarded — in transit inside an elevator
    DELIVERED = "DELIVERED"  # Arrived at destination — exiting animation


# ---------------------------------------------------------------------------
# Domain Entities
# ---------------------------------------------------------------------------

@dataclass
class ElevatorRequest:
    """
    Represents a single elevator request — either external (floor panel)
    or internal (cabin panel).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_floor: int = 1
    target_floor: Optional[int] = None         # None for external requests
    direction: Direction = Direction.UP
    request_type: RequestType = RequestType.EXTERNAL
    assigned_elevator_id: Optional[int] = None
    status: RequestStatus = RequestStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    @property
    def is_pending(self) -> bool:
        return self.status == RequestStatus.PENDING


@dataclass
class Elevator:
    """
    Represents physical elevator state.  All business logic about
    movement resides in the SimulationService.
    """
    id: int
    name: str
    current_floor: int
    capacity: int
    color: str = "#f59e0b"

    status: ElevatorStatus = ElevatorStatus.IDLE
    direction: Direction = Direction.IDLE

    # Ordered list of floors this elevator still needs to visit
    floor_queue: List[int] = field(default_factory=list)

    # Current number of passengers (simulated)
    passenger_count: int = 0
    
    # Stats
    floors_served: int = 0

    def is_idle(self) -> bool:
        return self.status == ElevatorStatus.IDLE

    def is_available(self) -> bool:
        """Elevator can accept new assignments."""
        return self.status not in (
            ElevatorStatus.MAINTENANCE,
            ElevatorStatus.EMERGENCY,
        )

    def has_capacity(self) -> bool:
        return self.passenger_count < self.capacity

    def enqueue_floor(self, floor: int) -> None:
        """Add a floor to the visit queue (deduplicates)."""
        if floor not in self.floor_queue:
            self.floor_queue.append(floor)

    def next_target(self) -> Optional[int]:
        """Peek at the next floor to visit."""
        return self.floor_queue[0] if self.floor_queue else None

    def get_state_snapshot(self) -> tuple:
        """Return hashable snapshot of state for change detection."""
        return (
            self.current_floor,
            self.status.value,
            self.direction.value,
            self.passenger_count,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "current_floor": self.current_floor,
            "status": self.status.value,
            "direction": self.direction.value,
            "floor_queue": self.floor_queue,
            "passenger_count": self.passenger_count,
            "capacity": self.capacity,
            "color": self.color,
            "floors_served": self.floors_served,
        }


# ---------------------------------------------------------------------------
# Passenger Group
# ---------------------------------------------------------------------------

@dataclass
class PassengerGroup:
    """
    A cohort of individual passengers sharing the same journey:
    source_floor → dest_floor.  Groups split when elevator capacity
    is insufficient — the overflow forms a new child group.
    """
    id: str
    source_floor: int
    dest_floor: int
    direction: Direction
    total_count: int                         # Immutable — original group size
    waiting_count: int                       # Still on the floor
    riding_count: int                        # Inside the elevator
    delivered_count: int                     # Reached destination
    assigned_elevator_id: Optional[int]      # Elevator transporting them
    state: PassengerGroupState = PassengerGroupState.WAITING
    spawned: bool = False                    # Has the external request fired?
    spawn_at_sec: float = 0.0               # Seconds from sim start to appear
    spawned_at: Optional[datetime] = None    # When group spawned
    boarded_at: Optional[datetime] = None    # When group boarded elevator

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_floor": self.source_floor,
            "dest_floor": self.dest_floor,
            "direction": self.direction.value,
            "total_count": self.total_count,
            "waiting_count": self.waiting_count,
            "riding_count": self.riding_count,
            "delivered_count": self.delivered_count,
            "assigned_elevator_id": self.assigned_elevator_id,
            "state": self.state.value,
            "spawned": self.spawned,
        }
