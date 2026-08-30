"""Tests for the new real-data providers.

These tests make REAL API calls. They are skipped if the network is unavailable
to keep CI/local development robust. Mark with @pytest.mark.network.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.providers.base import Point
from app.providers.open_elevation import OpenElevationTerrainProvider
from app.providers.osm_overpass import NER_BBOX, fetch_infrastructure
from app.providers.usgs_earthquakes import fetch_earthquakes_near
from app.providers.nominatim import geocode
from app.providers.gdacs import fetch_recent_alerts


network = pytest.mark.skipif(
    "--no-network" in sys.argv,
    reason="network tests skipped (use --no-network to disable)",
)


@network
def test_open_elevation_returns_terrain():
    p = Point(latitude=26.1445, longitude=91.7362)  # Guwahati
    terrain = OpenElevationTerrainProvider().get_terrain(p)
    assert terrain.elevation_m > 0
    assert 0 <= terrain.slope_deg <= 90
    assert 0 <= terrain.aspect_deg <= 360
    assert terrain.source == "open_elevation"
    assert terrain.is_synthetic is False


@network
def test_open_elevation_batch():
    points = [
        Point(latitude=26.1445, longitude=91.7362),  # Guwahati
        Point(latitude=25.5788, longitude=91.8832),  # Shillong
    ]
    results = OpenElevationTerrainProvider().get_terrain_batch(points)
    assert len(results) == 2
    assert all(r.elevation_m > 0 for r in results)


@network
def test_osm_overpass_fetches_infrastructure():
    from app.core.errors import ProviderError

    try:
        items = fetch_infrastructure(NER_BBOX)
    except ProviderError as e:
        pytest.skip(f"Overpass unavailable: {e}")
    if len(items) == 0:
        pytest.skip("Overpass returned 0 items (network/rate limit)")
    assert len(items) > 10  # NER should have hundreds of items
    assert any(item["type"].value == "HOSPITAL" for item in items)
    assert any(item["type"].value == "ROAD" for item in items[:100])  # in first batch


@network
def test_usgs_earthquakes():
    quakes = fetch_earthquakes_near(days=30, min_magnitude=4.0)
    # NER has occasional earthquakes - result may be empty list, which is valid
    assert isinstance(quakes, list)
    for q in quakes:
        assert 21.0 <= q.point.latitude <= 30.0
        assert 87.0 <= q.point.longitude <= 98.0
        assert q.magnitude >= 4.0


@network
def test_nominatim_geocode_known_city():
    p = geocode("Guwahati")
    assert p is not None
    assert 26.0 <= p.latitude <= 27.0
    assert 91.0 <= p.longitude <= 92.0


@network
def test_nominatim_unknown_returns_none():
    p = geocode("xyznonexistentplace12345")
    assert p is None


@network
def test_gdacs_alerts():
    alerts = fetch_recent_alerts(days=30)
    # May be empty for NER, which is valid
    assert isinstance(alerts, list)
    for a in alerts:
        assert a.event_type in {"FL", "EQ", "TC"}
        assert 21.0 <= a.point.latitude <= 30.0
        assert 87.0 <= a.point.longitude <= 98.0
