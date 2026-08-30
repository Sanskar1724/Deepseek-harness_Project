"""Standalone satellite experiment - Phase 4, not wired to risk_engine yet.
Choose ONE practical model: LFM2.5-VL-450M (CPU GGUF) as primary.
Usage:
  python experiments/satellite_landslide_test.py --lat 27.5829 --lon 91.8565 --provider mock
  python experiments/satellite_landslide_test.py --lat 27.5829 --lon 91.8565 --provider lfm_vlm (needs HF + llama-cpp)
"""
from __future__ import annotations

import argparse
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.providers.base import Point

PROVIDERS = {
    "mock": "app.providers.satellite_ai.mock:MockSatelliteAIProvider",
    "lfm_vlm": "app.providers.satellite_ai.landslide_vlm:LandslideVLMProvider",
    "terrafm": "app.providers.satellite_ai.terra_fm:TerraFMProvider",
    "prithvi": "app.providers.satellite_ai.prithvi:PrithviProvider",
    "indlands": "app.providers.satellite_ai.indlands:IndLandsProvider",
}

def load_provider(name: str):
    path = PROVIDERS.get(name)
    if not path:
        raise ValueError(f"unknown provider {name} choose {list(PROVIDERS)}")
    mod, cls = path.split(":")
    import importlib
    m = importlib.import_module(mod)
    return getattr(m, cls)()

def main():
    p = argparse.ArgumentParser(description="Satellite landslide standalone test")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--provider", type=str, default="mock", choices=list(PROVIDERS.keys()))
    args = p.parse_args()

    point = Point(latitude=args.lat, longitude=args.lon)
    provider = load_provider(args.provider)
    t0 = time.time()
    try:
        ev = provider.get_evidence(point)
        dt = time.time() - t0
        print(f"Provider: {ev.source} available={ev.available}")
        print(f"  landslide_probability: {ev.landslide_probability}")
        print(f"  confidence: {ev.confidence}")
        print(f"  signals: {ev.signals}")
        print(f"  is_live: {ev.is_live}")
        print(f"  inference_time: {dt:.3f}s")
        print(f"  full: {ev.to_dict()}")
    except Exception as e:
        print(f"FAILED provider={args.provider} error={e}")
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
