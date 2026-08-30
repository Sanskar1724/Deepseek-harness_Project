"""TerraFM stub - heavy EO foundation, GPU, Sentinel-1/2."""
from .interface import SatelliteAIProvider, SatelliteEvidence
from app.providers.base import Point

class TerraFMProvider(SatelliteAIProvider):
    name = "terrafm"
    def get_evidence(self, point: Point) -> SatelliteEvidence:
        # TODO: MBZUAI/TerraFM needs Sentinel chip + GPU, ~1B params
        # Not for local CPU 600-train; keep stub
        from .mock import MockSatelliteAIProvider
        ev = MockSatelliteAIProvider().get_evidence(point)
        return SatelliteEvidence(**{**ev.to_dict(), "source": "terrafm_stub_cpu_fallback", "is_live": False})
