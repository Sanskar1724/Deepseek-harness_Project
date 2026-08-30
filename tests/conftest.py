"""Pytest configuration. Adds the project to sys.path and provides a fresh DB fixture."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Make `app` importable when running `pytest` from the repo root.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import pytest


@pytest.fixture(scope="session", autouse=True)
def _isolated_db():
    """Point the app at a throwaway SQLite file for the test session."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp.name}"
    # Force the cached settings to reload with the new URL.
    from app.core import config as _config  # noqa: WPS433

    _config.get_settings.cache_clear()  # type: ignore[attr-defined]
    # Recreate engine/SessionLocal so they pick up the new DATABASE_URL
    from sqlalchemy import create_engine  # noqa: WPS433
    from sqlalchemy.orm import sessionmaker  # noqa: WPS433

    import app.db.session as _session  # noqa: WPS433

    settings = _config.get_settings()
    url = settings.database_url
    if url.startswith("sqlite"):
        new_engine = create_engine(url, future=True, connect_args={"check_same_thread": False})
    else:
        new_engine = create_engine(url, future=True, pool_pre_ping=True)
    _session.engine = new_engine  # type: ignore[attr-defined]
    _session.SessionLocal = sessionmaker(bind=new_engine, autoflush=False, autocommit=False, future=True)  # type: ignore[attr-defined]
    yield
    try:
        new_engine.dispose()
    except Exception:
        pass
    try:
        os.unlink(tmp.name)
    except (FileNotFoundError, PermissionError):
        pass
