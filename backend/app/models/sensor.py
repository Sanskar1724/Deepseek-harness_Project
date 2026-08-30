"""IoT sensors and their readings."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class Sensor(Base, TimestampMixin):
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sensor_pk: Mapped[int] = mapped_column(
        ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    soil_moisture: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pore_pressure: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
