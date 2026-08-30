"""Schemas for risk + prediction endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    save: bool = Field(default=True, description="If true, persist the prediction to the DB.")


class RiskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str
    model_version: str
    model_algorithm: str
    probability: float
    confidence: Optional[float] = Field(default=None, description="0-1, how confident the model is")
    latency_ms: Optional[float] = Field(default=None, description="Prediction latency in ms")
    is_synthetic: bool
    timestamp: datetime
    latitude: float
    longitude: float


class MapRiskPoint(BaseModel):
    location_id: Optional[int] = None
    name: str
    latitude: float
    longitude: float
    risk_score: int
    risk_level: str
    state: Optional[str] = None
    district: Optional[str] = None


class MapRiskResponse(BaseModel):
    count: int
    generated_at: datetime
    points: List[MapRiskPoint]
    thresholds: dict
    model_version: Optional[str] = None
    is_synthetic: bool = True
