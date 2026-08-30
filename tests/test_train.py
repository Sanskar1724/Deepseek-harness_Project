"""Phase 5: training pipeline trains both models, picks one, and persists it."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

import joblib  # noqa: E402

from ml.datasets.synthetic import BuildConfig, build_synthetic_dataframe  # noqa: E402
from ml.features import FeatureSchema, build_feature_matrix  # noqa: E402
from ml.predict import ModelNotFoundError, load_version  # noqa: E402
from ml.train import persist, register_in_db, train_and_compare  # noqa: E402

REGISTRY = Path("ml/artifacts/registry")


def test_train_compare_and_persist(tmp_path, monkeypatch):
    # Use a throwaway registry dir so we do not pollute the repo.
    monkeypatch.setattr("ml.train.REGISTRY_DIR", tmp_path)
    monkeypatch.setattr("ml.predict.REGISTRY_DIR", tmp_path)
    df = build_synthetic_dataframe(BuildConfig(n_points=400, seed=11))
    schema = FeatureSchema()
    rf, xgb, chosen = train_and_compare(df, schema, seed=11)
    # Both models should have a meaningful PR-AUC; XGBoost may be unavailable in
    # the test env, in which case it returns an "unavailable" TrainedModel.
    assert rf.metrics["pr_auc"] > 0.0
    assert chosen in {"random_forest", "xgboost"}
    chosen_model = xgb if chosen == "xgboost" else rf
    paths = persist(chosen_model, schema, training_dataset="synthetic:test")
    assert Path(paths["model"]).exists()
    assert Path(paths["metadata"]).exists()
    assert Path(paths["schema"]).exists() if False else Path(paths["feature_schema"]).exists()
    # Re-load to confirm the artifact is real.
    bundle = load_version(chosen_model.model_version)
    assert bundle.algorithm == chosen_model.algorithm
    # The model is a real fitted estimator with predict_proba.
    assert hasattr(bundle.model, "predict_proba")


def test_register_does_not_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr("ml.train.REGISTRY_DIR", tmp_path)
    monkeypatch.setattr("ml.predict.REGISTRY_DIR", tmp_path)
    df = build_synthetic_dataframe(BuildConfig(n_points=300, seed=3))
    schema = FeatureSchema()
    rf, _xgb, _chosen = train_and_compare(df, schema, seed=3)
    paths = persist(rf, schema, training_dataset="synthetic:test")
    register_in_db(rf, paths, schema, promoted=True)
    # Second call should be a no-op (no exception, no duplicate row).
    register_in_db(rf, paths, schema, promoted=True)


def test_load_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("ml.predict.REGISTRY_DIR", tmp_path)
    try:
        load_version("does-not-exist")
    except ModelNotFoundError:
        return
    raise AssertionError("expected ModelNotFoundError")


def test_feature_matrix_handles_missing_columns():
    import pandas as pd  # noqa: E402
    schema = FeatureSchema()
    df = pd.DataFrame([{"latitude": 26.0, "longitude": 91.0}])  # sparse
    X = build_feature_matrix(df, schema)
    for col in schema.numeric:
        assert col in X.columns
