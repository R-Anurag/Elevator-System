"""
app/services/controller.py
ElevatorController — core orchestrator.

Responsibilities:
  - Maintains the in-memory fleet of Elevator objects
  - Receives requests and delegates scheduling to the configured strategy
  - Updates elevator queues and status
  - Thread-safe through asyncio.Lock per elevator

Design: Controller reads ALL settings from config.yaml via get_settings().
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.config import get_settings
from app.db_client import get_db_client
from app.domain.models import (
    Direction,
    Elevator,
    ElevatorRequest,
    ElevatorStatus,
    RequestStatus,
    RequestType,
)
from app.domain.strategies import get_strategy, SchedulerStrategy

logger = logging.getLogger(__name__)


class ElevatorController:
    """
    Singleton-like orchestrator that owns the elevator fleet during
    the lifetime of the application.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._strategy: SchedulerStrategy = get_strategy(
            self._settings.simulation.scheduler_strategy
        )

        # Build fleet from config.yaml
        self.elevators: Dict[int, Elevator] = {}
        for ec in self._settings.elevators:
            elev = Elevator(
                id=ec.id,
                name=ec.name,
                current_floor=ec.starting_floor,
                capacity=self._settings.building.elevator_capacity,
                color=ec.color,
            )
            # Mark maintenance elevators immediately
            if ec.id in self._settings.modes.maintenance_ids:
                elev.status = ElevatorStatus.MAINTENANCE
            self.elevators[ec.id] = elev

        # Pending request queue (not yet assigned to an elevator)
        self.pending_requests: List[ElevatorRequest] = []

        # All requests (for history/status)
        self.all_requests: List[ElevatorRequest] = []

        # Per-elevator asyncio locks (prevent race conditions on floor_queue)
        self._locks: Dict[int, asyncio.Lock] = {
            eid: asyncio.Lock() for eid in self.elevators
        }

        # Stats
        self.total_wait_ms: float = 0.0
        self.requests_completed: int = 0

        # Passenger simulation (set after startup to avoid circular import)
        self.passenger_sim = None

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    async def load_state(self) -> None:
        """Restore elevator state and pending requests from database."""
        db_client = get_db_client()
        
        # Load elevator positions/status
        elevators_data = await db_client.load_all_elevators()
        for data in elevators_data:
            if data["id"] in self.elevators:
                self.elevators[data["id"]].current_floor = data["current_floor"]
                self.elevators[data["id"]].status = ElevatorStatus(data["status"])
                logger.info("Restored elevator %s: floor=%s status=%s", data["id"], data["current_floor"], data["status"])
        
        # Restore pending/assigned requests
        pending_data = await db_client.get_pending_requests()
        for req_data in pending_data:
            req = ElevatorRequest(
                id=req_data["id"],
                source_floor=req_data["source_floor"],
                target_floor=req_data["target_floor"],
                direction=Direction(req_data["direction"]),
                request_type=RequestType(req_data["request_type"]),
                status=RequestStatus.PENDING,
            )
            self.pending_requests.append(req)
            self.all_requests.append(req)
        
        if pending_data:
            logger.info("Restored %d pending requests", len(pending_data))
            await self._retry_pending()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def handle_external_request(
        self, floor: int, direction: Direction
    ) -> ElevatorRequest:
        """Process a call from a floor panel (outside the cab)."""
        self._validate_floor(floor)

        req = ElevatorRequest(
            source_floor=floor,
            direction=direction,
            request_type=RequestType.EXTERNAL,
        )
        self.all_requests.append(req)
        
        # Persist to database
        db_client = get_db_client()
        await db_client.save_request(req)
        
        await self._assign_and_enqueue(req)
        
        # Update request status in DB
        await db_client.update_request(req)
        
        return req

    async def handle_internal_request(
        self, elevator_id: int, target_floor: int
    ) -> ElevatorRequest:
        """Process a floor button press from inside an elevator cab."""
        self._validate_floor(target_floor)
        if elevator_id not in self.elevators:
            raise ValueError(f"Elevator {elevator_id} not found")

        elevator = self.elevators[elevator_id]
        
        # Prevent requesting current floor
        if target_floor == elevator.current_floor:
            raise ValueError(f"Elevator {elevator_id} is already at floor {target_floor}")
        
        req = ElevatorRequest(
            source_floor=elevator.current_floor,
            target_floor=target_floor,
            direction=(
                Direction.UP
                if target_floor > elevator.current_floor
                else Direction.DOWN
            ),
            request_type=RequestType.INTERNAL,
            assigned_elevator_id=elevator_id,
            status=RequestStatus.ASSIGNED,
        )
        self.all_requests.append(req)
        
        # Persist to database
        db_client = get_db_client()
        await db_client.save_request(req)

        async with self._locks[elevator_id]:
            elevator.enqueue_floor(target_floor)
            logger.info("Elevator %s queue before reorder (internal): %s", elevator_id, elevator.floor_queue)
            self._reorder_queue(elevator)
            logger.info("Elevator %s queue after reorder (internal): %s", elevator_id, elevator.floor_queue)

        logger.info(
            "Internal request: elevator=%s -> floor=%s", elevator_id, target_floor
        )
        return req

    async def complete_floor_visit(self, elevator_id: int) -> None:
        """Called by the simulator when an elevator arrives at its next floor."""
        elevator = self.elevators.get(elevator_id)
        if not elevator:
            return

        logger.info("Elevator %s completing floor %s, queue before pop: %s", 
                   elevator_id, elevator.current_floor, elevator.floor_queue)
        
        # Increment floors served for this elevator
        elevator.floors_served += 1
        
        async with self._locks[elevator_id]:
            if elevator.floor_queue:
                elevator.floor_queue.pop(0)
        
        logger.info("Elevator %s queue after pop: %s", elevator_id, elevator.floor_queue)

        # Log floor visit to history
        db_client = get_db_client()
        await db_client.log_floor_visit(
            elevator_id=elevator_id,
            floor=elevator.current_floor,
            status=elevator.status.value,
            direction=elevator.direction.value,
        )
        
        # Mark completed requests
        now = datetime.utcnow()
        for req in self.all_requests:
            if (
                req.assigned_elevator_id == elevator_id
                and req.status == RequestStatus.ASSIGNED
                and (
                    req.source_floor == elevator.current_floor
                    or req.target_floor == elevator.current_floor
                )
            ):
                req.status = RequestStatus.COMPLETED
                req.completed_at = now
                
                # Update in database
                await db_client.update_request(req)

        # Retry any pending requests now that this elevator may be free
        await self._retry_pending()

    async def trigger_emergency(self) -> None:
        """Send all elevators to the emergency floor (from config.yaml)."""
        emergency_floor = self._settings.modes.emergency_floor
        for elevator in self.elevators.values():
            if elevator.status != ElevatorStatus.MAINTENANCE:
                async with self._locks[elevator.id]:
                    elevator.floor_queue = [emergency_floor]
                    elevator.status = ElevatorStatus.EMERGENCY
        logger.warning("EMERGENCY triggered — all elevators going to floor %s", emergency_floor)

    async def clear_emergency(self) -> None:
        """Restore elevators from emergency state."""
        for elevator in self.elevators.values():
            if elevator.status == ElevatorStatus.EMERGENCY:
                elevator.status = ElevatorStatus.IDLE
        logger.info("Emergency cleared")

    async def set_maintenance(self, elevator_id: int, active: bool) -> None:
        """Put an elevator into or out of maintenance mode."""
        elevator = self.elevators.get(elevator_id)
        if not elevator:
            raise ValueError(f"Elevator {elevator_id} not found")
        
        db_client = get_db_client()
        
        if active:
            # Log maintenance start
            await db_client.start_maintenance(elevator_id, "Manual maintenance mode")
            
            # Entering maintenance: reassign all requests assigned to this elevator
            async with self._locks[elevator_id]:
                elevator.floor_queue.clear()
            elevator.status = ElevatorStatus.MAINTENANCE
            
            # Move assigned requests back to pending queue for reassignment
            for req in self.all_requests:
                if (
                    req.assigned_elevator_id == elevator_id
                    and req.status == RequestStatus.ASSIGNED
                ):
                    req.assigned_elevator_id = None
                    req.status = RequestStatus.PENDING
                    self.pending_requests.append(req)
                    
                    # Update in database
                    await db_client.update_request(req)
                    
                    logger.info("Request %s reassigned due to maintenance on elevator %s", req.id, elevator_id)
            
            # Try to reassign pending requests to other elevators
            await self._retry_pending()
        else:
            # Log maintenance end
            await db_client.end_maintenance(elevator_id)
            
            # Exiting maintenance
            elevator.status = ElevatorStatus.IDLE

    def get_status(self) -> dict:
        """Return a full system snapshot for the /status endpoint and WS broadcasts."""
        avg_wait = (
            self.total_wait_ms / max(self.requests_completed, 1)
        )
        passenger_groups = (
            self.passenger_sim.get_groups_snapshot()
            if self.passenger_sim is not None
            else []
        )
        
        # Collect active external requests (assigned or pending)
        active_requests = []
        for req in self.all_requests:
            if (
                req.request_type == RequestType.EXTERNAL
                and req.status in (RequestStatus.PENDING, RequestStatus.ASSIGNED)
            ):
                active_requests.append({
                    "floor": req.source_floor,
                    "direction": req.direction.value,
                })
        
        return {
            "elevators": [e.to_dict() for e in self.elevators.values()],
            "floors": self._settings.building.floors,
            "floor_height_px": self._settings.building.floor_height_px,
            "elevator_capacity": self._settings.building.elevator_capacity,
            "tick_interval_ms": self._settings.simulation.tick_interval_ms,
            "scheduler_strategy": self._strategy.name,
            "avg_wait_ms": round(avg_wait, 1),
            "vip_floors": self._settings.modes.vip_floors,
            "emergency_floor": self._settings.modes.emergency_floor,
            "pending_requests": len(self.pending_requests),
            "passenger_groups": passenger_groups,
            "active_requests": active_requests,
        }

    def reset_state(self) -> None:
        """Reset all elevators and requests to initial state."""
        # Reset elevators to starting positions
        for ec in self._settings.elevators:
            if ec.id in self.elevators:
                elev = self.elevators[ec.id]
                elev.current_floor = ec.starting_floor
                elev.status = ElevatorStatus.MAINTENANCE if ec.id in self._settings.modes.maintenance_ids else ElevatorStatus.IDLE
                elev.direction = Direction.IDLE
                elev.floor_queue = []
                elev.passenger_count = 0
                elev.floors_served = 0
        
        self.pending_requests.clear()
        self.all_requests.clear()
        self.total_wait_ms = 0.0
        self.requests_completed = 0
        logger.info("Controller state reset")

    async def reset_state_with_db(self) -> None:
        """Reset state and clear database."""
        db_client = get_db_client()
        await db_client.clear_pending_requests()
        
        for ec in self._settings.elevators:
            if ec.id in self.elevators:
                elev = self.elevators[ec.id]
                elev.current_floor = ec.starting_floor
                elev.status = ElevatorStatus.MAINTENANCE if ec.id in self._settings.modes.maintenance_ids else ElevatorStatus.IDLE
                elev.direction = Direction.IDLE
                elev.floor_queue = []
                elev.passenger_count = 0
                elev.floors_served = 0
                await db_client.upsert_elevator(elev)
        
        self.pending_requests.clear()
        self.all_requests.clear()
        self.total_wait_ms = 0.0
        self.requests_completed = 0
        logger.info("Controller state reset with database")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _assign_and_enqueue(self, req: ElevatorRequest) -> None:
        # Filter available elevators
        available = []
        for e in self.elevators.values():
            if not e.is_available():
                continue
            
            # Skip if elevator is full
            if e.passenger_count >= e.capacity:
                continue
            
            available.append(e)
        
        chosen = self._strategy.assign(req, available)

        if chosen is None:
            self.pending_requests.append(req)
            logger.warning("No available elevator — request queued: %s", req.id)
            return

        req.assigned_elevator_id = chosen.id
        req.status = RequestStatus.ASSIGNED

        async with self._locks[chosen.id]:
            # Only add source floor if elevator is not already there with doors open
            if not (chosen.current_floor == req.source_floor and chosen.status == ElevatorStatus.DOORS_OPEN):
                chosen.enqueue_floor(req.source_floor)
            if req.target_floor is not None:
                chosen.enqueue_floor(req.target_floor)
            
            # Only reorder queue if elevator is not currently moving
            if chosen.status not in (ElevatorStatus.MOVING_UP, ElevatorStatus.MOVING_DOWN):
                logger.info("Elevator %s queue before reorder: %s", chosen.id, chosen.floor_queue)
                self._reorder_queue(chosen)
                logger.info("Elevator %s queue after reorder: %s", chosen.id, chosen.floor_queue)
            else:
                logger.info("Elevator %s is moving, appended to queue without reorder: %s", chosen.id, chosen.floor_queue)

        # VIP priority: move VIP-floor requests to front
        if req.source_floor in self._settings.modes.vip_floors:
            async with self._locks[chosen.id]:
                if req.source_floor in chosen.floor_queue:
                    chosen.floor_queue.remove(req.source_floor)
                    chosen.floor_queue.insert(0, req.source_floor)

        logger.info(
            "Assigned request floor=%s dir=%s to elevator=%s", req.source_floor, req.direction.value, chosen.id
        )

    async def _retry_pending(self) -> None:
        """Try to assign previously unassignable pending requests."""
        if not self.pending_requests:
            return
        
        logger.info("Retrying %d pending requests", len(self.pending_requests))
        still_pending = []
        for req in self.pending_requests:
            # For retry, be more aggressive - accept ANY available elevator
            available = [
                e for e in self.elevators.values()
                if e.is_available() and e.passenger_count < e.capacity
            ]
            chosen = self._strategy.assign(req, available)
            if chosen:
                req.assigned_elevator_id = chosen.id
                req.status = RequestStatus.ASSIGNED
                async with self._locks[chosen.id]:
                    chosen.enqueue_floor(req.source_floor)
                    if req.target_floor is not None:
                        chosen.enqueue_floor(req.target_floor)
                    # Always reorder for pending requests
                    self._reorder_queue(chosen)
                logger.info("Assigned pending request floor=%s dir=%s to elevator=%s", 
                           req.source_floor, req.direction.value, chosen.id)
            else:
                still_pending.append(req)
        
        if still_pending:
            logger.warning("%d requests still pending (no available elevator)", len(still_pending))
        self.pending_requests = still_pending

    def _reorder_queue(self, elevator: Elevator) -> None:
        """
        SCAN algorithm:
        1. Deduplicate floors
        2. Sort based on current direction
        """
        if not elevator.floor_queue:
            return

        unique_floors = list(dict.fromkeys(elevator.floor_queue))
        if not unique_floors:
            return
            
        current = elevator.current_floor
        
        # Determine direction from first target
        first_target = unique_floors[0]
        
        if first_target > current:
            # Going UP: serve all floors above in ascending order, then below in descending
            up_floors = sorted([f for f in unique_floors if f > current])
            same_or_down = sorted([f for f in unique_floors if f <= current], reverse=True)
            elevator.floor_queue = up_floors + same_or_down
        elif first_target < current:
            # Going DOWN: serve all floors below in descending order, then above in ascending
            down_floors = sorted([f for f in unique_floors if f < current], reverse=True)
            same_or_up = sorted([f for f in unique_floors if f >= current])
            elevator.floor_queue = down_floors + same_or_up
        else:
            # Target is current floor - keep it first, then sort rest
            rest = [f for f in unique_floors if f != current]
            if rest:
                next_target = rest[0]
                if next_target > current:
                    up = sorted([f for f in rest if f > current])
                    down = sorted([f for f in rest if f < current], reverse=True)
                    elevator.floor_queue = [current] + up + down
                else:
                    down = sorted([f for f in rest if f < current], reverse=True)
                    up = sorted([f for f in rest if f > current])
                    elevator.floor_queue = [current] + down + up
            else:
                elevator.floor_queue = [current]

    def _validate_floor(self, floor: int) -> None:
        max_floor = self._settings.building.floors
        if not (1 <= floor <= max_floor):
            raise ValueError(f"Floor {floor} out of range (1–{max_floor})")
