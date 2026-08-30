"""FastAPI application entrypoint - reload trigger 2026-08-27T09:55:00Z

Run with:
    uvicorn app.main:app --reload --port 8000

Or via the console script defined in pyproject.toml:
    landslide-api
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path so we can import the `ml` package
# regardless of where uvicorn is launched from.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level)
log = get_logger("app.main")

app = FastAPI(
    title="Landslide Early Warning System - NER",
    description=(
        "AI-Based Early Warning and Landslide Risk Monitoring System for the "
        "North Eastern Region of India. Decision-support prototype."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "api": settings.api_prefix,
        "health": f"{settings.api_prefix}/health",
    }


def run() -> None:
    log.info("starting_api", host=settings.api_host, port=settings.api_port, env=settings.app_env)
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "development",
    )


if __name__ == "__main__":
    run()
