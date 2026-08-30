"""Nominatim geocoding provider: address to lat/lon, no key required.

Docs: https://nominatim.org/release-docs/develop/api/Overview/

Converts Indian district/village names to coordinates. Rate limit:
1 request/second. Must include a User-Agent header per their TOS.

Use case: When a field worker submits a report by place name instead
of GPS coordinates, this provider can resolve it.
"""
from __future__ import annotations

import time
from typing import Optional

import httpx

from app.core.errors import ProviderError
from app.core.logging import get_logger
from app.providers.base import Point

log = get_logger(__name__)

API_URL = "https://nominatim.openstreetmap.org/search"

# Required by Nominatim TOS
USER_AGENT = "LandslideEarlyWarning-NER/1.0 (research project)"


# Simple in-memory cache to respect rate limits
_cache: dict[str, Optional[Point]] = {}
_last_call: float = 0.0


def _rate_limit() -> None:
    """Ensure we respect 1 req/sec."""
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    _last_call = time.time()


def geocode(query: str, country: str = "India") -> Optional[Point]:
    """Convert a place name to lat/lon. Returns None if not found.

    Args:
        query: e.g. "Imphal", "Guwahati", "Shillong"
        country: ISO country code (default: India)
    """
    cache_key = f"{query}|{country}".lower()
    if cache_key in _cache:
        return _cache[cache_key]

    _rate_limit()
    try:
        r = httpx.get(
            API_URL,
            params={"q": query, "countrycodes": country.lower(), "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=15.0,
        )
        r.raise_for_status()
        results = r.json()
    except Exception as e:
        log.warning("nominatim_request_failed", query=query, error=str(e))
        return None

    if not results:
        _cache[cache_key] = None
        return None

    top = results[0]
    point = Point(
        latitude=float(top["lat"]),
        longitude=float(top["lon"]),
    )
    _cache[cache_key] = point
    return point


def reverse_geocode(latitude: float, longitude: float) -> Optional[str]:
    """Convert lat/lon to a human-readable place name."""
    _rate_limit()
    try:
        r = httpx.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": latitude, "lon": longitude, "format": "json"},
            headers={"User-Agent": USER_AGENT},
            timeout=15.0,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("display_name")
    except Exception as e:
        log.warning("nominatim_reverse_failed", lat=latitude, lon=longitude, error=str(e))
        return None
