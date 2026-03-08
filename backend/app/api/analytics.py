"""
app/api/analytics.py
Analytics endpoints for querying historical data via database service.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter
from app.db_client import get_db_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics")


@router.get("/requests/history", summary="Request history")
async def get_request_history(limit: int = 100) -> dict:
    """Get recent request history."""
    # Note: This endpoint currently returns pending requests only
    # A full history endpoint would require a new db-service route
    db_client = get_db_client()
    requests = await db_client.get_pending_requests()
    
    return {
        "total": len(requests),
        "requests": requests[:limit],
    }


@router.get("/elevators/{elevator_id}/history", summary="Elevator movement history")
async def get_elevator_history(elevator_id: int, limit: int = 100) -> dict:
    """Get movement history for a specific elevator."""
    db_client = get_db_client()
    history = await db_client.get_elevator_history(elevator_id, limit)
    
    return {
        "elevator_id": elevator_id,
        "total_visits": len(history),
        "history": history,
    }
