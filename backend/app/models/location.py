"""A monitored location: lat/lon + static terrain/land-cover attributes."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin

# WGS84 lat/lon. Geometry is stored as plain Float columns for SQLite compatibility.
GEOMETRY_SRID = 4326


class Location(Base, TimestampMixin):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(120), nullable=False, index=True)

    # WGS84 lat/lon. In production with PostGIS, these duplicate a geometry column.
    latitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)

    # Static attributes (extracted from DEM/land-cover providers).
    elevation_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    slope_deg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    aspect_deg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    land_cover: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    ndvi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Historical landslide count within a configurable radius.
    historical_landslide_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    def __repr__(self) -> str:
        return f"<Location id={self.id} {self.name!r} ({self.latitude},{self.longitude})>"
