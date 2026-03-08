"""
app/services/simulator.py
SimulationService — async tick loop that drives elevator movement.

Each tick (configured via simulation.tick_interval_ms in config.yaml) steps
each active elevator one floor closer to its next target, then broadcasts
the updated state via WebSocket.

The tick interval and number of floors are driven entirely by config.yaml.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Callable, Awaitable

from app.config import get_settings
from app.db_client import get_db_client
from app.domain.models import Direction, Elevator, ElevatorStatus

if TYPE_CHECKING:
    from app.services.controller import ElevatorController

logger = logging.getLogger(__name__)

BroadcastFn = Callable[[dict], Awaitable[None]]


class SimulationService:
    """
    Runs a background asyncio task that ticks every N milliseconds
    (determined by simulation.tick_interval_ms in config.yaml).
    On each tick every moving elevator advances one floor.
    """

    def __init__(
        self,
        controller: "ElevatorController",
        broadcast: BroadcastFn,
        passenger_sim=None,
    ) -> None:
        self._controller = controller
        self._broadcast = broadcast
        self._passenger_sim = passenger_sim
        self._settings = get_settings()
        self._task: asyncio.Task | None = None
        self._running = False
        self._start_time = asyncio.get_event_loop().time()
        # Track previous state for change detection
        self._prev_states: dict[int, tuple] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the simulation loop as a background asyncio task."""
        if self._running:
            return
        self._running = True
        self._start_time = asyncio.get_event_loop().time()
        # Initialize state snapshots
        for elevator in self._controller.elevators.values():
            self._prev_states[elevator.id] = elevator.get_state_snapshot()
        self._task = asyncio.create_task(self._loop(), name="SimulationLoop")
        logger.info(
            "Simulation started — tick=%sms, strategy=%s",
            self._settings.simulation.tick_interval_ms,
            self._settings.simulation.scheduler_strategy,
        )

    def stop(self) -> None:
        """Stop the simulation loop gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Simulation stopped")

    def restart(self) -> None:
        """Restart the simulation, resetting time and state to initial conditions."""
        self.stop()
        asyncio.create_task(self._async_restart())
        logger.info("Simulation restart initiated")

    async def _async_restart(self) -> None:
        """Async restart helper."""
        await self._controller.reset_state_with_db()
        if self._passenger_sim:
            self._passenger_sim.reset()
            self._passenger_sim.start()
        self._start_time = asyncio.get_event_loop().time()
        self.start()
        logger.info("Simulation restarted")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def _loop(self) -> None:
        interval = self._settings.simulation.tick_interval_ms / 1000.0
        while self._running:
            await asyncio.sleep(interval)
            try:
                await self._tick()
                # Let passenger sim process boarding/alighting for this tick
                if self._passenger_sim is not None:
                    await self._passenger_sim.on_tick(self._controller.elevators)
                state = self._controller.get_status()
                # Add elapsed time in seconds
                state["elapsed_seconds"] = int(asyncio.get_event_loop().time() - self._start_time)
                await self._broadcast(state)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Simulation tick error: %s", exc)

    async def _tick(self) -> None:
        """Advance every active elevator one step toward its next target."""
        changed_elevators = []
        
        for elevator in self._controller.elevators.values():
            prev_state = self._prev_states.get(elevator.id)
            await self._step_elevator(elevator)
            current_state = elevator.get_state_snapshot()
            
            # Only persist if state changed
            if prev_state != current_state:
                changed_elevators.append(elevator)
                self._prev_states[elevator.id] = current_state
        
        # Batch write only changed elevators
        if changed_elevators:
            db_client = get_db_client()
            for elevator in changed_elevators:
                await db_client.upsert_elevator(elevator)
            logger.debug("Persisted %d elevator state changes", len(changed_elevators))

    async def _step_elevator(self, elevator: Elevator) -> None:
        """Move a single elevator one floor, updating status & direction."""
        if not elevator.is_available():
            return  # Skip maintenance / emergency

        target = elevator.next_target()

        if target is None:
            # Nothing to do — mark idle and retry pending requests
            if elevator.status != ElevatorStatus.IDLE:
                elevator.status = ElevatorStatus.IDLE
                elevator.direction = Direction.IDLE
                logger.info("Elevator %s idle at floor %s - checking pending requests", elevator.id, elevator.current_floor)
                # Retry pending requests when elevator becomes idle
                await self._controller._retry_pending()
            return

        if target == elevator.current_floor:
            # Already here — open doors briefly then pop target
            elevator.status = ElevatorStatus.DOORS_OPEN
            await self._controller.complete_floor_visit(elevator.id)
            logger.info(
                "Elevator %s doors open at floor %s", elevator.id, elevator.current_floor
            )
            return

        # Move one floor toward target
        if target > elevator.current_floor:
            elevator.current_floor += 1
            elevator.direction = Direction.UP
            elevator.status = ElevatorStatus.MOVING_UP
        else:
            elevator.current_floor -= 1
            elevator.direction = Direction.DOWN
            elevator.status = ElevatorStatus.MOVING_DOWN

        logger.debug(
            "Elevator %s moved to floor %s (target=%s)",
            elevator.id, elevator.current_floor, target,
        )

        # If we've just reached the target, handle arrival
        if elevator.current_floor == target:
            elevator.status = ElevatorStatus.DOORS_OPEN
            await self._controller.complete_floor_visit(elevator.id)
