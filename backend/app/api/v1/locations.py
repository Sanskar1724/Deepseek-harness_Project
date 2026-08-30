"""Monitored locations CRUD + list."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import Location
from app.schemas.location import LocationCreate, LocationOut

router = APIRouter(prefix="/locations", tags=["locations"])


@router.post("", response_model=LocationOut, status_code=201)
def create_location(payload: LocationCreate, db: Session = Depends(get_db)) -> Location:
    loc = Location(**payload.model_dump())
    db.add(loc); db.commit(); db.refresh(loc)
    return loc


@router.get("", response_model=List[LocationOut])
def list_locations(
    state: Optional[str] = None,
    district: Optional[str] = None,
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> List[Location]:
    stmt = select(Location).order_by(Location.id)
    if state:
        stmt = stmt.where(Location.state == state)
    if district:
        stmt = stmt.where(Location.district == district)
    return list(db.execute(stmt.limit(limit)).scalars())


@router.get("/{location_id}", response_model=LocationOut)
def get_location(location_id: int, db: Session = Depends(get_db)) -> Location:
    loc = db.get(Location, location_id)
    if loc is None:
        raise NotFoundError(f"location {location_id} not found")
    return loc
