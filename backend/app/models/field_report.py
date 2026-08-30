"""Citizen/field reports. Designed to support offline sync (Phase 13)."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class ReportType(str, enum.Enum):
    CRACK = "CRACK"
    LANDSLIDE = "LANDSLIDE"
    ROCKFALL = "ROCKFALL"
    ROAD_BLOCKAGE = "ROAD_BLOCKAGE"
    SLOPE_MOVEMENT = "SLOPE_MOVEMENT"
    OTHER = "OTHER"


class ReportStatus(str, enum.Enum):
    PENDING_SYNC = "PENDING_SYNC"
    RECEIVED = "RECEIVED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"


class FieldReport(Base, TimestampMixin):
    __tablename__ = "field_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    report_type: Mapped[ReportType] = mapped_column(
        Enum(ReportType, native_enum=False, length=24), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    received_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, native_enum=False, length=24),
        nullable=False,
        default=ReportStatus.RECEIVED,
    )
    sync_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="synced"
    )
    conflict_with: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
