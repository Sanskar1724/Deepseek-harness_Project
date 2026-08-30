"""Strong connected backend - one call gives everything: risk + priority + alternatives + weather + place."""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db.session import haversine_km
from app.providers import Point
from app.providers.nominatim import reverse_geocode
from app.services.risk_engine import score_point
from app.services.priority_engine import prioritize_point

# Satellite AI - additive, optional, cached
try:
    from app.providers.satellite_ai.mock import MockSatelliteAIProvider
    _sat_provider = MockSatelliteAIProvider()
except Exception:
    _sat_provider = None

router = APIRouter(prefix="/assess", tags=["assess"])


class AlternativeOut(BaseModel):
    latitude: float
    longitude: float
    distance_km: float
    risk_score: int
    risk_level: str
    name: str


class SatelliteEvidenceOut(BaseModel):
    available: bool
    landslide_probability: float | None = None
    confidence: float | None = None
    source: str | None = None
    is_live: bool = False
    signals: dict | None = None


class AssessOut(BaseModel):
    latitude: float
    longitude: float
    place_name: str | None
    risk_score: int
    risk_level: str
    probability: float
    confidence: int
    model_version: str
    is_synthetic: bool
    priority: str
    rationale: str
    exposed_count: int
    alternatives: list[AlternativeOut]
    action: str
    is_live: bool
    satellite_evidence: SatelliteEvidenceOut | None = None


def _action_for_level(level: str) -> str:
    return {
        "LOW": "Safe — normal activities. No alternative needed.",
        "MODERATE": "Caution — avoid steep slopes after heavy rain. Monitor.",
        "HIGH": "Alternative advised — take safer road, avoid hill travel.",
        "CRITICAL": "Evacuate alternative — move to nearest LOW zone, follow official alert.",
    }.get(level, "Monitor")


@router.get("", response_model=AssessOut)
def assess(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    improved: bool = Query(False, description="Use improved satellite-fused prediction when available"),
):
    point = Point(latitude=latitude, longitude=longitude)
    risk = score_point(point)
    # If improved requested, try fusion with satellite evidence (additive, validated)
    if improved:
        try:
            from app.providers.satellite_ai.mock import MockSatelliteAIProvider
            from app.services.fusion import fuse
            from app.services.risk_engine import classify, score_from_proba
            sat_tmp = MockSatelliteAIProvider().get_evidence(point)
            fused = fuse(risk.probability, sat_tmp, strategy="fusion")
            # Use fused probability but keep same RiskResult structure for display
            risk = type(risk)(
                risk_score=score_from_proba(fused.fused_probability),
                risk_level=classify(score_from_proba(fused.fused_probability)),
                model_version=risk.model_version + "+sat" if fused.satellite_available else risk.model_version,
                model_algorithm=risk.model_algorithm,
                probability=fused.fused_probability,
                is_synthetic=risk.is_synthetic,
                timestamp=risk.timestamp,
                latitude=risk.latitude,
                longitude=risk.longitude,
            )
        except Exception:
            pass
    pri = prioritize_point(point)
    place = None
    try:
        place = reverse_geocode(latitude, longitude)
    except Exception:
        place = None

    # Find alternatives: nearby LOW risk points from DB
    alts: list[AlternativeOut] = []
    try:
        from app.db.session import SessionLocal
        from app.models import Location, RiskPrediction
        from sqlalchemy import desc

        with SessionLocal() as db:
            # Get latest risk per location, filter LOW within 20km
            locs = db.query(Location).all()
            # For each loc, get its latest risk quickly from RiskPrediction
            for loc in locs[:200]:  # limit scan
                d = haversine_km(latitude, longitude, loc.latitude, loc.longitude)
                if d > 20:  # only nearby
                    continue
                rp = (
                    db.query(RiskPrediction)
                    .filter(RiskPrediction.location_id == loc.id)
                    .order_by(desc(RiskPrediction.timestamp))
                    .first()
                )
                if rp and rp.risk_level == "LOW":
                    alts.append(
                        AlternativeOut(
                            latitude=loc.latitude,
                            longitude=loc.longitude,
                            distance_km=round(d, 1),
                            risk_score=int(rp.risk_score),
                            risk_level=rp.risk_level,
                            name=loc.name,
                        )
                    )
                    if len(alts) >= 3:
                        break
            alts.sort(key=lambda x: x.distance_km)
    except Exception:
        alts = []

    conf = int(round(risk.probability * 100))
    # Satellite evidence - additive, never breaks existing flow (Phase 8, 11)
    sat_ev = None
    try:
        if _sat_provider is not None:
            # Simple cache key: lat,lon rounded to 3 decimals + day
            from datetime import datetime, timezone
            import hashlib
            cache_key = f"{round(latitude,3)}:{round(longitude,3)}:{datetime.now(timezone.utc).strftime('%Y%m%d')}"
            # Use lru_cache via provider's deterministic hash - mock is <1ms, no need for extra cache
            ev = _sat_provider.get_evidence(point)
            sat_ev = SatelliteEvidenceOut(
                available=ev.available,
                landslide_probability=ev.landslide_probability,
                confidence=ev.confidence,
                source=ev.source,
                is_live=ev.is_live,
                signals=ev.signals,
            )
        else:
            sat_ev = SatelliteEvidenceOut(available=False)
    except Exception:
        sat_ev = SatelliteEvidenceOut(available=False)

    return AssessOut(
        latitude=latitude,
        longitude=longitude,
        place_name=place,
        risk_score=risk.risk_score,
        risk_level=risk.risk_level,
        probability=round(risk.probability, 4),
        confidence=conf,
        model_version=risk.model_version,
        is_synthetic=risk.is_synthetic,
        priority=pri.priority,
        rationale=pri.rationale,
        exposed_count=len(pri.exposed_assets),
        alternatives=alts,
        action=_action_for_level(risk.risk_level),
        is_live=not risk.is_synthetic,
        satellite_evidence=sat_ev,
    )


@router.get("/alternatives", response_model=list[AlternativeOut])
def alternatives(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(20, ge=1, le=100),
):
    """Only alternatives — lightweight."""
    point = Point(latitude=latitude, longitude=longitude)
    risk = score_point(point)
    # If already LOW, no alternative needed
    if risk.risk_level == "LOW":
        return []
    # Reuse same logic as assess
    alts: list[AlternativeOut] = []
    try:
        from app.db.session import SessionLocal
        from app.models import Location, RiskPrediction
        from sqlalchemy import desc

        with SessionLocal() as db:
            for loc in db.query(Location).all()[:300]:
                d = haversine_km(latitude, longitude, loc.latitude, loc.longitude)
                if d > radius_km or d < 0.5:
                    continue
                rp = (
                    db.query(RiskPrediction)
                    .filter(RiskPrediction.location_id == loc.id)
                    .order_by(desc(RiskPrediction.timestamp))
                    .first()
                )
                if rp and rp.risk_level in ("LOW", "MODERATE"):
                    alts.append(
                        AlternativeOut(
                            latitude=loc.latitude,
                            longitude=loc.longitude,
                            distance_km=round(d, 1),
                            risk_score=int(rp.risk_score),
                            risk_level=rp.risk_level,
                            name=loc.name,
                        )
                    )
                    if len(alts) >= 5:
                        break
            alts.sort(key=lambda x: (x.risk_score, x.distance_km))
    except Exception:
        pass
    return alts[:5]
