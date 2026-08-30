"""NASA POWER provider: real public API, no key required.

Docs: https://power.larc.nasa.gov/docs/services/api/

Returns daily precipitation + temperature aggregates. We expose this as both a
terrain/auxiliary source and a soil-precip proxy for the demo. It does NOT
provide true soil moisture; for that, use SMAP (out of scope for this build).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.errors import ProviderError
from app.providers.base import (
    Point,
    SoilAttributes,
    SoilProvider,
    TerrainAttributes,
    TerrainProvider,
)

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


class NasaPowerTerrainProvider(TerrainProvider):
    """NASA POWER does not provide elevation, so this is a clearly-labelled stub.

    Real elevation/slope must come from a DEM (SRTM/Copernicus). When that
    provider is added, replace this class.
    """
    name = "nasa_power"

    def get_terrain(self, point: Point) -> TerrainAttributes:
        return TerrainAttributes(
            elevation_m=0.0,
            slope_deg=0.0,
            aspect_deg=0.0,
            source="nasa_power (terrain=N/A, requires DEM)",
            is_synthetic=False,
        )


class NasaPowerSoilProvider(SoilProvider):
    """Maps daily precipitation (PRECTOT) to a rough soil-moisture proxy.

    This is NOT real soil moisture. It is a clearly-labelled proxy so the demo
    has a moving value when no real SMAP feed is wired in.
    """
    name = "nasa_power"

    def get_soil(self, point: Point, *, now: Optional[datetime] = None) -> SoilAttributes:
        now = now or datetime.now(timezone.utc)
        end = now.strftime("%Y%m%d")
        # NASA POWER renamed PRECTOT -> PRECTOTCORR (v2 API). Try both.
        params = {
            "parameters": "PRECTOTCORR",
            "community": "AG",
            "longitude": f"{point.longitude:.4f}",
            "latitude": f"{point.latitude:.4f}",
            "start": end,
            "end": end,
            "format": "JSON",
        }
        try:
            r = httpx.get(POWER_URL, params=params, timeout=20.0)
            r.raise_for_status()
            data = r.json()
        except Exception as e:  # noqa: BLE001
            # Fallback to mock-like value instead of hard failing (avoid 502)
            from app.core.logging import get_logger

            get_logger("app.providers.nasa_power").warning(
                "nasa_power_call_failed_fallback", error=str(e)
            )
            return SoilAttributes(
                soil_moisture_pct=35.0,
                source="nasa_power (fallback)",
                is_synthetic=True,
            )

        precip_mm = None
        try:
            param_block = data.get("properties", {}).get("parameter", {})
            # Try PRECTOTCORR first, then legacy PRECTOT
            for key in ("PRECTOTCORR", "PRECTOT"):
                if key in param_block and end in param_block[key]:
                    precip_mm = float(param_block[key][end])
                    break
            if precip_mm is None:
                raise KeyError(f"PRECTOTCORR/PRECTOT missing for {end}")
        except (KeyError, ValueError, TypeError) as e:
            from app.core.logging import get_logger

            get_logger("app.providers.nasa_power").warning(
                "nasa_power_shape_fallback", error=str(e)
            )
            return SoilAttributes(
                soil_moisture_pct=35.0,
                source="nasa_power (fallback)",
                is_synthetic=True,
            )

        # NASA uses -999 as fill/missing
        if precip_mm is None or precip_mm < -900:
            precip_mm = 0.0
        sm = max(0.0, min(95.0, precip_mm * 3.0 + 25.0))
        return SoilAttributes(
            soil_moisture_pct=sm,
            source="nasa_power (precip proxy)",
            is_synthetic=False,
        )
