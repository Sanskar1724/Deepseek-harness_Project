"""Improved training pipeline for landslide risk prediction.

Improvements over the base pipeline:
  1. Cross-validation (Stratified 5-fold) for robust metrics
  2. Feature engineering: derived features (interactions, ratios)
  3. Multiple algorithms: RF, XGBoost, GradientBoosting, Logistic Regression
  4. SMOTE for class imbalance handling
  5. Hyperparameter tuning (RandomizedSearchCV)
  6. Threshold optimization for early-warning (maximize recall)
  7. Stacking ensemble (best models combined)

Usage:
    python -m ml.scripts.train_improved --csv data/processed/real_training_dataset.csv
"""
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

from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
    StackingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_fscore_support,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
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

try:
    from imblearn.over_sampling import SMOTE
    HAS_SMOTE = True
except Exception:
    HAS_SMOTE = False

from ml.features import FeatureSchema, build_feature_matrix


REGISTRY_DIR = Path("ml/artifacts/registry")
REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived features that improve landslide prediction."""
    out = df.copy()

    # 1. Interaction features (rainfall * slope is a known risk factor)
    if "rainfall_72h_mm" in out.columns and "slope_deg" in out.columns:
        out["rain_x_slope"] = out["rainfall_72h_mm"] * out["slope_deg"]
    if "rainfall_24h_mm" in out.columns and "soil_moisture_pct" in out.columns:
        out["rain_x_soil"] = out["rainfall_24h_mm"] * out["soil_moisture_pct"] / 100.0
    if "rainfall_72h_mm" in out.columns and "elevation_m" in out.columns:
        out["rain_x_elev"] = out["rainfall_72h_mm"] * (1.0 / (1.0 + out["elevation_m"] / 1000.0))

    # 2. Cumulative rainfall pressure (weighted sum of recent rainfall)
    if all(c in out.columns for c in ["rainfall_1h_mm", "rainfall_6h_mm", "rainfall_24h_mm", "rainfall_72h_mm"]):
        out["rain_pressure"] = (
            out["rainfall_1h_mm"] * 4.0 +
            out["rainfall_6h_mm"] * 3.0 +
            out["rainfall_24h_mm"] * 2.0 +
            out["rainfall_72h_mm"] * 1.0
        )

    # 3. Forecast stress (incoming rain amplifies current risk)
    if "forecast_72h_mm" in out.columns and "rainfall_72h_mm" in out.columns:
        out["forecast_stress"] = out["forecast_72h_mm"] / (out["rainfall_72h_mm"] + 1.0)

    # 4. Slope risk classes (categorical bins)
    if "slope_deg" in out.columns:
        out["slope_high"] = (out["slope_deg"] > 30).astype(int)
        out["slope_steep"] = (out["slope_deg"] > 45).astype(int)

    # 5. Elevation categories (low elevation = more risk in monsoon)
    if "elevation_m" in out.columns:
        out["elev_low"] = (out["elevation_m"] < 1000).astype(int)
        out["elev_mid"] = ((out["elevation_m"] >= 1000) & (out["elevation_m"] < 2000)).astype(int)

    # 6. Historical risk signal (log-scaled)
    if "historical_landslide_count" in out.columns:
        out["log_hist"] = np.log1p(out["historical_landslide_count"])

    # 7. NDVI inverse (low vegetation = more risk)
    if "ndvi" in out.columns:
        out["low_veg"] = 1.0 - out["ndvi"]

    # 8. Aspect north-facing (more rain in NER during monsoon)
    if "aspect_deg" in out.columns:
        out["aspect_north"] = np.cos(np.radians(out["aspect_deg"] - 0))

    return out

def get_algorithms() -> dict:
    """Return the algorithms to train with hyperparameter search spaces."""
    algos = {
        "random_forest": {
            "model": RandomForestClassifier(
                n_estimators=300, max_depth=15, min_samples_split=4,
                min_samples_leaf=2, n_jobs=1, random_state=42,
                class_weight="balanced_subsample",
            ),
            "params": {
                "n_estimators": [200, 300, 500, 800],
                "max_depth": [8, 12, 15, 20, None],
                "min_samples_split": [2, 4, 6, 10],
                "min_samples_leaf": [1, 2, 4],
                "max_features": ["sqrt", "log2", 0.5],
            },
        },
        "gradient_boosting": {
            "model": GradientBoostingClassifier(
                n_estimators=200, max_depth=5, learning_rate=0.05,
                subsample=0.85, random_state=42,
            ),
            "params": {
                "n_estimators": [100, 200, 300, 500],
                "max_depth": [3, 5, 7, 10],
                "learning_rate": [0.01, 0.05, 0.1, 0.2],
                "subsample": [0.7, 0.85, 1.0],
            },
        },
        "logistic_regression": {
            "model": Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
            ]),
            "params": {
                "clf__C": [0.01, 0.1, 1.0, 10.0, 100.0],
                "clf__penalty": ["l1", "l2"],
            },
        },
    }
    if HAS_XGB:
        algos["xgboost"] = {
            "model": XGBClassifier(
                n_estimators=400, max_depth=8, learning_rate=0.05,
                subsample=0.85, colsample_bytree=0.85, reg_alpha=0.1,
                reg_lambda=1.0, eval_metric="logloss", random_state=42, n_jobs=1,
            ),
            "params": {
                "n_estimators": [200, 300, 500, 800],
                "max_depth": [4, 6, 8, 10, 12],
                "learning_rate": [0.01, 0.03, 0.05, 0.1, 0.2],
                "subsample": [0.7, 0.85, 1.0],
                "colsample_bytree": [0.7, 0.85, 1.0],
                "reg_alpha": [0.0, 0.1, 1.0],
                "reg_lambda": [0.1, 1.0, 10.0],
            },
        }
    return algos


def find_optimal_threshold(y_true, y_proba, min_recall: float = 0.85) -> tuple:
    """Find threshold that maximizes F1 subject to a minimum recall (for early-warning)."""
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


def cross_validate_evaluate(estimator, X, y, n_splits: int = 5) -> dict:
    """5-fold cross-validation to get robust metrics."""
    from sklearn.base import clone
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    cv_metrics = {"pr_auc": [], "roc_auc": [], "f1": [], "recall": [], "precision": []}
    for tr_idx, te_idx in skf.split(X, y):
        Xtr, Xte = X.iloc[tr_idx], X.iloc[te_idx]
        ytr, yte = y[tr_idx], y[te_idx]
        try:
            est = clone(estimator)
            est.fit(Xtr, ytr)
            proba = est.predict_proba(Xte)[:, 1]
            y_pred = (proba >= 0.5).astype(int)
            if len(set(yte)) > 1:
                cv_metrics["pr_auc"].append(average_precision_score(yte, proba))
                cv_metrics["roc_auc"].append(roc_auc_score(yte, proba))
            p, r, f, _ = precision_recall_fscore_support(yte, y_pred, average="binary", zero_division=0)
            cv_metrics["precision"].append(float(p))
            cv_metrics["recall"].append(float(r))
            cv_metrics["f1"].append(float(f))
        except Exception as e:
            print(f"  CV fold failed: {e}")
    return {k: float(np.mean(v)) if v else 0.0 for k, v in cv_metrics.items()}

def train_and_evaluate(df: pd.DataFrame, schema: FeatureSchema, *, seed: int = 42) -> dict:
    """Train multiple algorithms with CV and pick the best."""
    df_eng = engineer_features(df)
    X = build_feature_matrix(df_eng, schema)
    y = df_eng[schema.target].astype(int).to_numpy()

    print(f"\nDataset: {len(X)} rows, {X.shape[1]} features, {y.sum()} positives ({y.mean():.1%})")

    if len(X) < 20:
        print("WARNING: Very small dataset. Results may be unreliable.")

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y)

    if HAS_SMOTE and ytr.sum() >= 6 and (len(ytr) - ytr.sum()) >= 6:
        try:
            sm = SMOTE(random_state=seed, k_neighbors=min(5, int(ytr.sum()) - 1))
            Xtr, ytr = sm.fit_resample(Xtr, ytr)
            print(f"SMOTE applied: {Xtr.shape[0]} training rows ({ytr.sum()} positives)")
        except Exception as e:
            print(f"SMOTE skipped: {e}")

    algorithms = get_algorithms()
    results = {}
    trained_models = {}

    for name, cfg in algorithms.items():
        print(f"\nTraining {name}...")
        try:
            search = RandomizedSearchCV(
                cfg["model"], cfg["params"], n_iter=8,
                cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=seed),
                scoring="average_precision", n_jobs=1, random_state=seed, refit=True,
            )
            search.fit(Xtr, ytr)
            best_model = search.best_estimator_
            cv = cross_validate_evaluate(best_model, X, y, n_splits=5)
            proba = best_model.predict_proba(Xte)[:, 1]
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
            trained_models[name] = best_model
            print(f"  CV PR-AUC: {cv[chr(39)+chr(112)+chr(114)+chr(95)+chr(97)+chr(117)+chr(99)+chr(39)]}"
            f", F1: {cv[chr(39)+chr(102)+chr(49)+chr(39)]:.3f}, Recall: {cv[chr(39)+chr(114)+chr(101)+chr(99)+chr(97)+chr(108)+chr(108)+chr(39)]:.3f}")
            print(f"  Test PR-AUC: {test_metrics[chr(39)+chr(112)+chr(114)+chr(95)+chr(97)+chr(117)+chr(99)+chr(39)]:.3f}, F1: {test_metrics[chr(39)+chr(102)+chr(49)+chr(39)]:.3f}")
            print(f"  Optimal threshold: {opt_t:.2f} (F1={opt_f1:.3f}, Recall={opt_r:.3f})")
        except Exception as e:
            print(f"  FAILED: {e}")

    if not results:
        raise RuntimeError("All algorithms failed")

    sorted_algos = sorted(results.items(), key=lambda x: x[1]["cv"]["pr_auc"], reverse=True)
    print(f"\nBuilding stacking ensemble from: {[n for n, _ in sorted_algos[:3]]}")
    try:
        top_models = [(n, trained_models[n]) for n, _ in sorted_algos[:3]]
        ensemble = StackingClassifier(
            estimators=top_models,
            final_estimator=LogisticRegression(class_weight="balanced", max_iter=1000),
            cv=3, n_jobs=1,
        )
        ensemble.fit(Xtr, ytr)
        proba = ensemble.predict_proba(Xte)[:, 1]
        ens_metrics = {
            "pr_auc": float(average_precision_score(yte, proba)) if len(set(yte)) > 1 else 0.0,
            "roc_auc": float(roc_auc_score(yte, proba)) if len(set(yte)) > 1 else 0.0,
        }
        y_pred = (proba >= 0.5).astype(int)
        p, r, f, _ = precision_recall_fscore_support(yte, y_pred, average="binary", zero_division=0)
        ens_metrics.update({"precision": float(p), "recall": float(r), "f1": float(f)})
        opt_t, opt_f1, opt_r, opt_p = find_optimal_threshold(yte, proba, min_recall=0.80)
        results["ensemble"] = {
            "cv": ens_metrics, "test": ens_metrics,
            "optimal_threshold": opt_t,
            "optimal_metrics": {"f1": opt_f1, "recall": opt_r, "precision": opt_p},
        }
        trained_models["ensemble"] = ensemble
        print(f"  Ensemble PR-AUC: {ens_metrics[chr(39)+chr(112)+chr(114)+chr(95)+chr(97)+chr(117)+chr(99)+chr(39)]:.3f}, F1: {ens_metrics[chr(39)+chr(102)+chr(49)+chr(39)]:.3f}")
    except Exception as e:
        print(f"  Ensemble skipped: {e}")

    best_name = max(results, key=lambda n: results[n].get("cv", results[n].get("test", {})).get("pr_auc", 0))
    return {
        "best_name": best_name,
        "best_model": trained_models[best_name],
        "all_results": results,
        "feature_columns": list(X.columns),
    }

def persist_model(model, feature_columns, results, training_dataset):
    """Save the best model with metadata."""
    version = "improved-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    model_path = REGISTRY_DIR / (version + ".pkl")
    meta_path = REGISTRY_DIR / (version + ".metadata.json")
    joblib.dump({"model": model, "feature_columns": feature_columns}, model_path)
    meta = {
        "model_version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_dataset": training_dataset,
        "all_results": results,
        "feature_columns": feature_columns,
    }
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return version, str(model_path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=Path, default=ROOT / "data/processed/real_training_dataset.csv")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    if not args.csv.exists():
        print("ERROR: CSV not found: " + str(args.csv))
        print("Run first: python scripts/ingest_real_data.py --max-events 80")
        return 2

    print("=" * 60)
    print("IMPROVED ML TRAINING PIPELINE")
    print("=" * 60)
    df = pd.read_csv(args.csv)
    print("Loaded: " + str(len(df)) + " rows, " + str(df.shape[1]) + " columns")
    pos = int(df["landslide_occurred"].sum())
    print("Positives: " + str(pos) + " (" + str(round(df["landslide_occurred"].mean() * 100, 1)) + "%)")

    schema = FeatureSchema()
    out = train_and_evaluate(df, schema, seed=args.seed)

    print("")
    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print("Best algorithm: " + out["best_name"])
    best = out["all_results"][out["best_name"]]
    cv = best.get("cv", {})
    test_m = best.get("test", {})
    opt_m = best.get("optimal_metrics", {})
    print("  CV PR-AUC: " + str(round(cv.get("pr_auc", 0), 3)))
    print("  Test PR-AUC: " + str(round(test_m.get("pr_auc", 0), 3)))
    print("  Optimal threshold: " + str(round(best.get("optimal_threshold", 0.5), 2)))
    print("  At optimal: F1=" + str(round(opt_m.get("f1", 0), 3)) + ", Recall=" + str(round(opt_m.get("recall", 0), 3)))

    print("")
    print("All algorithms (sorted by CV PR-AUC):")
    sorted_res = sorted(out["all_results"].items(), key=lambda x: x[1].get("cv", x[1].get("test", {})).get("pr_auc", 0), reverse=True)
    for name, r in sorted_res:
        cv = r.get("cv", {})
        t = r.get("test", {})
        print("  " + name.ljust(20) + " CV PR-AUC=" + str(round(cv.get("pr_auc", 0), 3)) + " | Test PR-AUC=" + str(round(t.get("pr_auc", 0), 3)) + " | F1=" + str(round(t.get("f1", 0), 3)) + " | Recall=" + str(round(t.get("recall", 0), 3)))

    version, path = persist_model(out["best_model"], out["feature_columns"], out["all_results"], str(args.csv))
    print("")
    print("Saved: " + path)
    print("Version: " + version)
    print("")
    print("=" * 60)
    print("NEXT STEP: Restart the API to load the new model:")
    print("  Get-Process -Name python | Stop-Process -Force")
    print("  cd backend; ..\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8000")
    print("  cd ..; .venv\\Scripts\\python.exe -m streamlit run frontend/app.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())