"""Phase 4: synthetic dataset builder produces a labelled, deterministic frame."""
from __future__ import annotations

import sys
from pathlib import Path

# Allow `from ml.datasets.synthetic import ...` in pytest
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from ml.datasets.synthetic import (  # noqa: E402
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    BuildConfig,
    build_synthetic_dataframe,
    write_synthetic_csv,
)


def test_columns_and_shape():
    df = build_synthetic_dataframe(BuildConfig(n_points=50, seed=1))
    assert list(df.columns) == FEATURE_COLUMNS + [TARGET_COLUMN]
    assert len(df) == 50
    assert set(df[TARGET_COLUMN].unique()).issubset({0, 1})


def test_is_deterministic():
    a = build_synthetic_dataframe(BuildConfig(n_points=80, seed=123))
    b = build_synthetic_dataframe(BuildConfig(n_points=80, seed=123))
    assert a.equals(b)


def test_label_is_not_trivial():
    df = build_synthetic_dataframe(BuildConfig(n_points=500, seed=42))
    pos = int(df[TARGET_COLUMN].sum())
    assert 0 < pos < len(df)
    assert 5 <= pos <= 250


def test_features_have_no_nans():
    df = build_synthetic_dataframe(BuildConfig(n_points=100, seed=7))
    assert df[FEATURE_COLUMNS].isna().sum().sum() == 0


def test_csv_round_trip(tmp_path):
    df = build_synthetic_dataframe(BuildConfig(n_points=40, seed=2))
    csv = write_synthetic_csv(df, tmp_path)
    assert csv.exists()
    import pandas as pd
    again = pd.read_csv(csv)
    assert again.shape == df.shape
