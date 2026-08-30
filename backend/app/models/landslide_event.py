"""Historical landslide records."""
from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Date, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class LandslideEvent(Base, TimestampMixin):
    __tablename__ = "landslide_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
