"""Schemas for field reports."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReportCreate(BaseModel):
    client_id: str = Field(..., min_length=1, max_length=64)
    report_type: str = Field(..., pattern="^(CRACK|LANDSLIDE|ROCKFALL|ROAD_BLOCKAGE|SLOPE_MOVEMENT|OTHER)$")
    description: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    timestamp: datetime
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    sync_status: str = "synced"


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: str
    report_type: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    timestamp: datetime
    received_at: Optional[datetime] = None
    latitude: float
    longitude: float
    status: str
    sync_status: str
    conflict_with: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class ReportStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(RECEIVED|VERIFIED|REJECTED|DUPLICATE)$")