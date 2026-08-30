"""Direct training script - run me to train the real model."""
import sys
import joblib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, "ml/scripts")
from train_improved import engineer_features
from ml.features import FeatureSchema

df = pd.read_csv("data/processed/real_training_dataset_v3.csv")
print("Loaded:", len(df), "rows")

df_eng = engineer_features(df)
print("Engineered:", df_eng.shape)

drop_cols = ["event_month", "severity_num", "fatality_count"]
feature_cols = [c for c in df_eng.columns if c not in drop_cols + ["landslide_occurred"]]
df_features = pd.get_dummies(df_eng[feature_cols + ["land_cover"]], columns=["land_cover"])
X = df_features.astype(float)
y = df_eng["landslide_occurred"].astype(int).values
print("Final X:", X.shape, "y:", y.shape)

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
Xtr_np = Xtr.to_numpy()
Xte_np = Xte.to_numpy()

model = RandomForestClassifier(
    n_estimators=500, max_depth=15, min_samples_split=4,
    min_samples_leaf=2, n_jobs=1, random_state=42,
    class_weight="balanced_subsample",
)
print("Fitting RF with", X.shape[1], "features...")
model.fit(Xtr_np, ytr)
proba = model.predict_proba(Xte_np)[:, 1]
print("Probability range:", round(proba.min(), 3), "-", round(proba.max(), 3), "mean:", round(proba.mean(), 3))
print("Unique proba values:", len(np.unique(np.round(proba, 2))))

from sklearn.metrics import (
    average_precision_score, precision_recall_fscore_support, roc_auc_score, confusion_matrix
)
test_pr_auc = float(average_precision_score(yte, proba))
test_roc_auc = float(roc_auc_score(yte, proba))
y_pred = (proba >= 0.5).astype(int)
p, r, f, _ = precision_recall_fscore_support(yte, y_pred, average="binary", zero_division=0)
cm = confusion_matrix(yte, y_pred, labels=[0, 1])
tn, fp, fn, tp = cm.ravel().tolist()
print("Test PR-AUC:", round(test_pr_auc, 3), "F1:", round(f, 3), "Recall:", round(r, 3), "Precision:", round(p, 3))
print("Confusion: TP=" + str(tp) + " FP=" + str(fp) + " TN=" + str(tn) + " FN=" + str(fn))

reg = Path("ml/artifacts/registry")
version = "v3-real-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
model_path = reg / (version + ".pkl")
meta_path = reg / (version + ".metadata.json")
schema_path = reg / (version + ".feature_schema.json")
feature_columns = list(X.columns)
joblib.dump({"model": model, "feature_columns": feature_columns}, model_path)

schema = FeatureSchema()
schema_path.write_text(schema.to_json(), encoding="utf-8")

meta = {
    "model_version": version,
    "algorithm": "random_forest",
    "trained_at": datetime.now(timezone.utc).isoformat(),
    "training_dataset": "real_training_dataset_v3.csv",
    "feature_columns": feature_columns,
    "n_features": len(feature_columns),
    "n_train": int(len(Xtr)),
    "n_test": int(len(Xte)),
    "test_metrics": {
        "pr_auc": test_pr_auc,
        "roc_auc": test_roc_auc,
        "precision": float(p),
        "recall": float(r),
        "f1": float(f),
    },
    "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
}
meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
print("Saved:", version)
print("Features:", len(feature_columns))
