"""Provider interfaces.

Every provider returns plain Python dataclasses (never ORM rows, never raw
JSON dicts) so the rest of the codebase has a single stable contract.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class Point:
    latitude: float
    longitude: float

    def as_wkt(self) -> str:
        return f"POINT({self.longitude} {self.latitude})"


@dataclass(frozen=True)
class WeatherObservation:
    """A single moment-in-time observation at a point."""
    timestamp: datetime
    temperature_c: float = 0.0
    humidity_pct: float = 0.0
    rainfall_1h_mm: float = 0.0


@dataclass(frozen=True)
class WeatherSnapshot:
    """Aggregate the risk engine wants for one location at one moment."""
    point: Point
    observed: WeatherObservation
    forecast_24h_mm: float = 0.0
    forecast_72h_mm: float = 0.0
    rainfall_1h_mm: float = 0.0
    rainfall_6h_mm: float = 0.0
    rainfall_24h_mm: float = 0.0
    rainfall_72h_mm: float = 0.0
    source: str = "mock"
    is_synthetic: bool = True


@dataclass(frozen=True)
class TerrainAttributes:
    elevation_m: float = 0.0
    slope_deg: float = 0.0
    aspect_deg: float = 0.0
    source: str = "mock"
    is_synthetic: bool = True


@dataclass(frozen=True)
class SoilAttributes:
    soil_moisture_pct: float = 0.0
    source: str = "mock"
    is_synthetic: bool = True


@dataclass(frozen=True)
class SatelliteAttributes:
    ndvi: float = 0.0
    land_cover: str = "unknown"
    source: str = "mock"
    is_synthetic: bool = True


@dataclass(frozen=True)
class RainfallSeries:
    """Multi-window rainfall totals (mm) ending at `timestamp`."""
    point: Point
    timestamp: datetime
    rainfall_1h: float = 0.0
    rainfall_6h: float = 0.0
    rainfall_24h: float = 0.0
    rainfall_72h: float = 0.0
    forecast_24h: float = 0.0
    forecast_72h: float = 0.0
    source: str = "mock"
    is_synthetic: bool = True


@dataclass(frozen=True)
class HistoricalLandslide:
    point: Point
    event_date: datetime
    severity: int  # 1..5
    source: str = "unknown"
    description: str = ""


class WeatherProvider(ABC):
    """Returns current conditions + short-window rainfall for a point."""
    name: str = "abstract"

    @abstractmethod
    def get_snapshot(self, point: Point, *, now: Optional[datetime] = None) -> WeatherSnapshot: ...


class RainfallProvider(ABC):
    """Returns multi-window rainfall totals + forecast for a point."""
    name: str = "abstract"

    @abstractmethod
    def get_series(self, point: Point, *, now: Optional[datetime] = None) -> RainfallSeries: ...


class TerrainProvider(ABC):
    """Returns static terrain attributes for a point."""
    name: str = "abstract"

    @abstractmethod
    def get_terrain(self, point: Point) -> TerrainAttributes: ...


class SatelliteProvider(ABC):
    """Returns land-cover / NDVI for a point."""
    name: str = "abstract"

    @abstractmethod
    def get_attributes(self, point: Point) -> SatelliteAttributes: ...


class SoilProvider(ABC):
    """Returns soil-moisture for a point."""
    name: str = "abstract"

    @abstractmethod
    def get_soil(self, point: Point, *, now: Optional[datetime] = None) -> SoilAttributes: ...


class LandslideProvider(ABC):
    """Returns historical landslide events near a point (or globally)."""
    name: str = "abstract"

    @abstractmethod
    def list_events(
        self,
        *,
        near: Optional[Point] = None,
        radius_km: Optional[float] = None,
        since: Optional[datetime] = None,
    ) -> List[HistoricalLandslide]: ...
