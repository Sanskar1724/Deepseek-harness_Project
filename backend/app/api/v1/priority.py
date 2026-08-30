"""Priority endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.providers import Point
from app.services.priority_engine import prioritize_point, PriorityResult

router = APIRouter(prefix="/priority", tags=["priority"])


class PriorityOut:
    risk_score: int
    risk_level: str
    model_version: str
    probability: float
    priority: str
    rationale: str
    exposed_count: int
    latitude: float
    longitude: float


@router.get("/{latitude}/{longitude}")
def get_priority(
    latitude: float, longitude: float, db: Session = Depends(get_db)
):
    point = Point(latitude=latitude, longitude=longitude)
    result = prioritize_point(point)
    return {
        "risk_score": result.risk_result.risk_score,
        "risk_level": result.risk_result.risk_level,
        "model_version": result.risk_result.model_version,
        "probability": result.risk_result.probability,
        "priority": result.priority,
        "rationale": result.rationale,
        "exposed_count": len(result.exposed_assets),
        "latitude": latitude,
        "longitude": longitude,
    }


@router.get("")
def list_priorities(
    state: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return priorities for all known locations (or filtered by state)."""
    from app.models import Location
    from sqlalchemy import select

    stmt = select(Location)
    if state:
        stmt = stmt.where(Location.state == state)
    locs = list(db.execute(stmt.limit(limit)).scalars())
    out = []
    for loc in locs:
        point = Point(latitude=loc.latitude, longitude=loc.longitude)
        result = prioritize_point(point)
        out.append({
            "location_id": loc.id,
            "name": loc.name,
            "state": loc.state,
            "district": loc.district,
            "risk_score": result.risk_result.risk_score,
            "risk_level": result.risk_result.risk_level,
            "priority": result.priority,
            "rationale": result.rationale,
            "exposed_count": len(result.exposed_assets),
            "latitude": loc.latitude,
            "longitude": loc.longitude,
        })
    # Sort by risk desc, then P1 first
    out.sort(key=lambda x: (-x["risk_score"], x["priority"]))
    return out