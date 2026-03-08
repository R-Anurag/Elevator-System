from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ElevatorORM(Base):
    __tablename__ = "elevators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    current_floor: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="IDLE")
    direction: Mapped[str] = mapped_column(String(8), default="IDLE")
    capacity: Mapped[int] = mapped_column(Integer, default=8)
    color: Mapped[str] = mapped_column(String(16), default="#f59e0b")

    requests: Mapped[list["RequestORM"]] = relationship(back_populates="elevator")
    history: Mapped[list["ElevatorHistoryORM"]] = relationship(back_populates="elevator")
    maintenance_logs: Mapped[list["MaintenanceLogORM"]] = relationship(back_populates="elevator")


class RequestORM(Base):
    __tablename__ = "requests"
    __table_args__ = (
        Index("ix_requests_status", "status"),
        Index("ix_requests_elevator", "assigned_elevator_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_floor: Mapped[int] = mapped_column(Integer, nullable=False)
    target_floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    request_type: Mapped[str] = mapped_column(String(16), nullable=False)
    assigned_elevator_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("elevators.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    elevator: Mapped["ElevatorORM | None"] = relationship(back_populates="requests")


class ElevatorHistoryORM(Base):
    __tablename__ = "elevator_history"
    __table_args__ = (Index("ix_history_elevator_time", "elevator_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    elevator_id: Mapped[int] = mapped_column(Integer, ForeignKey("elevators.id"))
    floor: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    elevator: Mapped["ElevatorORM"] = relationship(back_populates="history")


class MaintenanceLogORM(Base):
    __tablename__ = "maintenance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    elevator_id: Mapped[int] = mapped_column(Integer, ForeignKey("elevators.id"))
    description: Mapped[str] = mapped_column(String(256), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    elevator: Mapped["ElevatorORM"] = relationship(back_populates="maintenance_logs")
