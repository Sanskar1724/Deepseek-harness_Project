"""Phase 2 smoke test.

Run after `alembic upgrade head`:
    python scripts/check_db.py

Verifies:
  - engine can connect (SpatiaLite extension loaded)
  - all expected tables exist
  - inserts + reads work
  - a spatial distance query works (ST_Distance is the lowest-common-denominator
    between SQLite+SpatiaLite and PostGIS).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

from sqlalchemy import func, select, text

from app.db.session import SessionLocal, engine, init_db
from app.models import (
    FieldReport,
    Infrastructure,
    InfrastructureType,
    LandslideEvent,
    Location,
    ReportStatus,
    ReportType,
    RiskPrediction,
    WeatherData,
)

EXPECTED_TABLES = {
    "locations",
    "weather_data",
    "landslide_events",
    "risk_predictions",
    "field_reports",
    "infrastructure",
    "sensors",
    "sensor_readings",
    "alerts",
    "alert_deliveries",
    "model_registry",
}


def _ensure_spatialite_loaded() -> None:
    """Touch a geometry-using query to confirm SpatiaLite is available."""
    with engine.connect() as conn:
        # Make a harmless spatial query that needs SpatiaLite.
        if conn.dialect.name == "sqlite":
            row = conn.execute(text("SELECT ST_AsText(ST_GeomFromText('POINT(0 0)', 4326))")).scalar()
            assert row == "POINT(0 0)", f"unexpected spatialite response: {row!r}"


def check_tables() -> None:
    inspector_tables = set()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
            if conn.dialect.name == "sqlite"
            else text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
        ).all()
        for (name,) in rows:
            inspector_tables.add(name)

    missing = EXPECTED_TABLES - inspector_tables
    if missing:
        raise SystemExit(f"missing tables: {sorted(missing)}")
    print(f"[ok] all {len(EXPECTED_TABLES)} expected tables present")


def check_crud_and_spatial() -> None:
    init_db()  # idempotent
    with SessionLocal() as db:
        # Wipe smoke-test rows so this is re-runnable.
        db.query(FieldReport).filter(FieldReport.client_id == "smoke-client-id").delete()
        db.query(WeatherData).filter(WeatherData.source == "smoke").delete()
        db.query(RiskPrediction).filter(RiskPrediction.model_version == "smoke").delete()
        db.query(Infrastructure).filter(Infrastructure.name == "Smoke Bridge").delete()
        db.query(LandslideEvent).filter(LandslideEvent.source == "smoke").delete()
        loc = db.query(Location).filter(Location.name == "Smoke Hill").one_or_none()
        if loc is not None:
            db.delete(loc)
        db.commit()

        loc = Location(
            name="Smoke Hill",
            state="Manipur",
            district="Imphal West",
            latitude=24.8170,
            longitude=93.9368,
            geom="SRID=4326;POINT(93.9368 24.8170)",
        )
        db.add(loc)
        db.commit()
        db.refresh(loc)
        assert loc.id is not None
        print(f"[ok] inserted location id={loc.id}")

        # Update
        loc.elevation_m = 1200.0
        db.commit()
        reread = db.get(Location, loc.id)
        assert reread is not None and reread.elevation_m == 1200.0
        print("[ok] update + read")

        # Weather row
        w = WeatherData(
            location_id=loc.id,
            timestamp=datetime.now(timezone.utc),
            rainfall_24h=42.0,
            source="smoke",
        )
        db.add(w)
        db.commit()

        # Risk prediction
        rp = RiskPrediction(
            location_id=loc.id,
            timestamp=datetime.now(timezone.utc),
            risk_score=72.0,
            risk_level="HIGH",
            model_version="smoke",
        )
        db.add(rp)
        db.commit()

        # Field report (offline-friendly: client_id unique)
        fr = FieldReport(
            client_id="smoke-client-id",
            report_type=ReportType.CRACK,
            description="smoke test crack",
            timestamp=datetime.now(timezone.utc),
            latitude=24.8170,
            longitude=93.9368,
            geom="SRID=4326;POINT(93.9368 24.8170)",
            status=ReportStatus.RECEIVED,
        )
        db.add(fr)
        db.commit()

        # Infrastructure
        infra = Infrastructure(
            name="Smoke Bridge",
            type=InfrastructureType.BRIDGE,
            importance=4,
            latitude=24.8175,
            longitude=93.9370,
            geom="SRID=4326;POINT(93.9370 24.8175)",
        )
        db.add(infra)
        db.commit()

        # Spatial query: distance from the location to the bridge, in degrees.
        # We use ST_Distance because it works on both SpatiaLite and PostGIS.
        d = db.execute(
            text(
                "SELECT ST_Distance(l.geom, i.geom) "
                "FROM locations l, infrastructure i "
                "WHERE l.id = :lid AND i.name = :name"
            ),
            {"lid": loc.id, "name": "Smoke Bridge"},
        ).scalar()
        print(f"[ok] spatial distance query returned {d}")
        assert d is not None and float(d) >= 0.0

        # Cleanup
        db.delete(fr); db.delete(rp); db.delete(w); db.delete(infra); db.delete(loc)
        db.commit()
        print("[ok] cleanup")


def main() -> int:
    try:
        _ensure_spatialite_loaded()
    except Exception as e:
        print(f"[FAIL] spatialite not loaded: {e}", file=sys.stderr)
        return 2
    check_tables()
    check_crud_and_spatial()
    print("[ok] phase 2 smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
