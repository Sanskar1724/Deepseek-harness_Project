"""Phase 3 provider tests: mock providers are deterministic + clearly synthetic."""
from __future__ import annotations

from datetime import datetime, timezone

from app.providers.base import Point
from app.providers.mock_providers import (
    MockLandslideProvider,
    MockRainfallProvider,
    MockSatelliteProvider,
    MockSoilProvider,
    MockTerrainProvider,
    MockWeatherProvider,
)
from app.providers.registry import (
    get_landslide_provider,
    get_rainfall_provider,
    get_satellite_provider,
    get_soil_provider,
    get_terrain_provider,
    get_weather_provider,
)


def test_mock_weather_is_synthetic_and_deterministic():
    p = Point(latitude=26.1445, longitude=91.7362)
    fixed = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    a = MockWeatherProvider().get_snapshot(p, now=fixed)
    b = MockWeatherProvider().get_snapshot(p, now=fixed)
    assert a.source == "mock" and a.is_synthetic is True
    assert (a.rainfall_24h_mm, a.forecast_72h_mm) == (b.rainfall_24h_mm, b.forecast_72h_mm)


def test_mock_terrain_ranges_are_ner_reasonable():
    p = Point(latitude=25.5, longitude=91.5)
    t = MockTerrainProvider().get_terrain(p)
    assert 100.0 <= t.elevation_m <= 4000.0
    assert 0.0 <= t.slope_deg <= 60.0
    assert 0.0 <= t.aspect_deg <= 360.0
    assert t.is_synthetic is True


def test_mock_satellite_ndvi_in_range():
    p = Point(latitude=26.0, longitude=91.0)
    s = MockSatelliteProvider().get_attributes(p)
    assert 0.0 <= s.ndvi <= 1.0
    assert s.land_cover in {
        "forest", "deciduous_forest", "evergreen_forest", "shrubland",
        "grassland", "cropland", "bare_soil", "built_up", "water",
    }


def test_mock_soil_rainfall_pairs_with_hour():
    p = Point(latitude=26.0, longitude=91.0)
    a = MockSoilProvider().get_soil(p, now=datetime(2024, 6, 1, tzinfo=timezone.utc))
    b = MockSoilProvider().get_soil(p, now=datetime(2024, 6, 1, tzinfo=timezone.utc))
    assert a.soil_moisture_pct == b.soil_moisture_pct  # day-aligned deterministic


def test_mock_landslide_events_around_near():
    p = Point(latitude=26.0, longitude=91.0)
    events = MockLandslideProvider().list_events(near=p)
    assert 1 <= len(events) <= 20
    assert all(e.source == "mock" for e in events)


def test_registry_returns_mock_by_default():
    # Default settings in .env.example pick mock for everything.
    assert get_weather_provider().name == "mock"
    assert get_rainfall_provider().name == "mock"
    assert get_terrain_provider().name == "mock"
    assert get_satellite_provider().name == "mock"
    assert get_soil_provider().name == "mock"
    assert get_landslide_provider().name == "mock"
