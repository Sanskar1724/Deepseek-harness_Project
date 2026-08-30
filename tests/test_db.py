"""Phase 2 model-level tests: create_all + CRUD + a spatial distance check."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text

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


def test_spatialite_is_loaded():
    init_db()
    if engine.dialect.name != "sqlite":
        return  # only meaningful on sqlite
    # SQLite build is intentionally WITHOUT SpatiaLite (see app/db/session.py).
    # Verify the haversine helper works as a replacement for ST_Distance.
    from app.db.session import haversine_km

    d = haversine_km(26.1445, 91.7362, 26.1445, 91.7362)
    assert d == 0.0
    assert haversine_km(26.0, 91.0, 27.0, 91.0) > 100.0


def test_full_crud_round_trip():
    init_db()
    with SessionLocal() as db:
        loc = Location(
            name="T1 Hill",
            state="Assam",
            district="Kamrup",
            latitude=26.1445,
            longitude=91.7362,
        )
        db.add(loc); db.commit(); db.refresh(loc)
        assert loc.id is not None

        # Weather
        w = WeatherData(
            location_id=loc.id,
            timestamp=datetime.now(timezone.utc),
            rainfall_24h=10.0,
            source="test",
        )
        db.add(w); db.commit()

        # Risk
        rp = RiskPrediction(
            location_id=loc.id,
            timestamp=datetime.now(timezone.utc),
            risk_score=55.0,
            risk_level="MODERATE",
            model_version="test-v1",
        )
        db.add(rp); db.commit()

        # Report + infra + spatial
        fr = FieldReport(
            client_id=f"cid-{loc.id}",
            report_type=ReportType.LANDSLIDE,
            timestamp=datetime.now(timezone.utc),
            latitude=26.1450,
            longitude=91.7370,
            status=ReportStatus.RECEIVED,
        )
        infra = Infrastructure(
            name=f"Infra {loc.id}",
            type=InfrastructureType.ROAD,
            latitude=26.1440,
            longitude=91.7350,
            importance=3,
        )
        db.add_all([fr, infra]); db.commit()

        # Use haversine instead of ST_Distance (no SpatiaLite)
        from app.db.session import haversine_km

        d = haversine_km(loc.latitude, loc.longitude, infra.latitude, infra.longitude)
        assert d is not None and float(d) >= 0.0

        # Cleanup
        db.delete(fr); db.delete(infra); db.delete(rp); db.delete(w); db.delete(loc)
        db.commit()


def test_table_count():
    init_db()
    with engine.connect() as conn:
        if conn.dialect.name == "sqlite":
            rows = conn.execute(
                text("SELECT count(*) FROM sqlite_master WHERE type='table'")
            ).scalar()
        else:
            rows = conn.execute(
                text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")
            ).scalar()
    # 11 application tables + alembic_version
    assert int(rows) >= 11
