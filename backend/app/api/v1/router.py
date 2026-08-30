"""Aggregate v1 routers."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import alerts, assess, geocode, health, locations, predictions, priority, reports, risk, sensors

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(locations.router)
api_router.include_router(predictions.router)
api_router.include_router(risk.router)
api_router.include_router(priority.router)
api_router.include_router(reports.router)
api_router.include_router(alerts.router)
api_router.include_router(sensors.router)
api_router.include_router(geocode.router)
api_router.include_router(assess.router)