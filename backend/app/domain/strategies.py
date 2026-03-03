"""
app/domain/strategies.py
Pluggable scheduling strategies — Strategy Pattern implementation.

To add a new strategy:
  1. Subclass SchedulerStrategy and implement assign()
  2. Register it in STRATEGY_REGISTRY at the bottom of this file
  3. Set scheduler_strategy in config.yaml

SOLID compliance:
  - SRP: each class has one job
  - OCP: new strategies require no modification to existing code
  - LSP: all strategies are interchangeable
  - ISP: thin interface — just one method
  - DIP: controller depends on the ABC, not concrete classes
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.models import Direction, Elevator, ElevatorRequest, ElevatorStatus


class SchedulerStrategy(ABC):
    """Abstract base class all scheduling strategies must implement."""

    @abstractmethod
    def assign(
        self, request: ElevatorRequest, elevators: List[Elevator]
    ) -> Optional[Elevator]:
        """
        Select the best elevator for the given request.
        Returns None if no elevator is available.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...


# ---------------------------------------------------------------------------
# Strategy 1 — Nearest Elevator
# Picks the elevator with the smallest floor distance.
# Best for: small buildings, low traffic.
# Trade-off: ignores direction — may cause unnecessary direction reversals.
# ---------------------------------------------------------------------------

class NearestElevatorStrategy(SchedulerStrategy):
    """Assigns the geographically closest available elevator."""

    name = "nearest"

    def assign(
        self, request: ElevatorRequest, elevators: List[Elevator]
    ) -> Optional[Elevator]:
        candidates = [
            e for e in elevators 
            if e.is_available() 
            and not (e.current_floor == request.source_floor and e.status == ElevatorStatus.DOORS_OPEN)
        ]
        if not candidates:
            return None

        return min(
            candidates,
            key=lambda e: abs(e.current_floor - request.source_floor),
        )


# ---------------------------------------------------------------------------
# Strategy 2 — Direction-Based
# Prefer an elevator already heading toward the request floor in the
# correct direction.  Falls back to nearest if no directional match.
# Best for: medium-to-large buildings, busy hours.
# Trade-off: slightly more complex assignment logic.
# ---------------------------------------------------------------------------

class DirectionBasedStrategy(SchedulerStrategy):
    """Prefers elevators already moving in the correct direction."""

    name = "direction_based"

    def assign(
        self, request: ElevatorRequest, elevators: List[Elevator]
    ) -> Optional[Elevator]:
        candidates = [
            e for e in elevators 
            if e.is_available() 
            and not (e.current_floor == request.source_floor and e.status == ElevatorStatus.DOORS_OPEN)
        ]
        if not candidates:
            return None

        # Separate by state: idle vs moving
        idle = [e for e in candidates if e.is_idle()]
        moving = [e for e in candidates if not e.is_idle()]
        
        # First priority: elevators moving in same direction AND approaching
        approaching = []
        for elev in moving:
            if not elev.floor_queue:
                continue
            
            next_stop = elev.floor_queue[0]
            
            # Check if elevator is approaching request floor in correct direction
            if request.direction == Direction.UP:
                # Request wants UP: elevator must be below and moving up toward request floor
                if (elev.direction == Direction.UP and 
                    elev.current_floor <= request.source_floor and 
                    next_stop >= request.source_floor):
                    approaching.append(elev)
            else:  # Direction.DOWN
                # Request wants DOWN: elevator must be above and moving down toward request floor
                if (elev.direction == Direction.DOWN and 
                    elev.current_floor >= request.source_floor and 
                    next_stop <= request.source_floor):
                    approaching.append(elev)
        
        if approaching:
            return min(approaching, key=lambda e: abs(e.current_floor - request.source_floor))
        
        # Second priority: idle elevators (nearest)
        if idle:
            return min(idle, key=lambda e: abs(e.current_floor - request.source_floor))
        
        # Last resort: any moving elevator (nearest)
        return min(moving, key=lambda e: abs(e.current_floor - request.source_floor))


# ---------------------------------------------------------------------------
# Strategy 3 — Idle Preference
# Always picks idle elevator first; among idle ones, nearest wins.
# Best for: low-traffic scenarios where fairness matters.
# Trade-off: ignores direction entirely.
# ---------------------------------------------------------------------------

class IdlePreferenceStrategy(SchedulerStrategy):
    """Strongly prefers idle elevators over busy ones."""

    name = "idle_preference"

    def assign(
        self, request: ElevatorRequest, elevators: List[Elevator]
    ) -> Optional[Elevator]:
        candidates = [
            e for e in elevators 
            if e.is_available() 
            and not (e.current_floor == request.source_floor and e.status == ElevatorStatus.DOORS_OPEN)
        ]
        if not candidates:
            return None

        idle = [e for e in candidates if e.is_idle()]
        pool = idle if idle else candidates

        return min(pool, key=lambda e: abs(e.current_floor - request.source_floor))


# ---------------------------------------------------------------------------
# Registry — maps config.yaml strategy string → class instance
# ---------------------------------------------------------------------------

STRATEGY_REGISTRY: dict[str, SchedulerStrategy] = {
    NearestElevatorStrategy.name: NearestElevatorStrategy(),
    DirectionBasedStrategy.name: DirectionBasedStrategy(),
    IdlePreferenceStrategy.name: IdlePreferenceStrategy(),
}


def get_strategy(name: str) -> SchedulerStrategy:
    """Return the strategy instance for the given name from config.yaml."""
    if name not in STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown scheduler strategy '{name}'. "
            f"Valid options: {list(STRATEGY_REGISTRY.keys())}"
        )
    return STRATEGY_REGISTRY[name]
