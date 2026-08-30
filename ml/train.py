"""Training pipeline.

Trains a Random Forest and an XGBoost on the same data, picks the one with the
better PR-AUC on a held-out set, and registers both + the chosen one in the DB.

Master prompt §11: we report precision, recall, F1, ROC-AUC, PR-AUC, and the
confusion matrix for both, with extra emphasis on recall for the positive class
(landslide), because this is an early-warning system.
"""
from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, train_test_split

# XGBoost is optional: if it is not installed, we still train RF and report that.
try:
    from xgboost import XGBClassifier  # type: ignore
    HAS_XGB = True
except Exception:  # noqa: BLE001
    HAS_XGB = False

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models import ModelRegistry
from ml.features import FeatureSchema, build_feature_matrix

log = get_logger("app.ml")

REGISTRY_DIR = Path(__file__).resolve().parent / "artifacts" / "registry"
REGISTRY_DIR.mkdir(parents=True, exist_ok=True)


class TrainingDataError(RuntimeError):
    pass


def _confusion_dict(y_true, y_pred) -> Dict[str, int]:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel().tolist()
    return {"tn": tn, "fp": fp, "fn": fn, "tp": tp}


def _metrics(y_true, y_proba) -> Dict[str, float]:
    y_pred = (y_proba >= 0.5).astype(int)
    p, r, f, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    return {
        "precision": float(p),
        "recall": float(r),
        "f1": float(f),
        "roc_auc": float(roc_auc_score(y_true, y_proba)) if len(set(y_true)) > 1 else 0.0,
        "pr_auc": float(average_precision_score(y_true, y_proba))
        if len(set(y_true)) > 1
        else 0.0,
        "confusion_matrix": _confusion_dict(y_true, y_pred),
    }


@dataclass
class TrainedModel:
    algorithm: str
    model_version: str
    model_object: object
    metrics: Dict[str, float]
    feature_columns: list
    trained_at: datetime


def _train_one(name: str, estimator, X_tr, y_tr, X_te, y_te) -> TrainedModel:
    # Fit with calibration for better probability (good prediction not just 0/1)
    # Use 3-fold CV calibration if enough samples
    if len(y_tr) >= 60:
        try:
            calib = CalibratedClassifierCV(estimator, method="sigmoid", cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=42))
            calib.fit(X_tr, y_tr)
            proba = calib.predict_proba(X_te)[:, 1]
            metrics = _metrics(y_te, proba)
            version = f"{name}-calibrated-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            log.info("trained_calibrated", algorithm=name, mv_name=version, **{k: metrics[k] for k in metrics if k != "confusion_matrix"})
            return TrainedModel(
                algorithm=name,
                model_version=version,
                model_object=calib,
                metrics=metrics,
                feature_columns=list(X_tr.columns),
                trained_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            log.warning("calibration_failed_fallback", algorithm=name, error=str(e))
    # Fallback without calibration
    estimator.fit(X_tr, y_tr)
    proba = estimator.predict_proba(X_te)[:, 1]
    metrics = _metrics(y_te, proba)
    version = f"{name}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    log.info("trained", algorithm=name, version=version, **{k: metrics[k] for k in metrics if k != "confusion_matrix"})
    return TrainedModel(
        algorithm=name,
        model_version=version,
        model_object=estimator,
        metrics=metrics,
        feature_columns=list(X_tr.columns),
        trained_at=datetime.now(timezone.utc),
    )


def train_and_compare(df: pd.DataFrame, schema: FeatureSchema, *, seed: int = 42) -> Tuple[TrainedModel, TrainedModel, str]:
    if schema.target not in df.columns:
        raise TrainingDataError(f"target column {schema.target!r} missing")
    if len(df) < 50:
        raise TrainingDataError(f"need at least 50 rows, got {len(df)}")
    if df[schema.target].nunique() < 2:
        raise TrainingDataError("target has only one class; cannot train a classifier")

    # Huge data efficient: sample if >5000 to avoid OOM, keep stratify
    if len(df) > 5000:
        log.warning("huge_data_sampled", original=len(df), sampled=5000)
        df = df.sample(n=5000, random_state=seed, weights=None).reset_index(drop=True)
        # keep class balance via stratify in split

    X = build_feature_matrix(df, schema)
    y = df[schema.target].astype(int).to_numpy()
    # Huge: use larger test 0.2 for more train data, else 0.25
    test_size = 0.2 if len(df) > 1000 else 0.25
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=test_size, random_state=seed, stratify=y
    )
    log.info("train_split", n_total=len(df), n_train=len(X_tr), n_test=len(X_te), pos_train=int(y_tr.sum()), pos_test=int(y_te.sum()))

    # STRONG + HUGE efficient: scale with data size, hist for XGB
    n = len(df)
    # Scale estimators with data: 600->400/500, 5000->600/800, huge uses hist
    rf_est = 400 if n < 1000 else 600 if n < 3000 else 800
    xgb_est = 500 if n < 1000 else 800 if n < 3000 else 1000
    rf_depth = 18 if n < 1000 else 20
    xgb_depth = 7 if n < 1000 else 8
    rf = _train_one(
        "random_forest",
        RandomForestClassifier(
            n_estimators=rf_est,
            max_depth=rf_depth,
            min_samples_split=3,
            min_samples_leaf=2,
            max_features="sqrt",
            n_jobs=-1,
            random_state=seed,
            class_weight="balanced_subsample",
        ),
        X_tr, y_tr, X_te, y_te,
    )

    if HAS_XGB:
        xgb = _train_one(
            "xgboost",
            XGBClassifier(
                n_estimators=xgb_est,
                max_depth=xgb_depth,
                learning_rate=0.04,
                subsample=0.88,
                colsample_bytree=0.88,
                colsample_bylevel=0.9,
                reg_alpha=0.05,
                reg_lambda=1.2,
                min_child_weight=3,
                gamma=0.1,
                tree_method="hist",  # efficient for huge
                eval_metric="logloss",
                random_state=seed,
                n_jobs=-1,
            ),
            X_tr, y_tr, X_te, y_te,
        )
        chosen = "xgboost" if xgb.metrics["pr_auc"] >= rf.metrics["pr_auc"] else "random_forest"
        return rf, xgb, chosen

    log.warning("xgboost_unavailable")
    return rf, TrainedModel(
        algorithm="xgboost",
        model_version="unavailable",
        model_object=None,
        metrics={},
        feature_columns=list(X_tr.columns),
        trained_at=datetime.now(timezone.utc),
    ), "random_forest"


