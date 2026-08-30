"""Seed the database with demo data."""
from __future__ import annotations

import random
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.db.session import init_db, SessionLocal
from app.models import (
    Infrastructure, InfrastructureType, Location, RiskPrediction, WeatherData
)


def seed(n_locations: int = 12, n_infra: int = 40) -> None:
    init_db()
    rng = random.Random(42)
    states = [
        ("Manipur", "Imphal West"), ("Assam", "Kamrup"),
        ("Meghalaya", "East Khasi Hills"), ("Nagaland", "Kohima"),
        ("Tripura", "West Tripura"),
    ]
    with SessionLocal() as db:
        db.query(RiskPrediction).delete()
        db.query(WeatherData).delete()
        db.query(Infrastructure).delete()
        db.query(Location).delete()
        db.commit()
        locs = []
        for i in range(n_locations):
            state, district = rng.choice(states)
            lat = 24.0 + rng.random() * 4.5
            lon = 89.5 + rng.random() * 5.0
            loc = Location(
                name=f"Demo Location {i + 1}",
                state=state, district=district,
                latitude=lat, longitude=lon,
                elevation_m=200 + rng.random() * 2500,
                slope_deg=8 + rng.random() * 40,
                aspect_deg=rng.random() * 360,
                land_cover=rng.choice(["forest", "shrubland", "grassland", "cropland"]),
                ndvi=0.2 + rng.random() * 0.6,
                historical_landslide_count=rng.randint(0, 8),
            )
            db.add(loc)
            locs.append(loc)
        db.commit()
        infra_types = [
            InfrastructureType.ROAD, InfrastructureType.BRIDGE,
            InfrastructureType.VILLAGE, InfrastructureType.HOSPITAL,
            InfrastructureType.SCHOOL,
        ]
        for i in range(n_infra):
            loc = rng.choice(locs)
            lat = loc.latitude + (rng.random() - 0.5) * 0.2
            lon = loc.longitude + (rng.random() - 0.5) * 0.2
            itype = rng.choice(infra_types)
            infra = Infrastructure(
                name=f"{itype.value.title()} {i + 1}",
                type=itype,
                importance=rng.randint(1, 5),
                latitude=lat, longitude=lon,
            )
            db.add(infra)
        db.commit()
        now = datetime.now(timezone.utc)
        for loc in locs:
            w = WeatherData(
                location_id=loc.id, timestamp=now,
                rainfall_1h=rng.uniform(0, 5), rainfall_6h=rng.uniform(0, 20),
                rainfall_24h=rng.uniform(0, 60), rainfall_72h=rng.uniform(0, 150),
                forecast_rainfall_24h=rng.uniform(5, 50),
                forecast_rainfall_72h=rng.uniform(15, 120),
                temperature_c=15 + rng.random() * 15,
                humidity_pct=50 + rng.random() * 40,
                soil_moisture_pct=30 + rng.random() * 50,
                source="mock",
            )
            db.add(w)
        db.commit()
        for loc in locs:
            score = rng.randint(0, 100)
            if score >= 81:
                level = "CRITICAL"
            elif score >= 61:
                level = "HIGH"
            elif score >= 31:
                level = "MODERATE"
            else:
                level = "LOW"
            rp = RiskPrediction(
                location_id=loc.id, timestamp=now,
                risk_score=score, risk_level=level,
                model_version="seed-v1",
            )
            db.add(rp)
        db.commit()
        print(f"Seeded {len(locs)} locations, {n_infra} infrastructure, {len(locs)} predictions.")


if __name__ == "__main__":
    seed()
