"""End-to-end test: provider -> risk -> priority -> alert -> map."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_full_pipeline():
    init_db()
    # 1. Create a location
    r = client.post("/api/v1/locations", json={
        "name": "E2E Test", "state": "Manipur", "district": "Imphal",
        "latitude": 25.0, "longitude": 93.0,
    })
    assert r.status_code == 201
    loc_id = r.json()["id"]
    # 2. Get a prediction
    r = client.post("/api/v1/predictions", json={"latitude": 25.0, "longitude": 93.0})
    assert r.status_code == 200
    assert "risk_score" in r.json()
    # 3. Get risk for that location
    r = client.get(f"/api/v1/risk/{loc_id}")
    assert r.status_code == 200
    # 4. Get risk map
    r = client.get("/api/v1/risk/map")
    assert r.status_code == 200
    assert "points" in r.json()
    # 5. Get priority
    r = client.get("/api/v1/priority/25.0/93.0")
    assert r.status_code == 200
    assert "priority" in r.json()
    # 6. Submit a report
    r = client.post("/api/v1/reports", json={
        "client_id": "e2e-test-1", "report_type": "CRACK",
        "description": "E2E", "timestamp": "2024-06-15T12:00:00Z",
        "latitude": 25.0, "longitude": 93.0,
    })
    assert r.status_code == 201
    # 7. List reports
    r = client.get("/api/v1/reports")
    assert r.status_code == 200
    assert any(rep["client_id"] == "e2e-test-1" for rep in r.json())
    # 8. List alerts
    r = client.get("/api/v1/alerts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    # 9. Ingest sensor data
    r = client.post("/api/v1/sensors/data", json={
        "sensor_id": "E2E-SM-1", "kind": "soil_moisture",
        "latitude": 25.0, "longitude": 93.0,
        "timestamp": "2024-06-15T12:00:00Z", "soil_moisture": 72.5,
    })
    assert r.status_code == 201


def test_duplicate_report_is_idempotent():
    payload = {
        "client_id": "dup-test-1", "report_type": "OTHER",
        "description": "dup", "timestamp": "2024-06-15T12:00:00Z",
        "latitude": 26.0, "longitude": 91.0,
    }
    r1 = client.post("/api/v1/reports", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/reports", json=payload)
    assert r2.status_code in (200, 201)  # idempotent
    assert r2.json()["client_id"] == "dup-test-1"


def test_invalid_lat_lon_rejected():
    r = client.post("/api/v1/predictions", json={"latitude": 99, "longitude": 0})
    assert r.status_code == 422
    r = client.post("/api/v1/reports", json={
        "client_id": "bad-1", "report_type": "OTHER",
        "timestamp": "2024-06-15T12:00:00Z",
        "latitude": 200, "longitude": 0,
    })
    assert r.status_code == 422