"""Schemas for monitored locations."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    state: str = Field(..., min_length=1, max_length=80)
    district: str = Field(..., min_length=1, max_length=120)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None
    aspect_deg: Optional[float] = None
    land_cover: Optional[str] = None
    ndvi: Optional[float] = None
    historical_landslide_count: int = 0


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    state: str
    district: str
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None
    slope_deg: Optional[float] = None
    aspect_deg: Optional[float] = None
    land_cover: Optional[str] = None
    ndvi: Optional[float] = None
    historical_landslide_count: int = 0
    created_at: datetime
    updated_at: datetime
