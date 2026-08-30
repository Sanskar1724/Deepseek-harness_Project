"""One risk prediction snapshot per (location, time, model_version).

Predictions are append-only. The dashboard picks the latest row per location.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class RiskPrediction(Base, TimestampMixin):
    __tablename__ = "risk_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    risk_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0..100
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)  # LOW/MODERATE/HIGH/CRITICAL
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Optional breakdown for explainability. Kept as a JSON string for portability
    # between SQLite and Postgres without a JSONB dependency.
    feature_contributions: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)

    __table_args__ = (
        Index("ix_risk_location_time", "location_id", "timestamp"),
    )
