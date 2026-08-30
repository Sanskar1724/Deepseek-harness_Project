"""Geocode / reverse-geocode for common people - uses Nominatim (no key)."""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.providers.nominatim import geocode, reverse_geocode
from app.providers.base import Point

router = APIRouter(prefix="/geocode", tags=["geocode"])


class GeocodeOut(BaseModel):
    latitude: float
    longitude: float
    display_name: str | None = None
    found: bool


@router.get("/search", response_model=GeocodeOut)
def search(place: str = Query(..., description="e.g. Imphal, Guwahati")):
    pt = geocode(place)
    if pt is None:
        return GeocodeOut(latitude=0, longitude=0, display_name=None, found=False)
    name = reverse_geocode(pt.latitude, pt.longitude)
    return GeocodeOut(latitude=pt.latitude, longitude=pt.longitude, display_name=name, found=True)


@router.get("/reverse", response_model=GeocodeOut)
def reverse(latitude: float = Query(..., ge=-90, le=90), longitude: float = Query(..., ge=-180, le=180)):
    name = reverse_geocode(latitude, longitude)
    return GeocodeOut(latitude=latitude, longitude=longitude, display_name=name, found=name is not None)
