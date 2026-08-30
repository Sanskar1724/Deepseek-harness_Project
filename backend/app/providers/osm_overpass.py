"""OpenStreetMap Overpass provider: real infrastructure data, no key required.

Docs: https://wiki.openstreetmap.org/wiki/Overpass_API

Fetches roads, hospitals, schools, bridges, and villages within a bounding box.
The NER bounding box is: lat 21.5-29.5, lon 88-97.5.

This is a query-based provider, not point-based. Call sync_infrastructure()
to fetch a region and insert into the local DB.
"""
from __future__ import annotations

from typing import Dict, List

import httpx

from app.core.errors import ProviderError
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models import Infrastructure, InfrastructureType
from app.providers.base import Point

log = get_logger(__name__)

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

# NER bounding box
NER_BBOX = {
    "south": 21.5,
    "west": 88.0,
    "north": 29.5,
    "east": 97.5,
}

# OSM tag -> our InfrastructureType
TAG_MAP = {
    "hospital": (InfrastructureType.HOSPITAL, 5),
    "clinic": (InfrastructureType.HOSPITAL, 3),
    "school": (InfrastructureType.SCHOOL, 4),
    "college": (InfrastructureType.SCHOOL, 3),
    "university": (InfrastructureType.SCHOOL, 4),
    "bridge": (InfrastructureType.BRIDGE, 4),
    "village": (InfrastructureType.VILLAGE, 2),
    "town": (InfrastructureType.TOWN, 3),
    "power_line": (InfrastructureType.POWER_LINE, 2),
    "substation": (InfrastructureType.POWER_LINE, 4),
}


def _build_query(bbox: Dict[str, float]) -> str:
    """Build Overpass QL query for infrastructure in the bounding box."""
    bb = f"{bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']}"
    return f"""
[out:json][timeout:60];
(
  node["amenity"="hospital"]({bb});
  node["amenity"="clinic"]({bb});
  node["amenity"="school"]({bb});
  node["amenity"="college"]({bb});
  node["amenity"="university"]({bb});
  way["bridge"]({bb});
  node["place"="village"]({bb});
  node["place"="town"]({bb});
  node["power"="line"]({bb});
  node["power"="substation"]({bb});
);
out center tags;
"""


def _classify(tags: dict) -> tuple[InfrastructureType, int] | None:
    """Map OSM tags to our InfrastructureType + importance."""
    if tags.get("amenity") in TAG_MAP:
        return TAG_MAP[tags["amenity"]]
    if tags.get("bridge") == "yes":
        return TAG_MAP["bridge"]
    if tags.get("place") in TAG_MAP:
        return TAG_MAP[tags["place"]]
    if tags.get("power") in TAG_MAP:
        return TAG_MAP[tags["power"]]
    return None


def _name(tags: dict, fallback: str) -> str:
    return tags.get("name", tags.get("name:en", fallback))


def fetch_infrastructure(bbox: Dict[str, float] | None = None) -> List[dict]:
    """Fetch infrastructure from OSM for the given bbox. Returns raw dicts.

    Each dict: {name, type, importance, latitude, longitude}
    """
    bbox = bbox or NER_BBOX
    query = _build_query(bbox)
    last_err = None
    for url in OVERPASS_URLS:
        try:
            log.info("overpass_request", url=url, bbox=bbox)
            r = httpx.post(
                url,
                data={"data": query},
                headers={"User-Agent": "LandslideEarlyWarning-NER/1.0"},
                timeout=90.0,
            )
            r.raise_for_status()
            data = r.json()
            break
        except Exception as e:
            log.warning("overpass_failed", url=url, error=str(e))
            last_err = e
    else:
        raise ProviderError(f"All Overpass servers failed. Last: {last_err}")

    elements = data.get("elements", [])
    out = []
    for el in elements:
        tags = el.get("tags", {})
        classification = _classify(tags)
        if classification is None:
            continue
        itype, importance = classification
        # Nodes have lat/lon directly; ways have center
        if el.get("type") == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:
            center = el.get("center", {})
            lat, lon = center.get("lat"), center.get("lon")
        if lat is None or lon is None:
            continue
        out.append({
            "name": _name(tags, f"{itype.value} {len(out) + 1}"),
            "type": itype,
            "importance": importance,
            "latitude": float(lat),
            "longitude": float(lon),
            "source": "openstreetmap",
        })
    log.info("overpass_results", count=len(out))
    return out


def sync_infrastructure(bbox: Dict[str, float] | None = None) -> int:
    """Fetch from OSM and upsert into the local DB. Returns count inserted/updated."""
    items = fetch_infrastructure(bbox)
    count = 0
    with SessionLocal() as db:
        for item in items:
            existing = (
                db.query(Infrastructure)
                .filter(
                    Infrastructure.name == item["name"],
                    Infrastructure.latitude == item["latitude"],
                    Infrastructure.longitude == item["longitude"],
                )
                .one_or_none()
            )
            if existing:
                continue  # idempotent
            infra = Infrastructure(
                name=item["name"],
                type=item["type"],
                importance=item["importance"],
                latitude=item["latitude"],
                longitude=item["longitude"],
            )
            db.add(infra)
            count += 1
        db.commit()
    log.info("infrastructure_synced", inserted=count, total_fetched=len(items))
    return count
