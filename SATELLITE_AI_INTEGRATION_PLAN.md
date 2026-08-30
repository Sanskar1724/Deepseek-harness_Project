# Satellite AI Integration Plan — Additive, No Rewrite

## 1. Existing Architecture (audit)
- **Providers:** `backend/app/providers/base.py:119` interfaces (`WeatherProvider`, `TerrainProvider`, `SoilProvider`, `SatelliteProvider.get_attributes(Point)->SatelliteAttributes(ndvi,land_cover,source,is_synthetic)`, `LandslideProvider`, `RainfallProvider`). Registry `backend/app/providers/registry.py:37` `_select(name,mock,real_map)` + `lru_cache` — already replaceable.
- **Features:** `ml/features.py:17` `NUMERIC_FEATURES` 16 cols + `CATEGORICAL land_cover` one-hot via `build_feature_matrix:62`. Target `landslide_occurred`.
- **ML:** `ml/train.py:126` `train_and_compare` RF 400/500 calibrated vs XGB 500/800 hist, pick `pr_auc`. `ml/predict.py:88` `load_latest` + `predict_proba` via `build_feature_matrix`. Storage `ml/artifacts/registry/*.pkl` + `ModelRegistry`.
- **Risk:** `backend/app/services/risk_engine.py:85` `score_point(Point)->RiskResult(score,level,prob,source,is_synthetic,lat/lon)` `score_from_proba:71` `prob*100` + `classify:58` thresholds 30/60/80 from `core/config.py`. `priority_engine.py:80` `haversine_km` + exposure P1/P2/P3.
- **Assess:** `backend/app/api/v1/assess.py:11` merges risk+priority+alternatives+place → single connected call. No satellite yet.
- **GIS/Frontend:** `frontend/pages/1_Map.py:107` Leaflet heatmap, `frontend/components.py:8` geolocation, `frontend/app.py:191` `GET /assess` best prediction.
- **Config:** `.env:20` `WEATHER=open_meteo, TERRAIN=open_elevation, SOIL=nasa_power, SATELLITE=real_derived, LANDSLIDE=real_coolr` — `risk_engine:116` `is_synthetic` now ignores satellite.

## 2. Integration Point (additive)
```
Point(lat,lon)
 → existing env providers (open_meteo/open_elevation/nasa_power/real_coolr)
 → existing RF/XGB → prob_env
 → NEW satellite_ai provider → SatelliteEvidence
 → Fusion (validated)
 → existing risk_engine.classify → score 0-100 → priority → alternatives → alert
```
No replacement of existing model. Satellite is optional evidence.

## 3. Proposed New Modules (no existing file rewrite)
```
backend/app/providers/satellite_ai/
  interface.py  (SatelliteEvidence dataclass)
  mock.py       (deterministic mock, fast, no HF)
  indlands.py   (stub for IndLands dataset inspection)
  terra_fm.py   (stub, heavy)
  landslide_vlm.py (LFM2.5-VL-450M GGUF, CPU)
  prithvi.py    (stub)
experiments/
  satellite_landslide_test.py (standalone, not wired to risk_engine yet)
docs/
  SATELLITE_MODEL_EVALUATION.md (Phase 5)
  MODEL_COMPARISON.md (Phase 6)
```

## 4. Files That Do NOT Need Modification
- `ml/features.py`, `ml/train.py` (until fusion validated)
- `risk_engine.py` (except optional post-validation import)
- `frontend/pages/*` (until backend stable)
- `tests/*` (must keep passing)
- `app/db/*`, `alembic/*`

## 5. Files That May Need Minimal Modification (later phases)
- `backend/app/providers/registry.py:71` — add `satellite_ai` mapping if `SATELLITE_PROVIDER=satellite_ai`
- `backend/app/api/v1/assess.py:11` — optional `satellite_evidence` field, keep existing fields, `available=false` fallback
- `backend/app/services/fusion.py` (new) — not existing file
- `pyproject.toml:40` — add `huggingface-hub`, `torch` (CPU) only if needed

## 6. Dependency & Hardware
- IndLands: dataset  ~few GB images/DEM, inspect via `datasets` lib, not full download
- TerraFM (MBZUAI): large EO foundation, needs GPU, Sentinel-1/2, heavy → not for local 600-train
- LFM2.5-VL-450M-GGUF: 450M quantized, CPU runnable, needs `llama-cpp-python` or `transformers`, image → text evidence (vegetation/wetness) → best for Phase 4
- Prithvi landslide: segmentation, needs HLS imagery, GPU
- Choice for Phase 4: **LFM2.5-VL-450M** (practical, NER relevant, CPU, quick test)

## 7. Fallback Strategy (mandatory)
- `satellite_evidence.available=false` → existing model continues
- `assess` always returns `risk_score/level` even if `satellite_ai` timeout/503/HF down
- Cache `lat,lon,day → SatelliteEvidence` (use existing `@st.cache_data(ttl=300)` pattern)
- Timeouts 8s, no blocking of `/assess` >2s
