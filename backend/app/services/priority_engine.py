"""Emergency prioritisation engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.db.session import SessionLocal, haversine_km
from app.models import Infrastructure
from app.providers import Point
from app.services.risk_engine import RiskResult, score_point


@dataclass
class ExposedAsset:
    infra_id: int
    name: str
    type: str
    importance: int
    distance_km: float


@dataclass
class PriorityResult:
    risk_result: RiskResult
    exposed_assets: List[ExposedAsset]
    priority: str
    rationale: str


NEAR_RADIUS_KM = 5.0

type_weight = {
    "HOSPITAL": 5,
    "SCHOOL": 4,
    "BRIDGE": 4,
    "ROAD": 3,
    "VILLAGE": 3,
    "TOWN": 4,
    "POWER_LINE": 2,
    "OTHER": 1,
}


def _infra_within_radius(point, radius_km=NEAR_RADIUS_KM):
    assets = []
    with SessionLocal() as db:
        all_infra = db.query(Infrastructure).all()
        for r in all_infra:
            d = haversine_km(point.latitude, point.longitude, r.latitude, r.longitude)
            if d <= radius_km:
                assets.append(ExposedAsset(
                    infra_id=r.id,
                    name=r.name,
                    type=str(r.type.value) if hasattr(r.type, "value") else str(r.type),
                    importance=r.importance,
                    distance_km=d,
                ))
    return assets


def _compute_priority(risk, assets):
    score = risk.risk_score
    if score >= 81:
        base = 3
    elif score >= 61:
        base = 2
    else:
        base = 1
    exposure = 0
    for a in assets:
        w = type_weight.get(a.type, 1) * (a.importance or 1)
        exposure += w
    if base >= 3 or (base == 2 and exposure >= 10):
        return "P1", f"Critical risk ({score}) with high exposure ({exposure})"
    if base >= 2 or (base == 1 and exposure >= 5):
        return "P2", f"High/Moderate risk ({score}) with exposure ({exposure})"
    return "P3", f"Low risk ({score}) limited exposure ({exposure})"


def prioritize_point(point):
    risk = score_point(point)
    assets = _infra_within_radius(point)
    priority, rationale = _compute_priority(risk, assets)
    return PriorityResult(
        risk_result=risk,
        exposed_assets=assets,
        priority=priority,
        rationale=rationale,
    )
