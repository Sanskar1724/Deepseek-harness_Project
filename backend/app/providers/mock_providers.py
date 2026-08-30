"""Deterministic mock providers.

These are the default in .env.example and they are loud about being synthetic:
every return value has is_synthetic=True and source="mock". The risk engine
and UI inspect this and surface a DEMO banner.

The values are seeded by (lat, lon) so the same point always returns the same
number, which makes the demo reproducible.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from app.providers.base import (
    HistoricalLandslide,
    LandslideProvider,
    Point,
    RainfallProvider,
    RainfallSeries,
    SatelliteAttributes,
    SatelliteProvider,
    SoilAttributes,
    SoilProvider,
    TerrainAttributes,
    TerrainProvider,
    WeatherObservation,
    WeatherProvider,
    WeatherSnapshot,
)


def _seeded_unit(*parts: object) -> float:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64


def _normalised(value: float, lo: float, hi: float) -> float:
    return lo + (hi - lo) * value


class MockWeatherProvider(WeatherProvider):
    name = "mock"

    def get_snapshot(self, point: Point, *, now: Optional[datetime] = None) -> WeatherSnapshot:
        now = now or datetime.now(timezone.utc)
        hour = int(now.timestamp()) // 3600
        u = _seeded_unit("wx", point.latitude, point.longitude, hour)
        v = _seeded_unit("wx2", point.latitude, point.longitude, hour)
        rain_1h = _normalised(v, 0.0, 30.0) if u > 0.85 else _normalised(v, 0.0, 5.0)
        return WeatherSnapshot(
            point=point,
            observed=WeatherObservation(
                timestamp=now,
                temperature_c=_normalised(u, 12.0, 32.0),
                humidity_pct=_normalised(v, 40.0, 95.0),
                rainfall_1h_mm=rain_1h,
            ),
            forecast_24h_mm=_normalised(u, 5.0, 60.0),
            forecast_72h_mm=_normalised(v, 15.0, 150.0),
            rainfall_1h_mm=rain_1h,
            rainfall_6h_mm=rain_1h * 3 + _normalised(u, 0.0, 10.0),
            rainfall_24h_mm=rain_1h * 8 + _normalised(v, 0.0, 30.0),
            rainfall_72h_mm=rain_1h * 18 + _normalised(u, 0.0, 80.0),
            source="mock",
            is_synthetic=True,
        )


class MockRainfallProvider(RainfallProvider):
    name = "mock"

    def get_series(self, point: Point, *, now: Optional[datetime] = None) -> RainfallSeries:
        now = now or datetime.now(timezone.utc)
        wx = MockWeatherProvider().get_snapshot(point, now=now)
        return RainfallSeries(
            point=point,
            timestamp=now,
            rainfall_1h=wx.rainfall_1h_mm,
            rainfall_6h=wx.rainfall_6h_mm,
            rainfall_24h=wx.rainfall_24h_mm,
            rainfall_72h=wx.rainfall_72h_mm,
            forecast_24h=wx.forecast_24h_mm,
            forecast_72h=wx.forecast_72h_mm,
            source="mock",
            is_synthetic=True,
        )


class MockTerrainProvider(TerrainProvider):
    name = "mock"

    def get_terrain(self, point: Point) -> TerrainAttributes:
        u = _seeded_unit("ter", point.latitude, point.longitude)
        v = _seeded_unit("ter2", point.latitude, point.longitude)
        return TerrainAttributes(
            elevation_m=_normalised(u, 200.0, 3000.0),
            slope_deg=_normalised(v, 8.0, 45.0),
            aspect_deg=_normalised(_seeded_unit("asp", point.latitude, point.longitude), 0.0, 360.0),
            source="mock",
            is_synthetic=True,
        )


class MockSatelliteProvider(SatelliteProvider):
    name = "mock"
    _LAND_COVERS = [
        "forest",
        "deciduous_forest",
        "evergreen_forest",
        "shrubland",
        "grassland",
        "cropland",
        "bare_soil",
        "built_up",
        "water",
    ]

    def get_attributes(self, point: Point) -> SatelliteAttributes:
        u = _seeded_unit("sat", point.latitude, point.longitude)
        idx = int(_seeded_unit("satlc", point.latitude, point.longitude) * len(self._LAND_COVERS))
        idx = min(idx, len(self._LAND_COVERS) - 1)
        return SatelliteAttributes(
            ndvi=_normalised(u, 0.1, 0.85),
            land_cover=self._LAND_COVERS[idx],
            source="mock",
            is_synthetic=True,
        )


class MockSoilProvider(SoilProvider):
    name = "mock"

    def get_soil(self, point: Point, *, now: Optional[datetime] = None) -> SoilAttributes:
        now = now or datetime.now(timezone.utc)
        day = int(now.timestamp()) // 86400
        u = _seeded_unit("soil", point.latitude, point.longitude, day)
        return SoilAttributes(
            soil_moisture_pct=_normalised(u, 15.0, 85.0),
            source="mock",
            is_synthetic=True,
        )


class MockLandslideProvider(LandslideProvider):
    name = "mock"

    def list_events(
        self,
        *,
        near: Optional[Point] = None,
        radius_km: Optional[float] = None,
        since: Optional[datetime] = None,
    ) -> List[HistoricalLandslide]:
        events: List[HistoricalLandslide] = []
        base = near or Point(latitude=26.0, longitude=91.0)
        for i in range(5):
            u = _seeded_unit("ls", base.latitude, base.longitude, i)
            v = _seeded_unit("ls2", base.latitude, base.longitude, i)
            dlat = (u - 0.5) * 0.5
            dlon = (v - 0.5) * 0.5
            events.append(
                HistoricalLandslide(
                    point=Point(latitude=base.latitude + dlat, longitude=base.longitude + dlon),
                    event_date=datetime(2023, 6, 1, tzinfo=timezone.utc) - timedelta(days=int(u * 600)),
                    severity=int(_seeded_unit("sev", i) * 5) + 1,
                    source="mock",
                    description=f"Synthetic historical event #{i}",
                )
            )
        if since is not None:
            events = [e for e in events if e.event_date >= since]
        return events
