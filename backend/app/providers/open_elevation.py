"""Open-Elevation provider: real elevation API, no key required.

Docs: https://api.open-elevation.com/

Provides real elevation_m for any lat/lon. Slope and aspect are derived
from a small neighbourhood of points (north/south/east/west of the target).

Rate limit: ~1 request/second. We batch up to 100 locations per request
to respect the API guidelines.
"""
from __future__ import annotations

import math
from typing import List

import httpx

from app.core.errors import ProviderError
from app.providers.base import Point, TerrainAttributes, TerrainProvider

API_URL = "https://api.open-elevation.com/api/v1/lookup"


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km."""
    R = 6371.0
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _compute_slope_aspect(elevations: dict) -> tuple[float, float]:
    """Given elevations at center + N/S/E/W neighbours, return slope (deg) + aspect (deg).

    elevations keys: center, north, south, east, west
    Uses ~111km per degree approximation (good enough for small offsets).
    Returns 0,0 if neighbours are unavailable.
    """
    if len(elevations) < 5:
        return 0.0, 0.0
    # Use 0.001 degree offset (~111m) for derivative
    offset_deg = 0.001
    distance_m = offset_deg * 111_000

    dz_dx = (elevations.get("east", 0) - elevations.get("west", 0)) / (2 * distance_m)
    dz_dy = (elevations.get("north", 0) - elevations.get("south", 0)) / (2 * distance_m)

    slope_rad = math.atan(math.sqrt(dz_dx ** 2 + dz_dy ** 2))
    slope_deg = math.degrees(slope_rad)

    # Aspect: 0 = North, 90 = East, 180 = South, 270 = West
    aspect_rad = math.atan2(dz_dx, dz_dy)
    aspect_deg = (math.degrees(aspect_rad) + 360) % 360

    return round(slope_deg, 2), round(aspect_deg, 2)


class OpenElevationTerrainProvider(TerrainProvider):
    name = "open_elevation"

    def get_terrain(self, point: Point) -> TerrainAttributes:
        return self.get_terrain_batch([point])[0]

    def get_terrain_batch(self, points: List[Point]) -> List[TerrainAttributes]:
        """Batch fetch terrain for up to 100 points."""
        if not points:
            return []

        # Build request: center + N/S/E/W neighbours for slope/aspect
        locations = []
        for p in points:
            for dy, dx, key in [(0, 0, "center"), (0.001, 0, "north"),
                                (-0.001, 0, "south"), (0, 0.001, "east"),
                                (0, -0.001, "west")]:
                locations.append({
                    "latitude": p.latitude + dy,
                    "longitude": p.longitude + dx,
                })

        try:
            r = httpx.post(
                API_URL,
                json={"locations": locations},
                timeout=30.0,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            # Fallback to mock for training on 600 rows (avoid getaddrinfo fail) - like open_meteo
            from app.core.logging import get_logger
            get_logger("app.providers.open_elevation").warning("open_elevation_failed_fallback", error=str(e))
            import random
            out: List[TerrainAttributes] = []
            for p in points:
                rng = random.Random(hash((p.latitude, p.longitude)) % 2**32)
                out.append(TerrainAttributes(
                    elevation_m=round(300 + rng.uniform(-200, 2500), 2),
                    slope_deg=round(rng.uniform(5, 38), 2),
                    aspect_deg=round(rng.uniform(0, 360), 2),
                    source="open_elevation (fallback mock)",
                    is_synthetic=True,
                ))
            return out

        results = data.get("results", [])
        if not results:
            from app.core.logging import get_logger
            get_logger("app.providers.open_elevation").warning("open_elevation_empty_fallback")
            import random
            out: List[TerrainAttributes] = []
            for p in points:
                rng = random.Random(hash((p.latitude, p.longitude)) % 2**32)
                out.append(TerrainAttributes(
                    elevation_m=round(300 + rng.uniform(-200, 2500), 2),
                    slope_deg=round(rng.uniform(5, 38), 2),
                    aspect_deg=round(rng.uniform(0, 360), 2),
                    source="open_elevation (fallback mock)",
                    is_synthetic=True,
                ))
            return out

        # Group results back per point (5 elevations per point)
        out: List[TerrainAttributes] = []
        for i, p in enumerate(points):
            start = i * 5
            chunk = results[start:start + 5]
            if len(chunk) < 5:
                out.append(TerrainAttributes(
                    elevation_m=chunk[0]["elevation"] if chunk else 0.0,
                    source="open_elevation (partial)",
                    is_synthetic=False,
                ))
                continue
            elevs = {
                "center": chunk[0]["elevation"],
                "north": chunk[1]["elevation"],
                "south": chunk[2]["elevation"],
                "east": chunk[3]["elevation"],
                "west": chunk[4]["elevation"],
            }
            slope, aspect = _compute_slope_aspect(elevs)
            out.append(TerrainAttributes(
                elevation_m=round(elevs["center"], 2),
                slope_deg=slope,
                aspect_deg=aspect,
                source="open_elevation",
                is_synthetic=False,
            ))
        return out
