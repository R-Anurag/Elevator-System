"""
app/services/passenger_sim.py
PassengerSimulationService — manages passenger groups and boarding/alighting.

Core principles:
  • Passengers spawn at configured times and call elevators
  • When elevator arrives, passengers board up to capacity
  • Overflow creates split groups that immediately call for pickup
  • Groups track their own state independently
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

import yaml

from app.domain.models import (
    Direction,
    ElevatorStatus,
    PassengerGroup,
    PassengerGroupState,
)

if TYPE_CHECKING:
    from app.services.controller import ElevatorController

logger = logging.getLogger(__name__)

_SIMULATION_YAML = Path(__file__).parent.parent.parent / "simulation.yaml"
_ALIGHT_TTL = 4.0


class PassengerSimulationService:
    """Manages passenger lifecycle from spawn to delivery."""

    def __init__(self, controller: "ElevatorController") -> None:
        self._controller = controller
        self._groups: Dict[str, PassengerGroup] = {}
        self._spawn_task: Optional[asyncio.Task] = None
        self._watchdog_task: Optional[asyncio.Task] = None
        self._running = False
        self._load_scenario()

    def _load_scenario(self) -> None:
        if not _SIMULATION_YAML.exists():
            logger.warning("simulation.yaml not found — no passengers will spawn")
            return

        with open(_SIMULATION_YAML, "r") as fh:
            data = yaml.safe_load(fh)

        max_floor = self._controller._settings.building.floors
        for entry in data.get("passengers", []):
            src = entry["source_floor"]
            dst = entry["dest_floor"]
            if not (1 <= src <= max_floor and 1 <= dst <= max_floor):
                logger.warning("Ignoring group %s — floors out of range", entry.get("id"))
                continue
            if src == dst:
                logger.warning("Ignoring group %s — source == dest", entry.get("id"))
                continue

            grp = PassengerGroup(
                id=entry["id"],
                source_floor=src,
                dest_floor=dst,
                direction=Direction(entry["direction"].upper()),
                total_count=entry["count"],
                waiting_count=entry["count"],
                riding_count=0,
                delivered_count=0,
                assigned_elevator_id=None,
                state=PassengerGroupState.WAITING,
                spawned=False,
                spawn_at_sec=float(entry["spawn_at_sec"]),
            )
            self._groups[grp.id] = grp
            logger.info("Loaded group %s: floor %s→%s @%ss ×%d",
                        grp.id, grp.source_floor, grp.dest_floor,
                        grp.spawn_at_sec, grp.total_count)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._spawn_task    = asyncio.create_task(self._spawn_loop())
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())
        logger.info("PassengerSimulationService started — %d groups loaded", len(self._groups))

    def stop(self) -> None:
        self._running = False
        if self._spawn_task:
            self._spawn_task.cancel()
        if self._watchdog_task:
            self._watchdog_task.cancel()
        logger.info("PassengerSimulationService stopped")

    async def _spawn_loop(self) -> None:
        """Spawn groups at configured times."""
        start = asyncio.get_event_loop().time()
        pending = sorted(self._groups.values(), key=lambda g: g.spawn_at_sec)
        
        for grp in pending:
            if not self._running:
                break
            
            delay = grp.spawn_at_sec
            if delay > 0:
                await asyncio.sleep(delay)
            
            if self._running:
                grp.spawned = True
                grp.spawned_at = datetime.utcnow()
                await self._call_elevator(grp.source_floor, grp.direction)
                logger.info("Spawned group %s at floor %s ×%d",
                            grp.id, grp.source_floor, grp.waiting_count)

    async def _call_elevator(self, floor: int, direction: Direction) -> Optional[int]:
        """Request an elevator for a floor. Returns chosen elevator id, or None."""
        try:
            req = await self._controller.handle_external_request(floor=floor, direction=direction)
            return req.assigned_elevator_id
        except Exception as exc:
            logger.error("Failed to call elevator to floor %s: %s", floor, exc)
            return None

    async def on_tick(self, elevators: Dict) -> None:
        """Process boarding and alighting on each tick."""
        for elevator in elevators.values():
            if elevator.status != ElevatorStatus.DOORS_OPEN:
                continue

            floor = elevator.current_floor
            
            # Alight passengers first
            await self._process_alighting(elevator, floor)
            
            # Board passengers (doors are open at this floor)
            await self._process_boarding(elevator, floor)
        
        # After all boarding/alighting, retry pending requests
        await self._controller._retry_pending()

    async def _process_alighting(self, elevator, floor: int) -> None:
        """Deliver passengers at their destination."""
        for grp in list(self._groups.values()):
            if (
                grp.state == PassengerGroupState.RIDING
                and grp.assigned_elevator_id == elevator.id
                and grp.dest_floor == floor
                and grp.riding_count > 0
            ):
                elevator.passenger_count = max(0, elevator.passenger_count - grp.riding_count)
                grp.delivered_count += grp.riding_count
                grp.riding_count = 0
                grp.state = PassengerGroupState.DELIVERED
                
                logger.info("Group %s delivered at floor %s (×%d)",
                            grp.id, floor, grp.delivered_count)
                
                asyncio.create_task(self._cleanup_after(grp.id, _ALIGHT_TTL))

    async def _process_boarding(self, elevator, floor: int) -> None:
        """Board waiting passengers onto elevator."""
        # Grace period: a group must have been WAITING for at least one full tick
        # before it can board.  This guarantees the WebSocket broadcasts the group
        # as WAITING at least once, so the frontend can render the sprites before
        # the boarding animation fires.
        tick_sec = self._controller._settings.simulation.tick_interval_ms / 1000.0
        now = datetime.utcnow()

        waiting_here = [
            g for g in self._groups.values()
            if g.state == PassengerGroupState.WAITING
            and g.source_floor == floor
            and g.waiting_count > 0
            and g.spawned
            and g.spawned_at is not None
            and (now - g.spawned_at).total_seconds() >= tick_sec
        ]

        if not waiting_here:
            return

        
        for grp in waiting_here:
            slots_free = elevator.capacity - elevator.passenger_count
            if slots_free <= 0:
                break  # Elevator full
            
            can_board = min(grp.waiting_count, slots_free)
            
            # Handle overflow
            if can_board < grp.waiting_count:
                leftover_count = grp.waiting_count - can_board
                leftover_id = f"{grp.id}_split_{uuid.uuid4().hex[:6]}"
                
                leftover = PassengerGroup(
                    id=leftover_id,
                    source_floor=grp.source_floor,
                    dest_floor=grp.dest_floor,
                    direction=grp.direction,
                    total_count=leftover_count,
                    waiting_count=leftover_count,
                    riding_count=0,
                    delivered_count=0,
                    assigned_elevator_id=None,
                    state=PassengerGroupState.WAITING,
                    spawned=True,
                    spawned_at=datetime.utcnow(),
                )
                self._groups[leftover_id] = leftover
                
                logger.warning("Overflow: group %s split — %d board, %d remain as %s",
                               grp.id, can_board, leftover_count, leftover_id)
                
                # Call elevator for leftover group.
                # CRITICAL FIX: _assign_and_enqueue skips enqueuing source_floor when
                # elevator.status == DOORS_OPEN and it's already at that floor — which
                # is exactly the situation here (boarding just happened).  We therefore
                # force-enqueue the source floor on whichever elevator gets assigned so
                # it actually returns after it leaves.
                chosen_id = await self._call_elevator(grp.source_floor, grp.direction)
                if chosen_id is not None:
                    chosen_elev = self._controller.elevators.get(chosen_id)
                    if chosen_elev is not None:
                        async with self._controller._locks[chosen_id]:
                            chosen_elev.enqueue_floor(grp.source_floor)
                        logger.info(
                            "Force-enqueued floor %s on elevator %s for leftover group %s",
                            grp.source_floor, chosen_id, leftover_id,
                        )
            
            # Update elevator passenger count immediately
            elevator.passenger_count += can_board
            logger.info("Elevator %s passenger_count now: %d", elevator.id, elevator.passenger_count)
            
            # Start boarding animation
            grp.state = PassengerGroupState.BOARDING
            grp.assigned_elevator_id = elevator.id
            grp.boarded_at = datetime.utcnow()
            grp.waiting_count = 0
            grp.riding_count = can_board
            
            # Track wait time
            if grp.spawned_at:
                wait_ms = (grp.boarded_at - grp.spawned_at).total_seconds() * 1000
                self._controller.total_wait_ms += wait_ms * can_board
                self._controller.requests_completed += can_board
            
            logger.info("Group %s (dir=%s) boarding elevator %s (×%d)",
                        grp.id, grp.direction.value, elevator.id, can_board)
            
            # Transition to RIDING after animation
            asyncio.create_task(self._complete_boarding(grp.id, elevator.id))

    async def _complete_boarding(self, group_id: str, elevator_id: int) -> None:
        """Transition from BOARDING to RIDING after animation."""
        await asyncio.sleep(0.6)
        
        grp = self._groups.get(group_id)
        if not grp or grp.state != PassengerGroupState.BOARDING:
            return
        
        grp.state = PassengerGroupState.RIDING
        
        # Add destination to queue
        try:
            await self._controller.handle_internal_request(
                elevator_id=elevator_id,
                target_floor=grp.dest_floor,
            )
        except Exception as exc:
            logger.error("Internal request for group %s failed: %s", grp.id, exc)
        
        logger.info("Group %s riding elevator %s → floor %s",
                    grp.id, elevator_id, grp.dest_floor)

    async def _cleanup_after(self, group_id: str, delay: float) -> None:
        """Remove delivered group after animation."""
        await asyncio.sleep(delay)
        self._groups.pop(group_id, None)
        logger.debug("Cleaned up group %s", group_id)

    async def _watchdog_loop(self) -> None:
        """
        Safety net: every 2 seconds scan for WAITING groups whose source floor
        is not already in any elevator's queue.  Re-call the elevator for them.
        This catches groups that were orphaned because the scheduler skipped
        enqueuing their floor (e.g. duplicate-floor guard during DOORS_OPEN).
        """
        tick_interval = self._controller._settings.simulation.tick_interval_ms / 1000.0
        watchdog_interval = max(tick_interval * 2, 2.0)

        await asyncio.sleep(watchdog_interval)  # let initial spawns settle

        while self._running:
            await asyncio.sleep(watchdog_interval)
            try:
                await self._rescue_orphans()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Watchdog error: %s", exc)

    async def _rescue_orphans(self) -> None:
        """Find WAITING groups with no elevator heading to their floor and re-call."""
        # Collect all floors currently enqueued across all elevators
        covered_floors: set[int] = set()
        for elev in self._controller.elevators.values():
            covered_floors.update(elev.floor_queue)
            # Also count elevator already at a floor with doors open
            if elev.status.value == "DOORS_OPEN":
                covered_floors.add(elev.current_floor)

        for grp in list(self._groups.values()):
            if (
                grp.state == PassengerGroupState.WAITING
                and grp.spawned
                and grp.waiting_count > 0
                and grp.source_floor not in covered_floors
            ):
                logger.warning(
                    "Watchdog: orphaned group %s (%d pax) at floor %s — re-calling elevator",
                    grp.id, grp.waiting_count, grp.source_floor,
                )
                chosen_id = await self._call_elevator(grp.source_floor, grp.direction)
                if chosen_id is not None:
                    covered_floors.add(grp.source_floor)  # mark covered for this scan

    def get_groups_snapshot(self) -> List[dict]:
        """Return serializable snapshot for WebSocket broadcast."""
        return [g.to_dict() for g in self._groups.values()]

    def reset(self) -> None:
        """Reset passenger simulation to initial state."""
        self._running = False
        if self._spawn_task:
            self._spawn_task.cancel()
        if self._watchdog_task:
            self._watchdog_task.cancel()
        self._groups.clear()
        self._load_scenario()
        logger.info("Passenger simulation reset")
