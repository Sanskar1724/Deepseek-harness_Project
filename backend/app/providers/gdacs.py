"""GDACS (Global Disaster Alert and Coordination System) provider.

Docs: https://www.gdacs.org/xml/rss.xml

Provides real-time global disaster alerts including floods, earthquakes,
tropical cyclones. Relevant for NER landslide early warning because:
  - Heavy rain events trigger landslides
  - Earthquakes can trigger landslides
  - Floods often precede landslides in monsoon season

No API key required. Returns alerts as RSS/JSON.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import httpx

from app.core.logging import get_logger
from app.providers.base import Point

log = get_logger(__name__)

GDACS_RSS = "https://www.gdacs.org/xml/rss.xml"
GDACS_JSON = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?fromDate=2024-01-01&limit=100"


@dataclass
class DisasterAlert:
    event_id: str
    event_type: str  # EQ, FL, TC, VO, DR, WF
    name: str
    point: Point
    severity: str  # Green, Orange, Red
    timestamp: datetime
    description: str
    url: str


# Map GDACS event types to our interest
RELEVANT_TYPES = {"FL", "EQ", "TC"}  # Flood, Earthquake, Tropical Cyclone


def fetch_recent_alerts(days: int = 7) -> List[DisasterAlert]:
    """Fetch recent disaster alerts from GDACS.

    Note: GDACS RSS is global. We return all alerts; the caller should
    filter by location if needed.
    """
    try:
        r = httpx.get(GDACS_JSON, timeout=30.0)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("gdacs_request_failed", error=str(e))
        return []

    features = data.get("features", [])
    out: List[DisasterAlert] = []
    for feat in features:
        props = feat.get("properties", {})
        event_type = props.get("eventtype", "")
        if event_type not in RELEVANT_TYPES:
            continue
        coords = feat.get("geometry", {}).get("coordinates")
        if not coords or len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        # Filter to NER region (rough bbox check)
        if not (21.0 <= lat <= 30.0 and 87.0 <= lon <= 98.0):
            continue
        out.append(DisasterAlert(
            event_id=str(props.get("eventid", "")),
            event_type=event_type,
            name=props.get("name", props.get("eventname", "Unknown")),
            point=Point(latitude=lat, longitude=lon),
            severity=props.get("alertlevel", "Green"),
            timestamp=datetime.fromisoformat(
                props.get("fromdate", "2024-01-01T00:00:00").replace("Z", "+00:00")
            ).astimezone(timezone.utc) if props.get("fromdate") else datetime.now(timezone.utc),
            description=props.get("description", "")[:500],
            url=props.get("url", {}).get("report", "") if isinstance(props.get("url"), dict) else str(props.get("url", "")),
        ))
    log.info("gdacs_alerts_fetched", count=len(out))
    return out
