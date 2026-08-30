"""Tracks every trained model artifact so we never silently overwrite one."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class ModelRegistry(Base, TimestampMixin):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    algorithm: Mapped[str] = mapped_column(String(40), nullable=False)  # random_forest | xgboost
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    training_dataset: Mapped[str] = mapped_column(String(200), nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON of metrics
    feature_schema_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    promoted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
