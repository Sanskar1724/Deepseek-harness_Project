"""Alert engine: creates alerts when risk crosses thresholds."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models import Alert, AlertDelivery, RiskPrediction
from app.services.risk_engine import LEVEL_CRITICAL, LEVEL_HIGH, RiskResult, score_point
from app.providers import Point

log = get_logger("app.alerts")

ALERT_SEVERITY = {
    LEVEL_CRITICAL: "CRITICAL",
    LEVEL_HIGH: "HIGH",
}


@dataclass
class AlertResult:
    alert_id: Optional[int]
    created: bool
    message: str


def _render_message(risk: RiskResult, lang: str = "en") -> str:
    ts = risk.timestamp.strftime("%Y-%m-%d %H:%M UTC")
    templates = {
        "en": f"Landslide risk {risk.risk_level} ({risk.risk_score}/100) at {ts}. Take precautions.",
        "hi": f"भूस्खलन जोखिम {risk.risk_level} ({risk.risk_score}/100) {ts} पर। सावधानी बरतें।",
        "as": f"ভূস্খলন ৰিস্ক {risk.risk_level} ({risk.risk_score}/100) {ts}ত। সাৱধানতা লওক।",
    }
    return templates.get(lang, templates["en"])

def _deliver(alert_id: int, channel: str, recipient: str, message: str) -> str:
    """Stub delivery - logs for now, returns provider_response."""
    if channel == "log":
        log.info("alert_delivered", channel=channel, recipient=recipient)
        return f"logged:{alert_id}"
    if channel == "sms":
        log.info("alert_sms_stub", recipient=recipient)
        return f"sms_stub:{alert_id}"
    if channel == "push":
        log.info("alert_push_stub", recipient=recipient)
        return f"push_stub:{alert_id}"
    return f"unknown:{alert_id}"

def check_and_create_alerts(risk: RiskResult, point: Point | None = None) -> List[AlertResult]:
    """Call after every risk prediction. Creates alert if level is HIGH or CRITICAL."""
    if risk.risk_level not in ALERT_SEVERITY:
        return []
    severity = ALERT_SEVERITY[risk.risk_level]
    # Resolve lat/lon from risk or explicit point
    lat = risk.latitude if risk.latitude is not None else (point.latitude if point else None)
    lon = risk.longitude if risk.longitude is not None else (point.longitude if point else None)
    with SessionLocal() as db:
        loc_id = None
        rp = None
        if lat is not None and lon is not None:
            from sqlalchemy import text

            row = db.execute(
                text("SELECT id FROM locations WHERE latitude=:lat AND longitude=:lon LIMIT 1"),
                {"lat": lat, "lon": lon},
            ).first()
            loc_id = row[0] if row else None
            if loc_id is not None:
                rp = (
                    db.query(RiskPrediction)
                    .filter(RiskPrediction.location_id == loc_id)
                    .order_by(RiskPrediction.timestamp.desc())
                    .first()
                )
        # Fallback: try to find most recent RiskPrediction for this model_version
        if loc_id is None and risk.model_version != "none":
            rp = (
                db.query(RiskPrediction)
                .filter(RiskPrediction.model_version == risk.model_version)
                .order_by(RiskPrediction.timestamp.desc())
                .first()
            )
            if rp:
                loc_id = rp.location_id
        if loc_id is None:
            # Create a placeholder location if needed for ad-hoc predictions
            # (so alerts can still be tracked). Use the point coords if available.
            if lat is not None and lon is not None:
                from app.models import Location

                loc = Location(
                    name=f"({lat:.4f}, {lon:.4f})",
                    state="unknown",
                    district="unknown",
                    latitude=lat,
                    longitude=lon,
                )
                db.add(loc)
                db.commit()
                db.refresh(loc)
                loc_id = loc.id
            else:
                return []
        # Check if an alert already exists for this location+level in last 6h
        existing = db.query(Alert).filter(
            Alert.location_id == loc_id,
            Alert.severity == severity,
            Alert.created_at >= datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=6),
        ).first()
        if existing:
            return [AlertResult(alert_id=existing.id, created=False, message="already exists")]
        alert = Alert(
            risk_prediction_id=rp.id if rp else None,
            location_id=loc_id,
            severity=severity,
            message=_render_message(risk, "en"),
            language="en",
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert); db.commit(); db.refresh(alert)
        # Deliver via configured channels
        channels = ["log"]  # In future: read from settings
        for ch in channels:
            delivery = AlertDelivery(
                alert_id=alert.id,
                channel=ch,
                recipient="authority_dashboard",
                status="sent",
                provider_response=_deliver(alert.id, ch, "authority_dashboard", alert.message),
                created_at=datetime.now(timezone.utc),
            )
            db.add(delivery)
        db.commit()
        log.info("alert_created", alert_id=alert.id, severity=severity, loc=loc_id)
        return [AlertResult(alert_id=alert.id, created=True, message=alert.message)]