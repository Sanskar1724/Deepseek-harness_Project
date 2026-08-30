"""Sync infrastructure (roads, hospitals, schools, bridges, villages) from OpenStreetMap.

Usage:
    python scripts/sync_osm_infrastructure.py
    python scripts/sync_osm_infrastructure.py --bbox 24.0,93.0,26.0,94.0  # custom bbox
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import init_db  # noqa: E402
from app.providers.osm_overpass import sync_infrastructure  # noqa: E402


def main() -> int:
    init_db()
    p = argparse.ArgumentParser(description="Sync infrastructure from OpenStreetMap")
    p.add_argument(
        "--bbox",
        type=str,
        default=None,
        help="Bounding box as south,west,north,east (default: NER region)",
    )
    args = p.parse_args()

    bbox = None
    if args.bbox:
        parts = [float(x) for x in args.bbox.split(",")]
        if len(parts) != 4:
            print("bbox must be south,west,north,east", file=sys.stderr)
            return 2
        bbox = {"south": parts[0], "west": parts[1], "north": parts[2], "east": parts[3]}

    count = sync_infrastructure(bbox)
    print(f"Synced {count} new infrastructure records from OpenStreetMap.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
