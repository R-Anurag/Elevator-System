import os
from datetime import datetime
from typing import List, Optional
import httpx
from app.domain.models import Elevator, ElevatorRequest

DB_SERVICE_URL = os.getenv("DB_SERVICE_URL", "http://db-service:8001/api")


class DatabaseClient:
    def __init__(self):
        self.base_url = DB_SERVICE_URL
        self.client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        await self.client.aclose()

    # Elevator operations
    async def upsert_elevator(self, elevator: Elevator):
        data = {
            "id": elevator.id,
            "name": elevator.name,
            "current_floor": elevator.current_floor,
            "status": elevator.status.value,
            "direction": elevator.direction.value,
            "capacity": elevator.capacity,
            "color": elevator.color,
        }
        await self.client.post(f"{self.base_url}/elevators", json=data)

    async def load_all_elevators(self) -> List[dict]:
        response = await self.client.get(f"{self.base_url}/elevators")
        return response.json()

    # Request operations
    async def save_request(self, request: ElevatorRequest):
        data = {
            "id": request.id,
            "source_floor": request.source_floor,
            "target_floor": request.target_floor,
            "direction": request.direction.value,
            "request_type": request.request_type.value,
            "assigned_elevator_id": request.assigned_elevator_id,
            "status": request.status.value,
            "created_at": request.created_at.isoformat(),
            "completed_at": request.completed_at.isoformat() if request.completed_at else None,
        }
        await self.client.post(f"{self.base_url}/requests", json=data)

    async def update_request(self, request: ElevatorRequest):
        data = {
            "id": request.id,
            "source_floor": request.source_floor,
            "target_floor": request.target_floor,
            "direction": request.direction.value,
            "request_type": request.request_type.value,
            "assigned_elevator_id": request.assigned_elevator_id,
            "status": request.status.value,
            "created_at": request.created_at.isoformat(),
            "completed_at": request.completed_at.isoformat() if request.completed_at else None,
        }
        await self.client.put(f"{self.base_url}/requests/{request.id}", json=data)

    async def get_pending_requests(self) -> List[dict]:
        response = await self.client.get(f"{self.base_url}/requests/pending")
        return response.json()

    # History operations
    async def log_floor_visit(self, elevator_id: int, floor: int, status: str, direction: str):
        data = {
            "elevator_id": elevator_id,
            "floor": floor,
            "status": status,
            "direction": direction,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.client.post(f"{self.base_url}/history", json=data)

    async def get_elevator_history(self, elevator_id: int, limit: int = 100) -> List[dict]:
        response = await self.client.get(f"{self.base_url}/history/{elevator_id}?limit={limit}")
        return response.json()

    async def clear_pending_requests(self):
        """Cancel all pending/assigned requests (for restart)."""
        await self.client.delete(f"{self.base_url}/requests/pending")

    # Maintenance operations
    async def start_maintenance(self, elevator_id: int, description: str = ""):
        await self.client.post(f"{self.base_url}/maintenance/start?elevator_id={elevator_id}&description={description}")

    async def end_maintenance(self, elevator_id: int):
        await self.client.post(f"{self.base_url}/maintenance/end/{elevator_id}")


# Singleton instance
_db_client: Optional[DatabaseClient] = None


def get_db_client() -> DatabaseClient:
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client
