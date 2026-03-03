"""
app/database.py
Async SQLAlchemy setup.  The DB URL is driven entirely by config.yaml.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

# Ensure the URL uses the aiosqlite driver for SQLite
_url = settings.database.url
if _url.startswith("sqlite:///") and "aiosqlite" not in _url:
    _url = _url.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(
    _url,
    echo=settings.database.echo_sql,
    connect_args={"check_same_thread": False} if "sqlite" in _url else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields a DB session."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables on startup."""
    from app.db import models as _  # noqa: F401 – ensure models are registered
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
