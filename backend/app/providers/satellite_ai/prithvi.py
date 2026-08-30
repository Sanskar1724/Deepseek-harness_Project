"""Prithvi landslide segmentation stub."""
from .interface import SatelliteAIProvider, SatelliteEvidence
from app.providers.base import Point

class PrithviProvider(SatelliteAIProvider):
    name = "prithvi"
    def get_evidence(self, point: Point) -> SatelliteEvidence:
        # TODO: srivassid/prithvi-landslide needs HLS, GPU
        from .mock import MockSatelliteAIProvider
        ev = MockSatelliteAIProvider().get_evidence(point)
        return SatelliteEvidence(**{**ev.to_dict(), "source": "prithvi_stub", "is_live": False})
