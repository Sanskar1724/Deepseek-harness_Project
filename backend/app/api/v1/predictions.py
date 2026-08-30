"""On-demand risk prediction for a coordinate."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.models import Location, RiskPrediction
from app.providers import Point
from app.schemas.risk import PredictRequest, RiskResponse
from app.services.alert_engine import check_and_create_alerts
from app.services.risk_engine import score_point
from ml.predict_v3 import predict_full, load_latest

log = get_logger("app.predictions")

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("", response_model=RiskResponse)
def predict(payload: PredictRequest, db: Session = Depends(get_db)) -> RiskResponse:
    point = Point(latitude=payload.latitude, longitude=payload.longitude)
    result = score_point(point)
    # Get full prediction with confidence + feature importance
    confidence = None
    latency_ms = None
    try:
        bundle = load_latest()
        full_result = predict_full(bundle, point)
        confidence = full_result.confidence
        latency_ms = full_result.latency_ms
    except Exception as e:
        log.debug("full_prediction_failed", error=str(e))
    # Fire alerts for HIGH/CRITICAL regardless of save flag
    try:
        check_and_create_alerts(result, point)
    except Exception as e:  # noqa: BLE001
        log.warning("alert_check_failed", error=str(e))
    if payload.save:
        loc = (
            db.query(Location)
            .filter(Location.latitude == payload.latitude, Location.longitude == payload.longitude)
            .first()
        )
        if loc is None:
            loc = Location(
                name=f"({payload.latitude:.4f}, {payload.longitude:.4f})",
                state="unknown",
                district="unknown",
                latitude=payload.latitude,
                longitude=payload.longitude,
            )
            db.add(loc); db.commit(); db.refresh(loc)
        rp = RiskPrediction(
            location_id=loc.id,
            timestamp=datetime.now(timezone.utc),
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            model_version=result.model_version,
        )
        db.add(rp); db.commit()
    return RiskResponse(
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        model_version=result.model_version,
        model_algorithm=result.model_algorithm,
        probability=result.probability,
        confidence=confidence,
        latency_ms=latency_ms,
        is_synthetic=result.is_synthetic,
        timestamp=result.timestamp,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
