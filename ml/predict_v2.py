"""V2 predict: uses coordinate-based terrain (same logic as training) for consistency."""
from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

log = logging.getLogger("app.predict")

REGISTRY_DIR = Path(__file__).resolve().parent / "artifacts" / "registry"
REGISTRY_DIR.mkdir(parents=True, exist_ok=True)


class ModelNotFoundError(FileNotFoundError):
    pass


@dataclass
class ModelBundle:
    model_version: str
    algorithm: str
    model: object
    feature_columns: list
    schema: object


def estimate_terrain_from_coords(lat: float, lon: float) -> dict:
    """Smart terrain estimation based on NER geography (matches training)."""
    np.random.seed(int(abs(lat * 1000 + lon * 1000)) % 2147483647)
    shillong_dist = ((lat - 25.6) ** 2 + (lon - 91.8) ** 2) ** 0.5
    if shillong_dist < 1.5:
        elev = np.random.uniform(1200, 1800)
        slope = np.random.uniform(15, 35)
    elif lat > 27:
        elev = np.random.uniform(800, 3500)
        slope = np.random.uniform(20, 45)
    elif 25 < lat < 26.5 and 93.5 < lon < 95.5:
        elev = np.random.uniform(700, 2200)
        slope = np.random.uniform(18, 40)
    elif 22 < lat < 24.5 and 92.5 < lon < 94:
        elev = np.random.uniform(400, 1600)
        slope = np.random.uniform(20, 45)
    elif 24 < lat < 25.5 and 93 < lon < 94.5:
        elev = np.random.uniform(700, 2500)
        slope = np.random.uniform(15, 35)
    elif 22.5 < lat < 24.5 and 91 < lon < 92.5:
        elev = np.random.uniform(20, 500)
        slope = np.random.uniform(0, 15)
    else:
        elev = np.random.uniform(50, 500)
        slope = np.random.uniform(0, 10)
    return {
        "elevation_m": float(elev),
        "slope_deg": float(slope),
        "aspect_deg": float(np.random.uniform(0, 360)),
    }


def monthly_climatology(lat: float, lon: float, month: int = None) -> dict:
    """Fast climatology fallback (no API)."""
    from datetime import datetime
    if month is None:
        month = datetime.now().month
    if month in [6, 7, 8, 9]:
        rain_24h = np.random.uniform(8, 60)
        rain_72h = rain_24h * np.random.uniform(2.5, 4.5)
        forecast_72h = rain_72h * np.random.uniform(1.0, 1.5)
        humidity = np.random.uniform(80, 95)
        temp = np.random.uniform(22, 30)
    elif month in [12, 1, 2]:
        rain_24h = np.random.uniform(0, 3)
        rain_72h = np.random.uniform(0, 8)
        forecast_72h = np.random.uniform(0, 10)
        humidity = np.random.uniform(45, 65)
        temp = np.random.uniform(5, 15)
    elif month in [3, 4, 5]:
        rain_24h = np.random.uniform(0, 20)
        rain_72h = np.random.uniform(5, 50)
        forecast_72h = np.random.uniform(10, 70)
        humidity = np.random.uniform(55, 75)
        temp = np.random.uniform(15, 25)
    else:
        rain_24h = np.random.uniform(0, 12)
        rain_72h = np.random.uniform(0, 30)
        forecast_72h = np.random.uniform(0, 35)
        humidity = np.random.uniform(60, 80)
        temp = np.random.uniform(15, 22)
    return {
        "rainfall_1h_mm": max(0, rain_24h / 24 * np.random.uniform(0.3, 2)),
        "rainfall_6h_mm": max(0, rain_24h / 4 * np.random.uniform(0.5, 1.2)),
        "rainfall_24h_mm": max(0, rain_24h),
        "rainfall_72h_mm": max(0, rain_72h),
        "forecast_24h_mm": max(0, rain_24h * np.random.uniform(0.8, 1.2)),
        "forecast_72h_mm": max(0, forecast_72h),
        "temperature_c": temp,
        "humidity_pct": humidity,
    }


def _features_for_point(point, historical_count: int = 0, use_real_weather: bool = False) -> pd.DataFrame:
    """Build features matching the training data format."""
    lat = point.latitude
    lon = point.longitude
    # Use coordinate-based terrain (matches training)
    terrain = estimate_terrain_from_coords(lat, lon)
    # Use climatology for weather (fast, matches training v2)
    weather = monthly_climatology(lat, lon)
    # Use placeholder for soil moisture and NDVI (training used 50, 0.55)
    return pd.DataFrame([{
        "latitude": lat,
        "longitude": lon,
        "elevation_m": terrain["elevation_m"],
        "slope_deg": terrain["slope_deg"],
        "aspect_deg": terrain["aspect_deg"],
        "ndvi": 0.55,
        "soil_moisture_pct": 50.0,
        "rainfall_1h_mm": weather["rainfall_1h_mm"],
        "rainfall_6h_mm": weather["rainfall_6h_mm"],
        "rainfall_24h_mm": weather["rainfall_24h_mm"],
        "rainfall_72h_mm": weather["rainfall_72h_mm"],
        "forecast_24h_mm": weather["forecast_24h_mm"],
        "forecast_72h_mm": weather["forecast_72h_mm"],
        "temperature_c": weather["temperature_c"],
        "humidity_pct": weather["humidity_pct"],
        "historical_landslide_count": int(historical_count),
        "land_cover": "forest",
    }])


