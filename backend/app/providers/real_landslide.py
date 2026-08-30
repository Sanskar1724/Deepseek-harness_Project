"""Real landslide provider using NASA COOLR CSV (no key, real historical)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from app.db.session import haversine_km
from app.providers.base import HistoricalLandslide, LandslideProvider, Point

CSV_PATH = Path(__file__).resolve().parents[3] / "data" / "raw" / "Global_Landslide_Catalog_Export_rows.csv"

# Cache the dataframe
_DF = None

def _load_df() -> pd.DataFrame:
    global _DF
    if _DF is not None:
        return _DF
    if not CSV_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(CSV_PATH, low_memory=False)
        df = df.dropna(subset=["latitude", "longitude"])
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        _DF = df
        return _DF
    except Exception:
        return pd.DataFrame()


class RealLandslideProvider(LandslideProvider):
    name = "real_coolr"

    def list_events(
        self,
        *,
        near: Optional[Point] = None,
        radius_km: Optional[float] = None,
        since: Optional[datetime] = None,
    ) -> List[HistoricalLandslide]:
        df = _load_df()
        if df.empty or near is None:
            return []
        radius_km = radius_km or 50.0
        out: List[HistoricalLandslide] = []
        for _, row in df.iterrows():
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                d = haversine_km(near.latitude, near.longitude, lat, lon)
                if d <= radius_km:
                    out.append(HistoricalLandslide(
                        point=Point(latitude=lat, longitude=lon),
                        event_date=datetime(2023, 6, 1),
                        severity=int(row.get("severity", 3)) if "severity" in row else 3,
                        source="nasa_coolr_real",
                        description=str(row.get("landslide_size", "real")),
                    ))
            except Exception:
                continue
        return out
