"""IndLands dataset stub - inspect, not full download."""
from .interface import SatelliteAIProvider, SatelliteEvidence
from app.providers.base import Point

class IndLandsProvider(SatelliteAIProvider):
    name = "indlands"
    def get_evidence(self, point: Point) -> SatelliteEvidence:
        # TODO: inspect https://huggingface.co/datasets/DataUploader/IndLands
        # Would load dataset.csv + DEM patches for Sikkim/Mizoram/Arunachal
        # For now return mock with source marking
        from .mock import MockSatelliteAIProvider
        ev = MockSatelliteAIProvider().get_evidence(point)
        return SatelliteEvidence(**{**ev.to_dict(), "source": "indlands_stub", "is_live": False})
