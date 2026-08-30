"""Mock satellite AI - deterministic, fast, no HF/GPU, fully testable."""
from __future__ import annotations

import hashlib
from typing import Dict

from app.providers.base import Point
from .interface import SatelliteAIProvider, SatelliteEvidence


def _h(key: str, point: Point) -> float:
    h = hashlib.sha256(f"{key}|{point.latitude:.4f}|{point.longitude:.4f}".encode()).digest()
    return int.from_bytes(h[:8], "big") / 2**64


class MockSatelliteAIProvider(SatelliteAIProvider):
    name = "mock_satellite_ai"

    def get_evidence(self, point: Point) -> SatelliteEvidence:
        # Deterministic per location, no network, <1ms
        # High-risk NER terrain (Tawang etc.) gets higher signals via hash
        veg = 0.2 + _h("veg", point) * 0.6
        wet = 0.25 + _h("wet", point) * 0.6
        bare = _h("bare", point) * 0.5
        eros = _h("eros", point) * 0.5
        steep = 0.3 + _h("steep", point) * 0.6
        terr = (steep + veg) / 2
        water = _h("water", point) * 0.6
        # Landslide prob correlates with steep+wet+bare
        prob = max(0.0, min(1.0, 0.15 + 0.4 * steep + 0.3 * wet + 0.2 * bare + 0.1 * eros - 0.1 * (1 - veg)))
        conf = 0.75 + _h("conf", point) * 0.2  # 0.75-0.95
        signals: Dict[str, float] = {
            "vegetation_stress": round(veg, 3),
            "wetness": round(wet, 3),
            "bare_soil": round(bare, 3),
            "erosion": round(eros, 3),
            "terrain_signal": round(terr, 3),
            "water_accumulation": round(water, 3),
            "steep_terrain": round(steep, 3),
        }
        return SatelliteEvidence(
            available=True,
            landslide_probability=round(prob, 4),
            confidence=round(conf, 4),
            vegetation_stress=round(veg, 3),
            wetness=round(wet, 3),
            bare_soil=round(bare, 3),
            erosion=round(eros, 3),
            terrain_signal=round(terr, 3),
            water_accumulation=round(water, 3),
            steep_terrain=round(steep, 3),
            source="mock_satellite_ai",
            is_live=False,
            signals=signals,
        )