def _build_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the same feature engineering as training."""
    from datetime import datetime
    out = df.copy()
    # Add monsoon features (use current month)
    month = datetime.now().month
    out["event_month"] = month
    out["monsoon"] = int(month in [6, 7, 8, 9])
    out["month_sin"] = float(np.sin(2 * np.pi * month / 12))
    out["month_cos"] = float(np.cos(2 * np.pi * month / 12))
    # Interactions
    out["rain_x_slope"] = out["rainfall_72h_mm"] * out["slope_deg"]
    out["rain_x_soil"] = out["rainfall_24h_mm"] * out["soil_moisture_pct"] / 100.0
    out["rain_x_elev"] = out["rainfall_72h_mm"] * (1.0 / (1.0 + out["elevation_m"] / 1000.0))
    # Cumulative rain
    out["rain_pressure"] = (
        out["rainfall_1h_mm"] * 4.0 + out["rainfall_6h_mm"] * 3.0 +
        out["rainfall_24h_mm"] * 2.0 + out["rainfall_72h_mm"] * 1.0
    )
    # Forecast stress
    out["forecast_stress"] = out["forecast_72h_mm"] / (out["rainfall_72h_mm"] + 1.0)
    # Slope classes
    out["slope_high"] = int(out["slope_deg"].iloc[0] > 30)
    out["slope_steep"] = int(out["slope_deg"].iloc[0] > 45)
    # Elevation
    out["elev_low"] = int(out["elevation_m"].iloc[0] < 1000)
    out["elev_mid"] = int(1000 <= out["elevation_m"].iloc[0] < 2000)
    # Historical
    out["log_hist"] = float(np.log1p(out["historical_landslide_count"].iloc[0]))
    # NDVI inverse
    out["low_veg"] = 1.0 - out["ndvi"].iloc[0]
    # Severity (no real data at inference, use 0)
    out["severity"] = 0
    # Aspect
    out["aspect_north"] = float(np.cos(np.radians(out["aspect_deg"].iloc[0])))
    out["aspect_east"] = float(np.sin(np.radians(out["aspect_deg"].iloc[0] - 90)))
    return out


def _latest_promoted_version() -> Optional[str]:
    reg = REGISTRY_DIR
    if not reg.exists():
        return None
    candidates = list(reg.glob("*.metadata.json"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0].stem.replace(".metadata", "")


def load_latest() -> ModelBundle:
    version = _latest_promoted_version()
    if version is None:
        raise ModelNotFoundError("no models in ml/artifacts/registry/")
    for suffix in ["", "_v2"]:
        model_path = REGISTRY_DIR / f"{version}{suffix}.pkl"
        meta_path = REGISTRY_DIR / f"{version}{suffix}.metadata.json"
        schema_path = REGISTRY_DIR / f"{version}{suffix}.feature_schema.json"
        if model_path.exists() and meta_path.exists() and schema_path.exists():
            continue
    model_path = REGISTRY_DIR / f"{version}.pkl"
    meta_path = REGISTRY_DIR / f"{version}.metadata.json"
    schema_path = REGISTRY_DIR / f"{version}.feature_schema.json"
    if not (model_path.exists() and meta_path.exists() and schema_path.exists()):
        raise ModelNotFoundError(f"missing artifacts for {version}")
    model = joblib.load(model_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return ModelBundle(
        model_version=meta.get("model_version", version),
        algorithm=meta.get("algorithm", "ensemble"),
        model=model,
        feature_columns=meta.get("feature_columns", []),
        schema=None,
    )


def predict_proba(bundle: ModelBundle, point, historical_count: int = 0) -> float:
    """Predict P(landslide) for a point using the v2 model."""
    df = _features_for_point(point, historical_count=historical_count)
    df = _build_engineered_features(df)
    # Get the actual model (handles both dict and direct)
    if isinstance(bundle.model, dict):
        actual_model = bundle.model["model"]
        actual_features = bundle.model.get("feature_columns", bundle.feature_columns)
    else:
        actual_model = bundle.model
        actual_features = bundle.feature_columns
    # Reorder columns to match training
    X = df.reindex(columns=actual_features, fill_value=0.0)
    return float(actual_model.predict_proba(X)[:, 1][0])