def persist(model: TrainedModel, schema: FeatureSchema, *, training_dataset: str) -> Dict[str, str]:
    """Save model.pkl, model_metadata.json, feature_schema.json.

    Returns the dict of paths written.
    """
    if model.model_object is None:
        raise TrainingDataError("refusing to persist a model that did not train")
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    model_path = REGISTRY_DIR / f"{model.model_version}.pkl"
    meta_path = REGISTRY_DIR / f"{model.model_version}.metadata.json"
    schema_path = REGISTRY_DIR / f"{model.model_version}.feature_schema.json"
    joblib.dump(model.model_object, model_path)
    meta = {
        "model_version": model.model_version,
        "algorithm": model.algorithm,
        "trained_at": model.trained_at.isoformat(),
        "metrics": model.metrics,
        "feature_columns": model.feature_columns,
        "training_dataset": training_dataset,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    schema_path.write_text(schema.to_json(), encoding="utf-8")
    return {
        "model": str(model_path),
        "metadata": str(meta_path),
        "feature_schema": str(schema_path),
    }


def register_in_db(model: TrainedModel, paths: Dict[str, str], schema: FeatureSchema, *, promoted: bool) -> None:
    """Append a row to model_registry. Never overwrite an existing version."""
    with SessionLocal() as db:
        existing = db.query(ModelRegistry).filter_by(model_version=model.model_version).one_or_none()
        if existing is not None:
            log.info("registry_row_already_exists", model_version=model.model_version)
            return
        row = ModelRegistry(
            model_version=model.model_version,
            algorithm=model.algorithm,
            artifact_path=paths["model"],
            training_dataset=model.metrics.get("training_dataset", "synthetic"),
            metrics_json=json.dumps(model.metrics),
            feature_schema_json=schema.to_json(),
            trained_at=model.trained_at,
            promoted=promoted,
            notes=f"python={sys.version.split()[0]}",
        )
        # In newer SQLAlchemy, training_dataset is a separate arg. Provide it explicitly.
        row.training_dataset = "synthetic"  # type: ignore[attr-defined]
        db.add(row)
        db.commit()
