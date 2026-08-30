"""Simple V3 training: trains and saves with full features."""
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
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except Exception:
    HAS_XGB = False

from ml.scripts.train_improved import engineer_features
from ml.features import FeatureSchema

REGISTRY_DIR = Path("ml/artifacts/registry")
REGISTRY_DIR.mkdir(parents=True, exist_ok=True)


def find_optimal_threshold(y_true, y_proba, min_recall=0.85):
    precision, recall, thresholds = precision_recall_curve(y_true, y_proba)
    f1_scores = 2 * (precision * recall) / (precision + recall + 1e-9)
    valid = recall >= min_recall
    if not valid.any():
        return 0.5, 0.0, 0.0, 0.0
    masked_f1 = np.where(valid, f1_scores, -1)
    best_idx = int(np.argmax(masked_f1))
    best_threshold = float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.5
    return best_threshold, float(f1_scores[best_idx]), float(recall[best_idx]), float(precision[best_idx])


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

    # Engineer features
    df_eng = engineer_features(df)
    print(f"After engineering: {df_eng.shape[1]} features")

    # Build feature matrix - USE ALL ENGINEERED FEATURES
    drop_cols = ["event_month", "severity_num", "fatality_count"]
    feature_cols = [c for c in df_eng.columns if c not in drop_cols + ["landslide_occurred"]]
    df_features = pd.get_dummies(df_eng[feature_cols + ["land_cover"]], columns=["land_cover"])
    X = df_features.astype(float).copy()
    y = df_eng["landslide_occurred"].astype(int).to_numpy()

    print(f"\nFinal X: {X.shape[1]} features, {len(X)} rows")
    print("Features:", list(X.columns))

    # Train/test split
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=args.seed, stratify=y)

    # Train multiple algorithms
    results = {}
    trained_models = {}

    algorithms = {
        "random_forest": RandomForestClassifier(
            n_estimators=500, max_depth=15, min_samples_split=4,
            min_samples_leaf=2, n_jobs=1, random_state=args.seed,
            class_weight="balanced_subsample",
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            subsample=0.85, random_state=args.seed,
        ),
    }
    if HAS_XGB:
        algorithms["xgboost"] = XGBClassifier(
            n_estimators=400, max_depth=6, learning_rate=0.05,
            subsample=0.85, colsample_bytree=0.85, reg_alpha=0.1,
            reg_lambda=1.0, eval_metric="logloss", random_state=args.seed, n_jobs=1,
        )

    print("\nTraining algorithms...")
    # Convert to numpy to avoid narwhals/pandas compatibility issues
    Xtr_np = Xtr.to_numpy()
    Xte_np = Xte.to_numpy()
    feature_columns = list(X.columns)
    for name, model in algorithms.items():
        print(f"  Training {name}...")
        try:
            model.fit(Xtr_np, ytr)
            trained_models[name] = model
            # Test metrics
            proba = model.predict_proba(Xte_np)[:, 1]
            y_pred = (proba >= 0.5).astype(int)
            test_metrics = {}
            if len(set(yte)) > 1:
                test_metrics["pr_auc"] = float(average_precision_score(yte, proba))
                test_metrics["roc_auc"] = float(roc_auc_score(yte, proba))
            else:
                test_metrics["pr_auc"] = 0.0
                test_metrics["roc_auc"] = 0.0
            p, r, f, _ = precision_recall_fscore_support(yte, y_pred, average="binary", zero_division=0)
            test_metrics["precision"] = float(p)
            test_metrics["recall"] = float(r)
            test_metrics["f1"] = float(f)
            cm = confusion_matrix(yte, y_pred, labels=[0, 1])
            tn, fp, fn, tp = cm.ravel().tolist()
            test_metrics["confusion_matrix"] = {"tn": tn, "fp": fp, "fn": fn, "tp": tp}
            opt_t, opt_f1, opt_r, opt_p = find_optimal_threshold(yte, proba, min_recall=0.80)
            results[name] = {
                "test": test_metrics,
                "optimal_threshold": opt_t,
                "optimal_metrics": {"f1": opt_f1, "recall": opt_r, "precision": opt_p},
            }
            print(f"    PR-AUC={test_metrics[chr(39)+chr(112)+chr(114)+chr(95)+chr(97)+chr(117)+chr(99)+chr(39)]:.3f}, F1={test_metrics[chr(39)+chr(102)+chr(49)+chr(39)]:.3f}, Recall={test_metrics[chr(39)+chr(114)+chr(101)+chr(99)+chr(97)+chr(108)+chr(108)+chr(39)]:.3f}")
        except Exception as e:
            print(f"    FAILED: {e}")
            import traceback; traceback.print_exc()

    if not results:
        print("All algorithms failed - using random forest as fallback")
        model = RandomForestClassifier(n_estimators=200, random_state=42)
        model.fit(Xtr, ytr)
        trained_models["random_forest_fallback"] = model
        results["random_forest_fallback"] = {"test": {"pr_auc": 0.0, "f1": 0.0}}

    # Pick best by test PR-AUC
    best_name = max(results, key=lambda n: results[n].get("test", {}).get("pr_auc", 0))
    best_model = trained_models[best_name]

    print(f"\nBest: {best_name}")
    print(f"  PR-AUC: {results[best_name][chr(39)+chr(116)+chr(101)+chr(115)+chr(116)+chr(39)][chr(39)+chr(112)+chr(114)+chr(95)+chr(97)+chr(117)+chr(99)+chr(39)]:.3f}")
    print(f"  F1: {results[best_name][chr(39)+chr(116)+chr(101)+chr(115)+chr(116)+chr(39)][chr(39)+chr(102)+chr(49)+chr(39)]:.3f}")
    print(f"  Recall: {results[best_name][chr(39)+chr(116)+chr(101)+chr(115)+chr(116)+chr(39)][chr(39)+chr(114)+chr(101)+chr(99)+chr(97)+chr(108)+chr(108)+chr(39)]:.3f}")

    # Save model with FULL engineered features
    version = "v3-real-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    model_path = REGISTRY_DIR / (version + ".pkl")
    meta_path = REGISTRY_DIR / (version + ".metadata.json")
    schema_path = REGISTRY_DIR / (version + ".feature_schema.json")
    feature_columns = list(X.columns)

    joblib.dump({"model": best_model, "feature_columns": feature_columns}, model_path)

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

    meta = make_serializable({
        "model_version": version,
        "algorithm": best_name,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_dataset": str(args.csv),
        "all_results": results,
        "feature_columns": feature_columns,
        "n_features": len(feature_columns),
    })
    meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")

    schema = FeatureSchema()
    schema_path.write_text(schema.to_json(), encoding="utf-8")

    print(f"\nSaved: {model_path}")
    print(f"Version: {version}")
    print(f"Features: {len(feature_columns)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
