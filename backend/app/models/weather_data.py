"""Observed + forecast weather snapshots, indexed by location + timestamp."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class WeatherData(Base, TimestampMixin):
    __tablename__ = "weather_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # Antecedent rainfall (mm).
    rainfall_1h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rainfall_6h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rainfall_24h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rainfall_72h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    forecast_rainfall_24h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    forecast_rainfall_72h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Other atmospheric features.
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    humidity_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    soil_moisture_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Provenance. Lets the risk engine + UI tag mock data honestly.
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="mock")

    __table_args__ = (
        Index("ix_weather_location_time", "location_id", "timestamp"),
    )
