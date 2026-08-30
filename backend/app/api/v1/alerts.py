"""Alerts API."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Alert, AlertDelivery

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    severity: str
    message: str
    language: str
    created_at: datetime


class DeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    alert_id: int
    channel: str
    recipient: str
    status: str
    provider_response: Optional[str] = None
    created_at: datetime


@router.get("", response_model=List[AlertOut])
def list_alerts(
    severity: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[Alert]:
    stmt = db.query(Alert).order_by(desc(Alert.created_at))
    if severity:
        stmt = stmt.filter(Alert.severity == severity)
    return stmt.limit(limit).all()


@router.get("/{alert_id}/deliveries", response_model=List[DeliveryOut])
def list_deliveries(alert_id: int, db: Session = Depends(get_db)) -> List[AlertDelivery]:
    return db.query(AlertDelivery).filter(AlertDelivery.alert_id == alert_id).all()
