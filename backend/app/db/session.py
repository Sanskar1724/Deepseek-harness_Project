"""Engine + session factory.

This version does NOT use SpatiaLite. Geometry is stored as plain latitude
and longitude Float columns. For real spatial SQL, migrate to PostgreSQL+PostGIS.
"""
from __future__ import annotations

from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _make_engine() -> Engine:
    url = settings.database_url
    if _is_sqlite(url):
        engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    else:
        engine = create_engine(url, future=True, pool_pre_ping=True)
    return engine


engine: Engine = _make_engine()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a SQLAlchemy session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Used in tests + emergency bootstrap."""
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km (used in place of PostGIS ST_Distance)."""
    import math
    R = 6371.0
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))
