"""Interface for satellite AI evidence (additive, optional)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional

from app.providers.base import Point


@dataclass(frozen=True)
class SatelliteEvidence:
    """Structured evidence from satellite/remote-sensing AI."""
    available: bool = True
    landslide_probability: float = 0.0  # 0-1
    confidence: float = 0.0  # 0-1 overall satellite confidence
    vegetation_stress: Optional[float] = None
    wetness: Optional[float] = None
    bare_soil: Optional[float] = None
    erosion: Optional[float] = None
    terrain_signal: Optional[float] = None
    water_accumulation: Optional[float] = None
    steep_terrain: Optional[float] = None
    source: str = "mock_satellite_ai"
    is_live: bool = False
    signals: Dict[str, float] | None = None

    def to_dict(self) -> Dict:
        return {
            "available": self.available,
            "landslide_probability": round(self.landslide_probability, 4),
            "confidence": round(self.confidence, 4),
            "vegetation_stress": self.vegetation_stress,
            "wetness": self.wetness,
            "bare_soil": self.bare_soil,
            "erosion": self.erosion,
            "terrain_signal": self.terrain_signal,
            "water_accumulation": self.water_accumulation,
            "steep_terrain": self.steep_terrain,
            "source": self.source,
            "is_live": self.is_live,
            "signals": self.signals or {},
        }


class SatelliteAIProvider(ABC):
    name: str = "abstract_satellite_ai"

    @abstractmethod
    def get_evidence(self, point: Point) -> SatelliteEvidence:
        """Return satellite evidence for point. Must never raise - return available=False on failure."""
        ...
