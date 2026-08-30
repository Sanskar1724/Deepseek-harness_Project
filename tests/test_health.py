"""Smoke test for the /api/v1/health endpoint."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "app" in body
    assert "env" in body


def test_root_returns_metadata():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "landslide-ner"
    assert body["api"] == "/api/v1"


def test_openapi_is_served():
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    spec = resp.json()
    assert "/api/v1/health" in spec["paths"]


def test_404_returns_app_error_shape():
    # Unknown routes are handled by FastAPI default; just ensure the test client
    # boots and returns the expected status. AppError shape is exercised in Phase 2+
    # once we have endpoints that raise AppError.
    resp = client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
