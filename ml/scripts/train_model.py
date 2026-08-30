"""Train models and register them.

Reads training data from one of three sources (in order of preference):
  1. --loader LOADER_NAME: Use a registered loader (e.g. nasa_coolr)
  2. --csv PATH: Read a pre-built CSV file
  3. Default: Build synthetic dataset

Trains RF + XGBoost, picks the better one by PR-AUC, persists artifacts,
and registers both in the DB.

Usage:
    # Train on real NASA COOLR data:
    python -m ml.scripts.train_model --loader nasa_coolr --data data/raw/nasa_coolr.csv

    # Train on pre-built CSV:
    python -m ml.scripts.train_model --csv data/processed/synthetic_dataset.csv

    # Train on synthetic data (default):
    python -m ml.scripts.train_model
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

import pandas as pd  # noqa: E402

from app.core.logging import configure_logging, get_logger  # noqa: E402
from ml.datasets.synthetic import BuildConfig, build_synthetic_dataframe  # noqa: E402
from ml.features import FeatureSchema  # noqa: E402
from ml.train import persist, register_in_db, train_and_compare  # noqa: E402

DEFAULT_CSV = REPO_ROOT / "data" / "processed" / "synthetic_dataset.csv"
DEFAULT_NASA_CSV = REPO_ROOT / "data" / "raw" / "nasa_coolr_sample.csv"

log = get_logger("app.ml.train")


def load_training_data(args) -> tuple[pd.DataFrame, str]:
    """Load training data based on args. Returns (df, source_description)."""

    # Option 1: Use a named loader (e.g. nasa_coolr)
    if args.loader:
        from ml.datasets.loaders import get_loader
        log.info("using_loader", loader=args.loader, data=args.data)
        loader = get_loader(args.loader, csv_path=args.data)
        df = loader.load()
        return df, f"loader:{args.loader}:{args.data}"

    # Option 2: Use a pre-built CSV
    if args.csv.exists():
        log.info("loading_csv", path=str(args.csv))
        return pd.read_csv(args.csv), f"csv:{args.csv}"

    # Option 3: Build synthetic data
    log.info("building_synthetic_dataset")
    cfg = BuildConfig(n_points=args.n_points, seed=args.seed)
    return build_synthetic_dataframe(cfg), f"synthetic:n={args.n_points}"


def main() -> int:
    configure_logging("INFO")
    p = argparse.ArgumentParser(description="Train landslide risk models")
    p.add_argument(
        "--loader", type=str, default=None,
        help="Use a registered loader (e.g. nasa_coolr). Requires --data.",
    )
    p.add_argument(
        "--data", type=str, default=str(DEFAULT_NASA_CSV),
        help="Path to the data file for the loader.",
    )
    p.add_argument(
        "--csv", type=Path, default=DEFAULT_CSV,
        help="Path to a pre-built training CSV.",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n-points", type=int, default=600, help="Synthetic points if no data found")
    p.add_argument("--no-promote", action="store_true", help="Register but do not mark promoted")
    args = p.parse_args()

    df, source = load_training_data(args)
    log.info("training_data_loaded", rows=len(df), source=source)

    if "landslide_occurred" not in df.columns:
        print("ERROR: loaded data has no `landslide_occurred` column", file=sys.stderr)
        return 2

    pos_count = int(df["landslide_occurred"].sum())
    neg_count = len(df) - pos_count
    log.info("class_balance", positive=pos_count, negative=neg_count)

    if pos_count < 10:
        print(f"WARNING: only {pos_count} positive samples. Model may not train well.", file=sys.stderr)

    schema = FeatureSchema()
    rf, xgb, chosen = train_and_compare(df, schema, seed=args.seed)
    print(f"\n=== Random Forest metrics ===\n{json.dumps(rf.metrics, indent=2)}")
    if xgb.model_object is not None:
        print(f"\n=== XGBoost metrics ===\n{json.dumps(xgb.metrics, indent=2)}")

    chosen_model = xgb if chosen == "xgboost" else rf
    paths = persist(chosen_model, schema, training_dataset=source)
    print(f"\npersisted {chosen_model.algorithm} -> {paths}")
    register_in_db(chosen_model, paths, schema, promoted=not args.no_promote)

    # Also register the other one (un-promoted) for the record
    other = rf if chosen != "random_forest" else None
    if other is not None and other.model_object is not None:
        other_paths = persist(other, schema, training_dataset=source)
        register_in_db(other, other_paths, schema, promoted=False)

    print(f"\nchosen model: {chosen_model.model_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
