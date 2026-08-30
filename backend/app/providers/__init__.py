"""Replaceable data providers.

Each provider family (weather, rainfall, terrain, satellite, landslide, soil)
has a base interface and one or more implementations. The active implementation
is selected at runtime from settings (WEATHER_PROVIDER=mock|open_meteo|...).

This honours master prompt Rule 2: never claim fake live data is real. The mock
provider is the default; real providers are stubs that explicitly say so when
their API key is missing.
"""
from app.providers.base import (  # noqa: F401
    LandslideProvider,
    Point,
    RainfallProvider,
    SatelliteProvider,
    SoilProvider,
    TerrainProvider,
    WeatherObservation,
    WeatherProvider,
    WeatherSnapshot,
)
from app.providers.registry import (  # noqa: F401
    get_landslide_provider,
    get_rainfall_provider,
    get_satellite_provider,
    get_soil_provider,
    get_terrain_provider,
    get_weather_provider,
)
