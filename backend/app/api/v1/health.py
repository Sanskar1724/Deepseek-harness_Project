"""Liveness/readiness probe. Returns {"status": "ok"} when the API is up."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Lightweight health check used by the UI and deployment probes."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "version": "0.1.0",
    }


@router.get("/model/health")
def model_health() -> dict:
    """Model registry health: loaded model, stats, available models."""
    try:
        from ml.model_registry import health_check
        return health_check()
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/health/full")
def full_health() -> dict:
    """Full health check: API + model + DB + providers."""
    settings = get_settings()
    result = {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "version": "0.1.0",
        "components": {},
    }
    result["components"]["api"] = {"status": "ok"}
    try:
        from ml.model_registry import health_check
        mh = health_check()
        result["components"]["model"] = mh
    except Exception as e:
        result["components"]["model"] = {"status": "error", "error": str(e)}
        result["status"] = "degraded"
    try:
        from app.db.session import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["components"]["database"] = {"status": "ok"}
    except Exception as e:
        result["components"]["database"] = {"status": "error", "error": str(e)}
        result["status"] = "degraded"
    return result
