"""Risk engine.

Converts a model probability into a 0-100 risk score and a 4-level class,
using thresholds read from settings. Thresholds are NEVER hardcoded in this
module or anywhere downstream; they are loaded once at startup from env.

The score is computed as round(prob * 100). The calibration work is the model
job. If you want a more elaborate mapping (piecewise linear with a fuse near
critical), add it here behind the same function signature so nothing downstream
changes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers import Point, get_landslide_provider
from ml.predict_v3 import (
    ModelNotFoundError,
    load_latest,
    predict_proba,
    predict_full,
    health_check as model_health,
)

log = get_logger("app.risk")

LEVEL_LOW = "LOW"
LEVEL_MODERATE = "MODERATE"
LEVEL_HIGH = "HIGH"
LEVEL_CRITICAL = "CRITICAL"
ALL_LEVELS = (LEVEL_LOW, LEVEL_MODERATE, LEVEL_HIGH, LEVEL_CRITICAL)


@dataclass
class RiskResult:
    risk_score: int
    risk_level: str
    model_version: str
    model_algorithm: str
    probability: float
    is_synthetic: bool
    timestamp: datetime
    latitude: float | None = None
    longitude: float | None = None

    def as_dict(self) -> dict:
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "model_version": self.model_version,
            "model_algorithm": self.model_algorithm,
            "probability": round(self.probability, 6),
            "is_synthetic": self.is_synthetic,
            "timestamp": self.timestamp.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


def classify(score: int, *, thresholds: Optional[dict] = None) -> str:
    """Map a 0-100 score to LOW/MODERATE/HIGH/CRITICAL using the configured thresholds."""
    if thresholds is None:
        thresholds = get_settings().risk_thresholds()
    if score < thresholds["low"]:
        return LEVEL_LOW
    if score < thresholds["moderate"]:
        return LEVEL_MODERATE
    if score < thresholds["high"]:
        return LEVEL_HIGH
    return LEVEL_CRITICAL


def score_from_proba(probability: float) -> int:
    p = max(0.0, min(1.0, float(probability)))
    return int(round(p * 100))


def _historical_count(point: Point) -> int:
    try:
        events = get_landslide_provider().list_events(near=point, radius_km=50.0)
        return len(events)
    except Exception as e:  # noqa: BLE001
        log.warning("historical_count_failed", error=str(e))
        return 0


def score_point(point: Point, *, now: Optional[datetime] = None) -> RiskResult:
    """End-to-end: providers + model + classify + is_synthetic flag."""
    now = now or datetime.now(timezone.utc)
    try:
        bundle = load_latest()
    except ModelNotFoundError as e:
        log.warning("no_model_available", error=str(e))
        return RiskResult(
            risk_score=0,
            risk_level=LEVEL_LOW,
            model_version="none",
            model_algorithm="none",
            probability=0.0,
            is_synthetic=True,
            timestamp=now,
            latitude=point.latitude,
            longitude=point.longitude,
        )

    hist = _historical_count(point)
    proba = predict_proba(bundle, point, historical_count=hist)
    score = score_from_proba(proba)
    level = classify(score)

    from app.providers import (  # local import to avoid a cycle in tests
        get_rainfall_provider,
        get_satellite_provider,
        get_soil_provider,
        get_terrain_provider,
        get_weather_provider,
    )
    # Live if core providers are real; satellite is optional (no free real provider) so ignore it
    is_synth = any(
        p.name == "mock"
        for p in [
            get_weather_provider(),
            get_rainfall_provider(),
            get_terrain_provider(),
            get_soil_provider(),
        ]
    )
    return RiskResult(
        risk_score=score,
        risk_level=level,
        model_version=bundle.model_version,
        model_algorithm=bundle.algorithm,
        probability=proba,
        is_synthetic=is_synth,
        timestamp=now,
        latitude=point.latitude,
        longitude=point.longitude,
    )
