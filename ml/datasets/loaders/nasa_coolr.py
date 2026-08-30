"""NASA COOLR (Cooperative Open Online Landslide Repository) loader.

This loader reads the NASA Global Landslide Catalog CSV and produces a
pandas DataFrame suitable for training. The CSV is expected to have the
columns documented at:
  https://data.nasa.gov/dataset/cooperative-open-online-landslide-repository-cool-r

Required columns: event_date, latitude, longitude, country_name, landslide_size

Usage:
    # Save the downloaded CSV as data/raw/nasa_coolr.csv
    # Then in a script:
    from ml.datasets.loaders.nasa_coolr import NasaCoolrLoader
    df = NasaCoolrLoader("data/raw/nasa_coolr.csv").load()
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from app.core.logging import get_logger

from ml.datasets.loaders.base import DatasetLoader

log = get_logger(__name__)


# NER bounding box: Arunachal -> Manipur -> Mizoram -> Assam
NER_LAT_RANGE = (21.5, 29.5)
NER_LON_RANGE = (88.0, 97.5)

# Map admin division names to our state names
NER_STATE_MAP = {
    "Assam": "Assam",
    "Arunachal Pradesh": "Arunachal Pradesh",
    "Manipur": "Manipur",
    "Meghalaya": "Meghalaya",
    "Mizoram": "Mizoram",
    "Nagaland": "Nagaland",
    "Sikkim": "Sikkim",
    "Tripura": "Tripura",
}

# Map landslide_size to severity 1-5
SIZE_TO_SEVERITY = {
    "small": 1,
    "medium": 2,
    "large": 3,
    "very_large": 4,
    "catastrophic": 5,
    "unknown": 2,
    "": 2,
}


class NasaCoolrLoader(DatasetLoader):
    name = "nasa_coolr"

    def __init__(
        self,
        csv_path: str | Path,
        *,
        ner_only: bool = True,
        min_year: int = 2007,
        max_year: int = 2024,
    ) -> None:
        self.csv_path = Path(csv_path)
        self.ner_only = ner_only
        self.min_year = min_year
        self.max_year = max_year

    def load(self) -> pd.DataFrame:
        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"NASA COOLR CSV not found: {self.csv_path}\n"
                f"Download from https://data.nasa.gov/ and save to this path."
            )

        log.info("loading_nasa_coolr", path=str(self.csv_path))
        df = pd.read_csv(self.csv_path, low_memory=False)
        log.info("raw_rows", count=len(df))

        # Standardize column names (strip whitespace)
        df.columns = [c.strip() for c in df.columns]

        # Parse event_date (format: MM-DD-YYYY HH:MM or similar)
        df["event_date_parsed"] = pd.to_datetime(
            df["event_date"], errors="coerce", format="mixed"
        )
        df["year"] = df["event_date_parsed"].dt.year

        # Filter by year range
        mask = (df["year"] >= self.min_year) & (df["year"] <= self.max_year)
        df = df[mask].copy()
        log.info("after_year_filter", count=len(df))

        # Filter to NER bounding box (if requested)
        if self.ner_only:
            mask = (
                (df["latitude"].between(NER_LAT_RANGE[0], NER_LAT_RANGE[1]))
                & (df["longitude"].between(NER_LON_RANGE[0], NER_LON_RANGE[1]))
            )
            df = df[mask].copy()
            log.info("after_ner_bbox_filter", count=len(df))

        # Drop rows without lat/lon
        df = df.dropna(subset=["latitude", "longitude"])
        log.info("after_dropna_latlon", count=len(df))

        # Map state names
        df["state"] = df["admin_division_name"].map(NER_STATE_MAP)

        # Map severity from landslide_size
        df["severity"] = (
            df["landslide_size"].fillna("unknown").str.lower().map(SIZE_TO_SEVERITY).fillna(2)
        )

        # Create the target column (always 1 for actual landslide events)
        df["landslide_occurred"] = 1

        # Create negative samples (non-events) by jittering locations
        # This is important: we need both classes for training
        # We create 3x as many negative samples as positive (typical for landslide)
        negative_df = self._create_negative_samples(df)
        log.info("negative_samples_created", count=len(negative_df))

        # Combine
        full_df = pd.concat([df, negative_df], ignore_index=True)
        log.info("total_training_rows", count=len(full_df))

        # Return the standard columns our system expects
        # Plus keep the original NASA columns for traceability
        return full_df

    def _create_negative_samples(
        self, positive_df: pd.DataFrame, ratio: int = 3
    ) -> pd.DataFrame:
        """Create synthetic negative samples (no-landslide points).

        We jitter the positive locations by ~0.05-0.2 degrees to create
        nearby points that did NOT have a landslide. This is a common
        technique when only positive examples are available.
        """
        import numpy as np

        rng = np.random.default_rng(42)
        negative_rows = []

        for _, row in positive_df.iterrows():
            for _ in range(ratio):
                # Jitter by 0.05-0.3 degrees (~5-30 km)
                dlat = rng.uniform(-0.3, 0.3)
                dlon = rng.uniform(-0.3, 0.3)
                new_row = row.copy()
                new_row["latitude"] = row["latitude"] + dlat
                new_row["longitude"] = row["longitude"] + dlon
                new_row["landslide_occurred"] = 0
                new_row["severity"] = 0
                negative_rows.append(new_row)

        return pd.DataFrame(negative_rows)

    def to_training_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert to the feature schema our ML pipeline expects.

        Returns a DataFrame with the columns defined in
        ml/datasets/synthetic.py:FEATURE_COLUMNS plus the target.

        Note: Terrain/weather features will be filled by the providers
        at prediction time. This loader provides:
          - latitude, longitude
          - historical_landslide_count (from nearby events)
          - land_cover (placeholder)
        """
        out = pd.DataFrame()
        out["latitude"] = df["latitude"].values
        out["longitude"] = df["longitude"].values

        # Historical landslide count: within ~50km
        # For simplicity, count events in same bounding box tile
        out["historical_landslide_count"] = (
            df.apply(lambda r: self._count_nearby(r["latitude"], r["longitude"], df), axis=1)
        )

        # Placeholder land_cover (will be overridden by satellite provider)
        out["land_cover"] = "forest"

        # Target
        out["landslide_occurred"] = df["landslide_occurred"].values

        # Other columns will be filled by providers at training time
        for col in [
            "elevation_m", "slope_deg", "aspect_deg", "ndvi",
            "soil_moisture_pct", "rainfall_1h_mm", "rainfall_6h_mm",
            "rainfall_24h_mm", "rainfall_72h_mm", "forecast_24h_mm",
            "forecast_72h_mm", "temperature_c", "humidity_pct",
        ]:
            out[col] = 0.0

        return out

    @staticmethod
    def _count_nearby(lat: float, lon: float, df: pd.DataFrame, radius_deg: float = 0.5) -> int:
        """Count events within ~50km (0.5 degrees)."""
        mask = (
            (df["latitude"].between(lat - radius_deg, lat + radius_deg))
            & (df["longitude"].between(lon - radius_deg, lon + radius_deg))
            & (df["landslide_occurred"] == 1)
        )
        return int(mask.sum())
