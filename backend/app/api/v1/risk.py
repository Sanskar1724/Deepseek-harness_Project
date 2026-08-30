"""Risk endpoints: latest per location, by id, and the map view."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import Location, RiskPrediction
from app.providers import get_weather_provider
from app.schemas.risk import MapRiskPoint, MapRiskResponse, RiskResponse

router = APIRouter(prefix="/risk", tags=["risk"])


def _latest_per_location(db: Session, limit: int) -> List[RiskResponse]:
    """Return the latest prediction per location, up to `limit` rows."""
    rows = db.execute(
        select(RiskPrediction).order_by(desc(RiskPrediction.timestamp)).limit(limit * 5)
    ).scalars()
    is_synth = get_weather_provider().name == "mock"
    seen = set()
    out: List[RiskResponse] = []
    for rp in rows:
        if rp.location_id in seen:
            continue
        seen.add(rp.location_id)
        loc = db.get(Location, rp.location_id)
        if loc is None:
            continue
        out.append(
            RiskResponse(
                risk_score=int(rp.risk_score),
                risk_level=rp.risk_level,
                model_version=rp.model_version,
                model_algorithm="",
                probability=0.0,
                is_synthetic=is_synth,
                timestamp=rp.timestamp,
                latitude=loc.latitude,
                longitude=loc.longitude,
            )
        )
        if len(out) >= limit:
            break
    return out


@router.get("/current", response_model=List[RiskResponse])
def latest_all(limit: int = Query(200, ge=1, le=2000), db: Session = Depends(get_db)) -> List[RiskResponse]:
    return _latest_per_location(db, limit)


@router.get("/map", response_model=MapRiskResponse)
def risk_map(db: Session = Depends(get_db)) -> MapRiskResponse:
    latest = _latest_per_location(db, limit=2000)
    points: List[MapRiskPoint] = []
    for r in latest:
        points.append(
            MapRiskPoint(
                location_id=None,
                name=f"({r.latitude:.3f}, {r.longitude:.3f})",
                latitude=r.latitude,
                longitude=r.longitude,
                risk_score=r.risk_score,
                risk_level=r.risk_level,
            )
        )
    return MapRiskResponse(
        count=len(points),
        generated_at=datetime.now(timezone.utc),
        points=points,
        thresholds=get_settings().risk_thresholds(),
        model_version=(latest[0].model_version if latest else None),
        is_synthetic=bool(latest and latest[0].is_synthetic),
    )


@router.get("/{location_id}", response_model=RiskResponse)
def latest_for_location(location_id: int, db: Session = Depends(get_db)) -> RiskResponse:
    loc = db.get(Location, location_id)
    if loc is None:
        raise NotFoundError(f"location {location_id} not found")
    rp = (
        db.query(RiskPrediction)
        .filter(RiskPrediction.location_id == location_id)
        .order_by(desc(RiskPrediction.timestamp))
        .first()
    )
    if rp is None:
        raise NotFoundError(f"no predictions for location {location_id}")
    return RiskResponse(
        risk_score=int(rp.risk_score),
        risk_level=rp.risk_level,
        model_version=rp.model_version,
        model_algorithm="",
        probability=0.0,
        is_synthetic=get_weather_provider().name == "mock",
        timestamp=rp.timestamp,
        latitude=loc.latitude,
        longitude=loc.longitude,
    )
