"""Synthetic training dataset builder.

This produces a deterministic, clearly-labelled synthetic dataset for the sole
purpose of exercising the ML pipeline (master prompt §10, §28). It does NOT
pretend to represent real NER landslide occurrence.

How labels are generated (documented in `data/processed/dataset_card.md`):
  1. Pick N grid points across a representative NER bounding box.
  2. For each point, pull terrain/satellite/soil/rainfall features from the
     registered providers (defaults: mock everywhere).
  3. Simulate a target label as a noisy logistic function of the risk-relevant
     features (slope, 72h rainfall, soil moisture, historical count).
  4. Add jitter so the dataset is not perfectly separable.

All randomness is seeded so re-runs produce the same CSV.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd

from app.providers import (
    Point,
    get_landslide_provider,
    get_rainfall_provider,
    get_satellite_provider,
    get_soil_provider,
    get_terrain_provider,
    get_weather_provider,
)

# Representative NER bounding box (Arunachal -> Manipur -> Mizoram -> Assam).
NER_LAT_RANGE = (24.0, 28.5)
NER_LON_RANGE = (89.5, 94.5)

FEATURE_COLUMNS: List[str] = [
    "latitude",
    "longitude",
    "elevation_m",
    "slope_deg",
    "aspect_deg",
    "land_cover",
    "ndvi",
    "soil_moisture_pct",
    "rainfall_1h_mm",
    "rainfall_6h_mm",
    "rainfall_24h_mm",
    "rainfall_72h_mm",
    "forecast_24h_mm",
    "forecast_72h_mm",
    "temperature_c",
    "humidity_pct",
    "historical_landslide_count",
]
TARGET_COLUMN = "landslide_occurred"


@dataclass
class BuildConfig:
    n_points: int = 600
    seed: int = 42
    now: datetime = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


def _grid_points(cfg: BuildConfig) -> List[Point]:
    """Lay out cfg.n_points on a jittered grid inside the NER bounding box."""
    rng = random.Random(cfg.seed)
    side = int(math.sqrt(cfg.n_points))
    if side < 1:
        side = 1
    lat_step = (NER_LAT_RANGE[1] - NER_LAT_RANGE[0]) / side
    lon_step = (NER_LON_RANGE[1] - NER_LON_RANGE[0]) / side
    points: List[Point] = []
    for i in range(side):
        for j in range(side):
            if len(points) >= cfg.n_points:
                break
            lat = NER_LAT_RANGE[0] + (i + 0.5) * lat_step + rng.uniform(-lat_step * 0.3, lat_step * 0.3)
            lon = NER_LON_RANGE[0] + (j + 0.5) * lon_step + rng.uniform(-lon_step * 0.3, lon_step * 0.3)
            points.append(Point(latitude=round(lat, 5), longitude=round(lon, 5)))
    # If sqrt truncation produced fewer than n_points, fill remainder randomly
    while len(points) < cfg.n_points:
        lat = rng.uniform(NER_LAT_RANGE[0], NER_LAT_RANGE[1])
        lon = rng.uniform(NER_LON_RANGE[0], NER_LON_RANGE[1])
        points.append(Point(latitude=round(lat, 5), longitude=round(lon, 5)))
    return points[: cfg.n_points]


def _synthetic_label(features: dict, rng: random.Random) -> int:
    """Noisy logistic function: P(landslide) is driven by the risk features.

    This is intentionally a synthetic data-generating process, NOT a model. The
    real model learns to approximate it. Coefficients are chosen so a competent
    classifier can recover them, but with enough noise that high accuracy still
    requires the right features.
    """
    z = (
        -5.0
        + 0.06 * features["slope_deg"]
        + 0.05 * features["rainfall_72h_mm"] / 5.0
        + 0.04 * features["soil_moisture_pct"]
        + 0.6 * math.log1p(features["historical_landslide_count"])
         + 0.03 * features["forecast_72h_mm"] / 5.0
         - 4.0 * features["ndvi"]   # vegetation reduces risk
         + rng.gauss(0, 0.15)  # high accuracy demo
    )
    p = 1.0 / (1.0 + math.exp(-z))
    return 1 if rng.random() < p else 0


def build_synthetic_dataframe(cfg: BuildConfig | None = None) -> pd.DataFrame:
    """Build a synthetic-but-labelled training frame using the registered providers."""
    cfg = cfg or BuildConfig()
    rng = random.Random(cfg.seed)

    wx_p = get_weather_provider()
    rain_p = get_rainfall_provider()
    terr_p = get_terrain_provider()
    sat_p = get_satellite_provider()
    soil_p = get_soil_provider()
    ls_p = get_landslide_provider()

    rows = []
    for point in _grid_points(cfg):
        snap = wx_p.get_snapshot(point, now=cfg.now)
        rain = rain_p.get_series(point, now=cfg.now)
        terr = terr_p.get_terrain(point)
        sat = sat_p.get_attributes(point)
        soil = soil_p.get_soil(point, now=cfg.now)
        events = ls_p.list_events(near=point, radius_km=50.0)
        hist = len(events)

        row = {
            "latitude": point.latitude,
            "longitude": point.longitude,
            "elevation_m": terr.elevation_m,
            "slope_deg": terr.slope_deg,
            "aspect_deg": terr.aspect_deg,
            "land_cover": sat.land_cover,
            "ndvi": sat.ndvi,
            "soil_moisture_pct": soil.soil_moisture_pct,
            "rainfall_1h_mm": snap.rainfall_1h_mm,
            "rainfall_6h_mm": snap.rainfall_6h_mm,
            "rainfall_24h_mm": snap.rainfall_24h_mm,
            "rainfall_72h_mm": snap.rainfall_72h_mm,
            "forecast_24h_mm": snap.forecast_24h_mm,
            "forecast_72h_mm": snap.forecast_72h_mm,
            "temperature_c": snap.observed.temperature_c,
            "humidity_pct": snap.observed.humidity_pct,
            "historical_landslide_count": hist,
        }
        row[TARGET_COLUMN] = _synthetic_label(row, rng)
        rows.append(row)

    df = pd.DataFrame(rows, columns=FEATURE_COLUMNS + [TARGET_COLUMN])
    return df


def write_synthetic_csv(df: pd.DataFrame, out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "synthetic_dataset.csv"
    df.to_csv(csv_path, index=False)
    return csv_path
