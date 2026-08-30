"""IoT sensor ingestion API."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Sensor, SensorReading

router = APIRouter(prefix="/sensors", tags=["sensors"])


class SensorIngest(BaseModel):
    sensor_id: str = Field(..., min_length=1, max_length=64)
    kind: str = Field(..., description="e.g. soil_moisture, pore_pressure, rain_gauge")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    timestamp: datetime
    soil_moisture: Optional[float] = None
    pore_pressure: Optional[float] = None
    temperature: Optional[float] = None


class SensorOut(BaseModel):
    id: int
    sensor_id: str
    kind: str
    latitude: float
    longitude: float
    last_seen_at: Optional[datetime] = None


@router.post("/data", status_code=201)
def ingest(payload: SensorIngest, db: Session = Depends(get_db)):
    sensor = db.query(Sensor).filter(Sensor.sensor_id == payload.sensor_id).one_or_none()
    if sensor is None:
        sensor = Sensor(
            sensor_id=payload.sensor_id,
            kind=payload.kind,
            latitude=payload.latitude,
            longitude=payload.longitude,
            last_seen_at=payload.timestamp,
        )
        db.add(sensor); db.commit(); db.refresh(sensor)
    else:
        sensor.last_seen_at = payload.timestamp
        db.commit()
    reading = SensorReading(
        sensor_pk=sensor.id,
        timestamp=payload.timestamp,
        soil_moisture=payload.soil_moisture,
        pore_pressure=payload.pore_pressure,
        temperature=payload.temperature,
    )
    db.add(reading); db.commit()
    return {"sensor_pk": sensor.id, "reading_id": reading.id}


@router.get("", response_model=list[SensorOut])
def list_sensors(
    limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)
) -> list[Sensor]:
    return db.query(Sensor).limit(limit).all()
