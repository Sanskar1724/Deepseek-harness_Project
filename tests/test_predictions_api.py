"""Phase 7: prediction + locations + risk APIs."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app

client = TestClient(app)


def _setup():
    init_db()


def test_create_location_and_predict():
    _setup()
    r = client.post(
        "/api/v1/locations",
        json={
            "name": "Test Hill",
            "state": "Manipur",
            "district": "Imphal West",
            "latitude": 24.817,
            "longitude": 93.937,
        },
    )
    assert r.status_code == 201, r.text
    loc = r.json()
    assert loc["id"] > 0

    r = client.post(
        "/api/v1/predictions",
        json={"latitude": 24.817, "longitude": 93.937},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "risk_score" in body and 0 <= body["risk_score"] <= 100
    assert body["risk_level"] in {"LOW", "MODERATE", "HIGH", "CRITICAL"}
    assert "model_version" in body
    assert "is_synthetic" in body


def test_predict_validation():
    r = client.post("/api/v1/predictions", json={"latitude": 99, "longitude": 0})
    assert r.status_code == 422


def test_latest_for_location_404():
    _setup()
    r = client.get("/api/v1/risk/9999999")
    assert r.status_code == 404


def test_map_endpoint_shape():
    _setup()
    r = client.get("/api/v1/risk/map")
    assert r.status_code == 200
    body = r.json()
    for k in ("count", "generated_at", "points", "thresholds", "is_synthetic"):
        assert k in body
    assert body["count"] == len(body["points"])
    assert set(body["thresholds"].keys()) == {"low", "moderate", "high"}
