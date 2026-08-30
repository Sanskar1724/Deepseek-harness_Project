"""Feature schema + transform from raw DataFrame to model inputs.

This module is the single source of truth for what columns the model expects
and in what order. Anything that wants to call `model.predict_proba(X)` must
build X through `build_feature_matrix`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import pandas as pd

# Same order as the synthetic builder. Real-data loaders must conform.
NUMERIC_FEATURES: List[str] = [
    "latitude",
    "longitude",
    "elevation_m",
    "slope_deg",
    "aspect_deg",
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
CATEGORICAL_FEATURES: List[str] = ["land_cover"]
TARGET_COLUMN = "landslide_occurred"


@dataclass
class FeatureSchema:
    numeric: List[str] = field(default_factory=lambda: list(NUMERIC_FEATURES))
    categorical: List[str] = field(default_factory=lambda: list(CATEGORICAL_FEATURES))
    target: str = TARGET_COLUMN

    @property
    def all_inputs(self) -> List[str]:
        return self.numeric + self.categorical

    def to_json(self) -> str:
        return json.dumps(
            {"numeric": self.numeric, "categorical": self.categorical, "target": self.target},
            indent=2,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, s: str) -> "FeatureSchema":
        d = json.loads(s)
        return cls(numeric=d["numeric"], categorical=d["categorical"], target=d["target"])


def build_feature_matrix(df: pd.DataFrame, schema: FeatureSchema) -> pd.DataFrame:
    """Return a DataFrame with the schema columns, in order, with categoricals
    one-hot-encoded. Missing columns are filled with safe defaults.
    """
    out = pd.DataFrame(index=df.index)
    for col in schema.numeric:
        if col in df.columns:
            out[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        else:
            out[col] = 0.0
    if schema.categorical:
        present = [c for c in schema.categorical if c in df.columns]
        if present:
            dummies = pd.get_dummies(df[present].astype(str), prefix=present).astype(float)
            out = pd.concat([out, dummies], axis=1)
    return out.fillna(0.0)
