"""USGS Earthquake provider: real-time earthquake data, no key required.

Docs: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php

Earthquakes are a major trigger for landslides. This provider fetches
earthquakes in/near the NER bounding box for the last 30 days.

Returns a list of points that can be fed into the risk engine as a
"recent seismic activity" feature.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List

import httpx

from app.core.logging import get_logger
from app.providers.base import Point

log = get_logger(__name__)

API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# NER bounding box
NER_LAT_RANGE = (21.5, 29.5)
NER_LON_RANGE = (88.0, 97.5)


@dataclass
class Earthquake:
    point: Point
    magnitude: float
    depth_km: float
    timestamp: datetime
    place: str
    url: str


def fetch_earthquakes_near(
    point: Point | None = None,
    radius_km: float = 300.0,
    days: int = 30,
    min_magnitude: float = 2.5,
) -> List[Earthquake]:
    """Fetch earthquakes near a point (default: center of NER bbox).

    Args:
        point: Center point (default: NER center).
        radius_km: Search radius in km.
        days: How many days back to search.
        min_magnitude: Minimum magnitude to include.
    """
    if point is None:
        point = Point(
            latitude=(NER_LAT_RANGE[0] + NER_LAT_RANGE[1]) / 2,
            longitude=(NER_LON_RANGE[0] + NER_LON_RANGE[1]) / 2,
        )
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    params = {
        "format": "geojson",
        "starttime": start.strftime("%Y-%m-%d"),
        "endtime": end.strftime("%Y-%m-%d"),
        "latitude": point.latitude,
        "longitude": point.longitude,
        "maxradiuskm": radius_km,
        "minmagnitude": min_magnitude,
    }
    try:
        r = httpx.get(API_URL, params=params, timeout=20.0)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("usgs_request_failed", error=str(e))
        return []

    out = []
    for feat in data.get("features", []):
        coords = feat.get("geometry", {}).get("coordinates", [None, None, None])
        if len(coords) < 2 or coords[0] is None:
            continue
        lon, lat, depth = coords[0], coords[1], coords[2] if len(coords) > 2 else 0.0
        props = feat.get("properties", {})
        mag = props.get("mag", 0.0) or 0.0
        ts_ms = props.get("time", 0)
        ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc) if ts_ms else datetime.now(timezone.utc)
        out.append(Earthquake(
            point=Point(latitude=lat, longitude=lon),
            magnitude=float(mag),
            depth_km=float(depth) if depth else 0.0,
            timestamp=ts,
            place=props.get("place", "Unknown"),
            url=props.get("url", ""),
        ))
    log.info("usgs_earthquakes_fetched", count=len(out), center=point)
    return out


def count_recent_earthquakes(
    point: Point, radius_km: float = 100.0, days: int = 7, min_magnitude: float = 2.5
) -> int:
    """Quick count for use as a feature in the risk model."""
    return len(fetch_earthquakes_near(point, radius_km, days, min_magnitude))
