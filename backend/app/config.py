"""
app/config.py
Loads config.yaml and provides a typed Settings object to the entire application.
This is the single source of truth for all functional requirements.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Sub-models (sections of config.yaml)
# ---------------------------------------------------------------------------

class BuildingConfig(BaseModel):
    # Required — owned by config.yaml. No defaults here to avoid dual-maintenance.
    floors: int
    elevator_capacity: int
    floor_height_px: int


class SimulationConfig(BaseModel):
    # Required — owned by config.yaml.
    tick_interval_ms: int
    scheduler_strategy: str


class ElevatorConfig(BaseModel):
    id: int
    name: str
    starting_floor: int = 1    # Optional override — default is fine
    color: str = "#f59e0b"     # Optional override — default is fine


class ModesConfig(BaseModel):
    # Required — owned by config.yaml.
    emergency_floor: int
    vip_floors: List[int]
    maintenance_ids: List[int] = []   # Empty list is a safe, obvious default


class DatabaseConfig(BaseModel):
    # Infrastructure — reasonable defaults so devs don't need to touch YAML to run locally.
    url: str = "sqlite+aiosqlite:///./elevator.db"
    echo_sql: bool = False


class ApiConfig(BaseModel):
    # Infrastructure — same rationale.
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000"]


class Settings(BaseModel):
    """
    Master settings object loaded from config.yaml.
    Functional sections (building, simulation, modes) are required.
    Infrastructure sections (database, api) have safe defaults.
    """
    building: BuildingConfig
    simulation: SimulationConfig
    elevators: List[ElevatorConfig]
    modes: ModesConfig
    database: DatabaseConfig = DatabaseConfig()
    api: ApiConfig = ApiConfig()

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Settings":
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
        return cls.model_validate(raw)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def get_settings() -> Settings:
    """Return Settings loaded from config.yaml (reloads on every call for hot reload)."""
    return Settings.from_yaml(_CONFIG_PATH)
