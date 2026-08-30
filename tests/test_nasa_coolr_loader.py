"""Test for NASA COOLR loader."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from ml.datasets.loaders.nasa_coolr import NasaCoolrLoader, NER_LAT_RANGE, NER_LON_RANGE


@pytest.fixture
def sample_csv(tmp_path: Path) -> Path:
    """Create a minimal sample NASA COOLR CSV for testing."""
    csv_path = tmp_path / "nasa_coolr_sample.csv"
    data = {
        "source_name": ["AGU", "News", "Report"],
        "event_id": [1, 2, 3],
        "event_date": ["08-01-2014 00:00", "07-15-2018 00:00", "06-20-2020 00:00"],
        "latitude": [26.1445, 25.5, 24.8],  # All in NER bbox
        "longitude": [91.7362, 92.0, 93.5],  # All in NER bbox
        "country_name": ["India", "India", "India"],
        "country_code": ["IN", "IN", "IN"],
        "admin_division_name": ["Assam", "Manipur", "Nagaland"],
        "landslide_category": ["landslide", "mudslide", "landslide"],
        "landslide_trigger": ["rain", "rain", "continuous_rain"],
        "landslide_size": ["medium", "small", "large"],
        "fatality_count": [5, 0, 12],
    }
    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False)
    return csv_path


def test_loader_returns_dataframe(sample_csv: Path):
    loader = NasaCoolrLoader(sample_csv)
    df = loader.load()
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert "landslide_occurred" in df.columns


def test_loader_creates_negative_samples(sample_csv: Path):
    loader = NasaCoolrLoader(sample_csv)
    df = loader.load()
    positives = df[df["landslide_occurred"] == 1]
    negatives = df[df["landslide_occurred"] == 0]
    assert len(positives) >= 3
    assert len(negatives) >= 3 * 3  # ratio=3
    assert len(negatives) > len(positives)


def test_loader_maps_severity(sample_csv: Path):
    loader = NasaCoolrLoader(sample_csv)
    df = loader.load()
    positives = df[df["landslide_occurred"] == 1]
    severities = positives["severity"].tolist()
    assert 2 in severities  # medium -> 2
    assert 1 in severities  # small -> 1
    assert 3 in severities  # large -> 3


def test_loader_ner_bbox_filter(tmp_path: Path):
    """Events outside NER bbox should be filtered out."""
    csv_path = tmp_path / "mixed.csv"
    data = {
        "event_id": [1, 2, 3, 4],
        "event_date": ["08-01-2014 00:00"] * 4,
        "latitude": [26.0, 25.0, 40.0, 35.0],  # 2 in NER, 2 outside
        "longitude": [91.0, 92.0, 120.0, 100.0],
        "country_name": ["India"] * 4,
        "admin_division_name": ["Assam", "Manipur", "Beijing", "Tokyo"],
        "landslide_size": ["medium"] * 4,
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)

    loader = NasaCoolrLoader(csv_path, ner_only=True)
    df = loader.load()
    positives = df[df["landslide_occurred"] == 1]
    assert len(positives) == 2  # Only the 2 NER events


def test_loader_year_filter(tmp_path: Path):
    """Events outside year range should be filtered."""
    csv_path = tmp_path / "years.csv"
    data = {
        "event_id": [1, 2, 3],
        "event_date": ["08-01-2005 00:00", "08-01-2018 00:00", "08-01-2023 00:00"],
        "latitude": [26.0, 25.0, 24.5],
        "longitude": [91.0, 92.0, 93.0],
        "country_name": ["India"] * 3,
        "admin_division_name": ["Assam"] * 3,
        "landslide_size": ["medium"] * 3,
    }
    pd.DataFrame(data).to_csv(csv_path, index=False)

    loader = NasaCoolrLoader(csv_path, min_year=2010, max_year=2020)
    df = loader.load()
    positives = df[df["landslide_occurred"] == 1]
    assert len(positives) == 1  # Only 2018 event


def test_to_training_format(sample_csv: Path):
    loader = NasaCoolrLoader(sample_csv)
    df = loader.load()
    train_df = loader.to_training_format(df)
    expected_cols = {
        "latitude", "longitude", "historical_landslide_count",
        "land_cover", "landslide_occurred",
    }
    assert expected_cols.issubset(set(train_df.columns))
    assert len(train_df) == len(df)
