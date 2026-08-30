"""Alerts created by the alert engine, plus their delivery attempts."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import TimestampMixin


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    risk_prediction_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("risk_predictions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    location_id: Mapped[int] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # HIGH | CRITICAL
    message: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )


class AlertDelivery(Base):
    __tablename__ = "alert_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(
        ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # in_app | sms | push | log
    recipient: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"  # pending | sent | failed | logged
    )
    provider_response: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
