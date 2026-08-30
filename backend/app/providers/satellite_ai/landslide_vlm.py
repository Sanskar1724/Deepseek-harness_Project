"""LFM2.5-VL-450M landslide VLM stub - CPU GGUF."""
from .interface import SatelliteAIProvider, SatelliteEvidence
from app.providers.base import Point

class LandslideVLMProvider(SatelliteAIProvider):
    name = "lfm_vlm"
    def get_evidence(self, point: Point) -> SatelliteEvidence:
        # TODO: Sciamlab/LFM2.5-VL-450M-landslide-GGUF needs image + prompt
        # Would call llama-cpp with prompt: "vegetation stress, bare soil..."
        # Stub returns mock with correct source
        from .mock import MockSatelliteAIProvider
        ev = MockSatelliteAIProvider().get_evidence(point)
        return SatelliteEvidence(**{**ev.to_dict(), "source": "lfm_vlm_stub", "is_live": False})
