"""
app/api/websocket.py
WebSocket connection manager + endpoint.

The ConnectionManager broadcasts JSON state to ALL connected dashboard clients
after every simulation tick.  Clients reconnect automatically on disconnect.
"""
from __future__ import annotations

import json
import logging
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages the set of active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info("WS client connected — total=%s", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info("WS client disconnected — total=%s", len(self._connections))

    async def broadcast(self, data: dict) -> None:
        """Send a JSON snapshot to every connected client."""
        payload = json.dumps(data)
        dead: List[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Singleton shared across the app
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    WebSocket endpoint — clients connect here and receive JSON state
    pushed from the simulation loop on every tick.
    """
    from app.main import controller  # late import to avoid circular

    await manager.connect(websocket)
    try:
        # Send the current state immediately on connect
        await websocket.send_text(json.dumps(controller.get_status()))
        # Keep channel open — server pushes; client listens
        while True:
            await websocket.receive_text()  # ping-pong or ignore
    except WebSocketDisconnect:
        manager.disconnect(websocket)
