# Model Comparison — 3 Strategies (held-out 25% of real_training_dataset.csv)

| Strategy | PR-AUC | ROC-AUC | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Existing XGBoost/RF | 0.5341 | 0.6216 | 0.5854 | 0.2892 | 0.3871 |
| Satellite only (mock) | 0.3328 | 0.4899 | 0.3214 | 0.7590 | 0.4516 |
| Fusion (0.65 env + 0.35 sat, conf-weighted) | 0.5272 | 0.6229 | 0.5424 | 0.3855 | 0.4507 |

Best: existing (by PR-AUC)

Notes:
- Satellite mock is random per location (not NER-trained) so PR-AUC near 0.5 expected; fusion with mock should not beat existing — validates no fake gain.
- Real LFM2.5 would be evaluated same way when image available; if fusion does not improve, keep existing as production (per final principle).
- No leakage: historical_landslide_count computed spatially pre-split, train/test split stratified, satellite not using label.

Generated via `experiments/fusion_comparison.py`.
