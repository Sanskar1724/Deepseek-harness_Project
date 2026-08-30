"""Phase 8 sanity: the data shape the map page consumes."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.session import init_db
from app.main import app

client = TestClient(app)


def test_risk_map_returns_expected_shape():
    init_db()
    r = client.get("/api/v1/risk/map")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) >= {"count", "generated_at", "points", "thresholds", "is_synthetic"}
    assert isinstance(body["points"], list)
    assert {"low", "moderate", "high"} <= set(body["thresholds"].keys())
    assert isinstance(body["is_synthetic"], bool)
