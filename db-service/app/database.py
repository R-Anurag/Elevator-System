import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.models.database import Base

# Support Docker secrets
DATABASE_URL_FILE = os.getenv("DATABASE_URL_FILE")
if DATABASE_URL_FILE and os.path.exists(DATABASE_URL_FILE):
    with open(DATABASE_URL_FILE, 'r') as f:
        db_password = f.read().strip()
    DATABASE_URL = f"postgresql+asyncpg://elevator_user:{db_password}@db:5432/elevator_db"
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://elevator_user:elevator_pass@db:5432/elevator_db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
