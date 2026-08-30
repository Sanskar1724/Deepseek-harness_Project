"""Predict risk for a single location using a registered model.

Loads `model.pkl` and `feature_schema.json` from `ml/artifacts/registry/`
and returns a probability in [0, 1] for a landslide occurring. The risk engine
turns that probability into a 0-100 score with the configured thresholds.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

from app.providers import (
    Point,
    get_rainfall_provider,
    get_satellite_provider,
    get_soil_provider,
    get_terrain_provider,
    get_weather_provider,
)
from ml.features import FeatureSchema, build_feature_matrix

REGISTRY_DIR = Path(__file__).resolve().parent / "artifacts" / "registry"
REGISTRY_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_registry_dir() -> Path:
    """Return the active registry dir, respecting monkeypatched ml.train.REGISTRY_DIR in tests."""
    try:
        from ml import train as _train  # local import to avoid circular at import time

        return Path(_train.REGISTRY_DIR)
    except Exception:
        return REGISTRY_DIR


class ModelNotFoundError(FileNotFoundError):
    pass


@dataclass
class ModelBundle:
    model_version: str
    algorithm: str
    model: object
    feature_columns: list
    schema: FeatureSchema


def _latest_promoted_version() -> Optional[str]:
    """Return the model version with the lexicographically-largest name, as a
    cheap stand-in for "most recently trained". A real deployment should use
    `model_registry.promoted = 1`; we honour both by preferring any version that
    has a metadata file newer than the others.
    """
    reg = _resolve_registry_dir()
    # also consider the local REGISTRY_DIR for backward-compat
    candidates: list[Path] = []
    for d in {reg, REGISTRY_DIR}:
        if d.exists():
            candidates.extend(d.glob("*.metadata.json"))
    if not candidates:
        return None
    # Sort by modification time, most recent first
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0].stem.replace(".metadata", "")


def load_latest() -> ModelBundle:
    version = _latest_promoted_version()
    if version is None:
        raise ModelNotFoundError("no models in ml/artifacts/registry/; run ml.scripts.train_model first")
    return load_version(version)


def load_version(version: str) -> ModelBundle:
    for reg in [_resolve_registry_dir(), REGISTRY_DIR]:
        model_path = reg / f"{version}.pkl"
        meta_path = reg / f"{version}.metadata.json"
        schema_path = reg / f"{version}.feature_schema.json"
        if model_path.exists() and meta_path.exists() and schema_path.exists():
            model = joblib.load(model_path)
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            schema = FeatureSchema.from_json(schema_path.read_text(encoding="utf-8"))
            return ModelBundle(
                model_version=meta["model_version"],
                algorithm=meta.get("algorithm", "ensemble"),
                model=model,
                feature_columns=meta.get("feature_columns", list(schema.all_inputs)),
                schema=schema,
            )
    raise ModelNotFoundError(f"missing artifacts for {version}")


def _features_for_point(point: Point) -> pd.DataFrame:
    """Build a one-row DataFrame of features for a single point.

    The risk engine calls this. We pull from the registered providers and the
    schema in the saved model bundle.
    """
    snap = get_weather_provider().get_snapshot(point)
    terr = get_terrain_provider().get_terrain(point)
    sat = get_satellite_provider().get_attributes(point)
    soil = get_soil_provider().get_soil(point)
    rain = get_rainfall_provider().get_series(point)
    return pd.DataFrame(
        [
            {
                "latitude": point.latitude,
                "longitude": point.longitude,
                "elevation_m": terr.elevation_m,
                "slope_deg": terr.slope_deg,
                "aspect_deg": terr.aspect_deg,
                "ndvi": sat.ndvi,
                "soil_moisture_pct": soil.soil_moisture_pct,
                "rainfall_1h_mm": rain.rainfall_1h,
                "rainfall_6h_mm": rain.rainfall_6h,
                "rainfall_24h_mm": rain.rainfall_24h,
                "rainfall_72h_mm": rain.rainfall_72h,
                "forecast_24h_mm": rain.forecast_24h,
                "forecast_72h_mm": rain.forecast_72h,
                "temperature_c": snap.observed.temperature_c,
                "humidity_pct": snap.observed.humidity_pct,
                "historical_landslide_count": 0,  # filled by caller if known
                "land_cover": sat.land_cover,
            }
        ]
    )




def _engineer_features_for_inference(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the same feature engineering as training, for inference."""
    out = df.copy()
    if "rainfall_72h_mm" in out.columns and "slope_deg" in out.columns:
        out["rain_x_slope"] = out["rainfall_72h_mm"] * out["slope_deg"]
    if "rainfall_24h_mm" in out.columns and "soil_moisture_pct" in out.columns:
        out["rain_x_soil"] = out["rainfall_24h_mm"] * out["soil_moisture_pct"] / 100.0
    if "rainfall_72h_mm" in out.columns and "elevation_m" in out.columns:
        out["rain_x_elev"] = out["rainfall_72h_mm"] * (1.0 / (1.0 + out["elevation_m"] / 1000.0))
    if all(c in out.columns for c in ["rainfall_1h_mm", "rainfall_6h_mm", "rainfall_24h_mm", "rainfall_72h_mm"]):
        out["rain_pressure"] = (
            out["rainfall_1h_mm"] * 4.0 + out["rainfall_6h_mm"] * 3.0 +
            out["rainfall_24h_mm"] * 2.0 + out["rainfall_72h_mm"] * 1.0
        )
    if "forecast_72h_mm" in out.columns and "rainfall_72h_mm" in out.columns:
        out["forecast_stress"] = out["forecast_72h_mm"] / (out["rainfall_72h_mm"] + 1.0)
    if "slope_deg" in out.columns:
        out["slope_high"] = (out["slope_deg"] > 30).astype(int)
        out["slope_steep"] = (out["slope_deg"] > 45).astype(int)
    if "elevation_m" in out.columns:
        out["elev_low"] = (out["elevation_m"] < 1000).astype(int)
        out["elev_mid"] = ((out["elevation_m"] >= 1000) & (out["elevation_m"] < 2000)).astype(int)
    if "historical_landslide_count" in out.columns:
        out["log_hist"] = np.log1p(out["historical_landslide_count"])
    if "ndvi" in out.columns:
        out["low_veg"] = 1.0 - out["ndvi"]
    if "aspect_deg" in out.columns:
        out["aspect_north"] = np.cos(np.radians(out["aspect_deg"] - 0))
    return out


def predict_proba(bundle: ModelBundle, point: Point, historical_count: int = 0) -> float:
    """Return P(landslide) for a single point. Handles both old and new model formats."""
    df = _features_for_point(point)
    df["historical_landslide_count"] = int(historical_count)
    # If model was trained with engineered features, apply them too
    if any(col in bundle.feature_columns for col in ["rain_x_slope", "rain_pressure", "forecast_stress"]):
        df = _engineer_features_for_inference(df)
    X = build_feature_matrix(df, bundle.schema)
    # Handle new model format: bundle is a dict {model, feature_columns}
    if isinstance(bundle.model, dict) and "model" in bundle.model:
        actual_model = bundle.model["model"]
        actual_features = bundle.model.get("feature_columns", bundle.feature_columns)
    else:
        actual_model = bundle.model
        actual_features = bundle.feature_columns
    X = X.reindex(columns=actual_features, fill_value=0.0).to_numpy()
    return float(actual_model.predict_proba(X)[:, 1][0])