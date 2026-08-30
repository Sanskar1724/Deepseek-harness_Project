"""Provider registry.

One accessor per provider family. Cached so the same instance is reused per
process. If the configured provider is unknown, we fall back to mock and log a
warning so the operator sees the misconfiguration instead of getting silent
fake data labelled as the configured source.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import (
    LandslideProvider,
    RainfallProvider,
    SatelliteProvider,
    SoilProvider,
    TerrainProvider,
    WeatherProvider,
)
from app.providers.mock_providers import (
    MockLandslideProvider,
    MockRainfallProvider,
    MockSatelliteProvider,
    MockSoilProvider,
    MockTerrainProvider,
    MockWeatherProvider,
)
from app.providers.nasa_power import NasaPowerSoilProvider, NasaPowerTerrainProvider
from app.providers.open_meteo import OpenMeteoRainfallProvider, OpenMeteoWeatherProvider
from app.providers.open_elevation import OpenElevationTerrainProvider
from app.providers.real_landslide import RealLandslideProvider
from app.providers.real_satellite import RealSatelliteProvider

log = get_logger("app.providers")


def _select(name: str, mock_cls, real_map: dict):
    settings = get_settings()
    chosen = getattr(settings, name, "mock") or "mock"
    if chosen == "mock":
        return mock_cls()
    if chosen in real_map:
        return real_map[chosen]()
    log.warning("unknown_provider_falling_back", setting=name, requested=chosen)
    return mock_cls()


@lru_cache(maxsize=1)
def get_weather_provider() -> WeatherProvider:
    return _select("weather_provider", MockWeatherProvider, {
        "open_meteo": OpenMeteoWeatherProvider,
    })


@lru_cache(maxsize=1)
def get_rainfall_provider() -> RainfallProvider:
    return _select("rainfall_provider", MockRainfallProvider, {
        "open_meteo": OpenMeteoRainfallProvider,
    })


@lru_cache(maxsize=1)
def get_terrain_provider() -> TerrainProvider:
    return _select("terrain_provider", MockTerrainProvider, {
        "nasa_power": NasaPowerTerrainProvider,
        "open_elevation": OpenElevationTerrainProvider,
    })


@lru_cache(maxsize=1)
def get_satellite_provider() -> SatelliteProvider:
    return _select("satellite_provider", MockSatelliteProvider, {
        "real": RealSatelliteProvider,
        "real_derived": RealSatelliteProvider,
        "derived": RealSatelliteProvider,
    })


@lru_cache(maxsize=1)
def get_soil_provider() -> SoilProvider:
    return _select("soil_provider", MockSoilProvider, {
        "nasa_power": NasaPowerSoilProvider,
    })


@lru_cache(maxsize=1)
def get_landslide_provider() -> LandslideProvider:
    return _select("landslide_provider", MockLandslideProvider, {
        "real": RealLandslideProvider,
        "real_coolr": RealLandslideProvider,
        "nasa_coolr": RealLandslideProvider,
        "coolr": RealLandslideProvider,
    })
