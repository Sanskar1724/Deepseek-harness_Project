# Data

This directory holds raw and processed data files. It is **gitignored** except
for the `.gitkeep` placeholders.

## What goes here
- `data/raw/`     — source data dumps (e.g. GSI Bhukosh export, IMD rainfall
  CSV, OSM PBF for NER).
- `data/processed/` — derived, normalised training frames produced by
  `ml/scripts/build_dataset.py`.

## Current state
No real NER data is bundled. Phase 4 will create a **clearly-labelled synthetic
dataset** under `data/processed/` so the rest of the pipeline can be exercised.
The UI will display a DEMO/SYNTHETIC banner so the numbers are never mistaken
for real forecasts.

## How real data will be plugged in
1. Drop files into `data/raw/`.
2. Update `ml/scripts/build_dataset.py` to read them (or add a new loader under
   `ml/datasets/loaders/`).
3. Re-run training: `python ml/scripts/train_model.py`.
4. The new model lands in `ml/artifacts/registry/` and is promoted in the
   `model_registry` table only after evaluation metrics pass review.
