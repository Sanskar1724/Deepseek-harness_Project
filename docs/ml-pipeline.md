# ML Pipeline

## Overview

The ML pipeline trains a binary classifier (landslide yes/no) on a feature
vector of 16 features, then converts the predicted probability to a 0-100
risk score via the risk engine.

## Features (16)

| Feature | Source | Type |
|---------|--------|------|
| latitude, longitude | location | float |
| elevation_m | DEM/terrain provider | float |
| slope_deg | DEM/terrain provider | float |
| aspect_deg | DEM/terrain provider | float |
| ndvi | satellite provider | float |
| soil_moisture_pct | soil provider | float |
| rainfall_1h, 6h, 24h, 72h_mm | rainfall provider | float |
| forecast_24h, 72h_mm | weather provider | float |
| temperature_c | weather provider | float |
| humidity_pct | weather provider | float |
| historical_landslide_count | landslide provider (or DB) | int |
| land_cover | satellite provider | categorical |

## Training

Two models are trained and compared:
- Random Forest (200 trees, max_depth=12, class_weight=balanced)
- XGBoost (300 trees, max_depth=6, learning_rate=0.08) if available

The model with higher PR-AUC is promoted in `model_registry`.

## Metrics

Precision, Recall, F1, ROC-AUC, PR-AUC, confusion matrix are logged.
Recall for the positive class (landslide) is emphasized because this is an
early-warning system: false negatives are worse than false positives.

## Artifacts

Written to `ml/artifacts/registry/<version>.{pkl,metadata.json,feature_schema.json}`.
Versions are timestamped; nothing is silently overwritten.

## Known Limitations

- Training data is synthetic (see `docs/limitations.md`).
- No cross-validation (single train/test split) for speed.
- No hyperparameter tuning.
- `score_from_proba(p) = round(p * 100)` is a linear mapping; no calibration.