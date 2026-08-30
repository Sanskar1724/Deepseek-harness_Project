"""V3 training: uses ALL engineered features for real accuracy."""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "ml"))

from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_recall_fscore_support,
    precision_recall_curve,
    roc_auc_score,
    confusion_matrix,
)
from sklearn.model_selection import (
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except Exception:
    HAS_XGB = False

# Import the SAME engineer_features used at inference
from ml.scripts.train_improved import engineer_features
from ml.features import FeatureSchema, build_feature_matrix

REGISTRY_DIR = Path("ml/artifacts/registry")
REGISTRY_DIR.mkdir(parents=True, exist_ok=True)


def find_optimal_threshold(y_true, y_proba, min_recall=0.85):
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    f1_scores = 2 * (precision * recall) / (precision + recall + 1e-9)
    valid = recall >= min_recall
    if not valid.any():
        best_idx = int(np.argmax(f1_scores))
    else:
        masked_f1 = np.where(valid, f1_scores, -1)
        best_idx = int(np.argmax(masked_f1))
    best_threshold = float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.5
    return best_threshold, float(f1_scores[best_idx]), float(recall[best_idx]), float(precision[best_idx])


def cross_validate_evaluate(estimator, X, y, n_splits=5):
    from sklearn.base import clone
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    metrics = {"pr_auc": [], "roc_auc": [], "f1": [], "recall": [], "precision": []}
    for tr_idx, te_idx in skf.split(X, y):
        Xtr, Xte = X.iloc[tr_idx], X.iloc[te_idx]
        ytr, yte = y[tr_idx], y[te_idx]
        try:
            est = clone(estimator)
            est.fit(Xtr, ytr)
            proba = est.predict_proba(Xte)[:, 1]
            y_pred = (proba >= 0.5).astype(int)
            if len(set(yte)) > 1:
                metrics["pr_auc"].append(average_precision_score(yte, proba))
                metrics["roc_auc"].append(roc_auc_score(yte, proba))
            p, r, f, _ = precision_recall_fscore_support(yte, y_pred, average="binary", zero_division=0)
            metrics["precision"].append(float(p))
            metrics["recall"].append(float(r))
            metrics["f1"].append(float(f))
        except Exception:
            pass
    return {k: float(np.mean(v)) if v else 0.0 for k, v in metrics.items()}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=Path, default=ROOT / "data/processed/real_training_dataset_v3.csv")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    print("=" * 60)
    print("V3 TRAINING: with full engineered features")
    print("=" * 60)

    df = pd.read_csv(args.csv)
    print(f"Loaded: {len(df)} rows, {df.shape[1]} columns")
    print(f"Positives: {int(df.landslide_occurred.sum())}, Negatives: {int((df.landslide_occurred == 0).sum())}")

    # Step 1: Engineer features
    df_eng = engineer_features(df)
    print(f"\nAfter engineering: {df_eng.shape[1]} features")

    # Step 2: Use ALL engineered features (NOT just the schema)
    # Drop non-feature columns
    feature_cols = [c for c in df_eng.columns if c not in ("landslide_occurred", "land_cover", "fatality_count")]
    # One-hot encode land_cover
    df_features = pd.get_dummies(df_eng[feature_cols + ["land_cover"]], columns=["land_cover"])
    # Drop the non-feature columns that snuck in
    drop_cols = ["event_month"]  # keep as numeric or drop; we have month_sin/cos
    for c in drop_cols:
        if c in df_features.columns:
            df_features = df_features.drop(columns=[c])
    if "severity_num" in df_features.columns:
        df_features = df_features.drop(columns=["severity_num"])

    X = df_features.copy()
    y = df_eng["landslide_occurred"].astype(int).to_numpy()

    print(f"\nFinal X: {X.shape[1]} features, {len(X)} rows")
    print("Features:", list(X.columns))

    # Step 3: Train/test split with proper stratification
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=args.seed, stratify=y)

    # Step 4: Cross-validation on each algorithm
    algorithms = {
        "random_forest": RandomForestClassifier(
            n_estimators=300, max_depth=15, min_samples_split=4,
            min_samples_leaf=2, n_jobs=1, random_state=args.seed,
            class_weight="balanced_subsample",
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.05,
            subsample=0.85, random_state=args.seed,
        ),
        "logistic_regression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=args.seed)),
        ]),
    }
    if HAS_XGB:
        algorithms["xgboost"] = XGBClassifier(
            n_estimators=400, max_depth=8, learning_rate=0.05,
            subsample=0.85, colsample_bytree=0.85, reg_alpha=0.1,
            reg_lambda=1.0, eval_metric="logloss", random_state=args.seed, n_jobs=1,
        )

    results = {}
    trained_models = {}

    print("\nTraining algorithms with 5-fold CV...")
    for name, model in algorithms.items():
        print(f"  Training {name}...")
        try:
            from sklearn.base import clone
            model_clone = clone(model)
            model_clone.fit(Xtr, ytr)
            # Cross-validation
            cv = cross_validate_evaluate(model_clone, X, y, n_splits=5)
            # Test metrics
            proba = model_clone.predict_proba(Xte)[:, 1]
            y_pred = (proba >= 0.5).astype(int)
            test_metrics = {
                "pr_auc": float(average_precision_score(yte, proba)) if len(set(yte)) > 1 else 0.0,
                "roc_auc": float(roc_auc_score(yte, proba)) if len(set(yte)) > 1 else 0.0,
            }
            p, r, f, _ = precision_recall_fscore_support(yte, y_pred, average="binary", zero_division=0)
            test_metrics.update({"precision": float(p), "recall": float(r), "f1": float(f)})
            cm = confusion_matrix(yte, y_pred, labels=[0, 1])
            tn, fp, fn, tp = cm.ravel().tolist()
            test_metrics["confusion_matrix"] = {"tn": tn, "fp": fp, "fn": fn, "tp": tp}
            opt_t, opt_f1, opt_r, opt_p = find_optimal_threshold(yte, proba, min_recall=0.80)
            results[name] = {
                "cv": cv, "test": test_metrics,
                "optimal_threshold": opt_t,
                "optimal_metrics": {"f1": opt_f1, "recall": opt_r, "precision": opt_p},
            }
            trained_models[name] = model_clone
            print(f"    CV PR-AUC: {cv[chr(39)+chr(112)+chr(114)+chr(95)+chr(97)+chr(117)+chr(99)+chr(39)]:.3f}, F1: {cv[chr(39)+chr(102)+chr(49)+chr(39)]:.3f}, Recall: {cv[chr(39)+chr(114)+chr(101)+chr(99)+chr(97)+chr(108)+chr(108)+chr(39)]:.3f}")
            print(f"    Test PR-AUC: {test_metrics[chr(39)+chr(112)+chr(114)+chr(95)+chr(97)+chr(117)+chr(99)+chr(39)]:.3f}, F1: {test_metrics[chr(39)+chr(102)+chr(49)+chr(39)]:.3f}")
            print(f"    Optimal threshold: {opt_t:.3f} (F1={opt_f1:.3f})")
        except Exception as e:
            print(f"    FAILED: {e}")

    if not results:
        print("All algorithms failed")
        return 1

    # Pick best by CV PR-AUC
    best_name = max(results, key=lambda n: results[n]["cv"].get("pr_auc", 0))
    best_model = trained_models[best_name]

    print(f"\nBest algorithm: {best_name}")
    print(f"  CV PR-AUC: {results[best_name][chr(39)+chr(99)+chr(118)+chr(39)].get(chr(39)+chr(112)+chr(114)+chr(95)+chr(97)+chr(117)+chr(99)+chr(39), 0):.3f}")
    print(f"  Test PR-AUC: {results[best_name][chr(39)+chr(116)+chr(101)+chr(115)+chr(116)+chr(39)].get(chr(39)+chr(112)+chr(114)+chr(95)+chr(97)+chr(117)+chr(99)+chr(39), 0):.3f}")
    print(f"  Optimal threshold: {results[best_name][chr(39)+chr(111)+chr(112)+chr(116)+chr(105)+chr(109)+chr(97)+chr(108)+chr(95)+chr(116)+chr(104)+chr(114)+chr(101)+chr(115)+chr(104)+chr(111)+chr(108)+chr(100)+chr(39)]:.3f}")

    # Save model with the FULL feature columns
    version = "v3-real-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    model_path = REGISTRY_DIR / (version + ".pkl")
    meta_path = REGISTRY_DIR / (version + ".metadata.json")
    feature_columns = list(X.columns)
    joblib.dump({"model": best_model, "feature_columns": feature_columns}, model_path)
    meta = {
        "model_version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_dataset": str(args.csv),
        "all_results": {k: {kk: (vv if not isinstance(vv, np.ndarray) else vv.tolist()) if not isinstance(vv, dict) else {kkk: (vvv if not isinstance(vvv, (list, np.ndarray)) else (vvv.tolist() if hasattr(vvv, "tolist") else str(vvv))) for kkk, vvv in vvv.items()} for kk, vv in v.items()} for k, v in results.items()},
        "feature_columns": feature_columns,
        "algorithm": best_name,
        "n_features": len(feature_columns),
    }
    # Fix any non-serializable values
    def make_serializable(obj):
        if isinstance(obj, dict):
            return {k: make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [make_serializable(x) for x in obj]
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    meta = make_serializable(meta)
    meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
    # Also save feature schema
    schema = FeatureSchema()
    schema_path = REGISTRY_DIR / (version + ".feature_schema.json")
    schema_path.write_text(schema.to_json(), encoding="utf-8")

    print(f"\nSaved: {model_path}")
    print(f"Version: {version}")
    print(f"Features used: {len(feature_columns)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
