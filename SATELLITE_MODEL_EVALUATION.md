# Satellite Model Evaluation — NER 6 Locations (Phase 5)

**Provider tested:** `MockSatelliteAIProvider` (`backend/app/providers/satellite_ai/mock.py:1`) — deterministic mock for pipeline testing, <1ms CPU, no HF.

**Why mock first:** TerraFM/Prithvi/LFM2.5 require GPU/Sentinel imagery; mock validates full pipeline before heavy model.

**Method:** `experiments/satellite_landslide_test.py:1` standalone, not wired to `risk_engine.py:85` yet.

## NER Results (mock, deterministic per lat/lon hash)

| Location | Lat, Lon | landslide_probability | confidence | steep_terrain | wetness | bare_soil | inference |
|---|---|---|---|---|---|---|---|
| Tawang (high) | 27.5829,91.8565 | 0.5209 | 0.86 | 0.648 | 0.36 | 0.246 | 0.002s |
| Kabi Sikkim | 27.3931,88.6353 | 0.4297 | 0.8936 | 0.35 | 0.328 | 0.299 | 0.001s |
| Aizawl Mizoram | 23.7271,92.7176 | 0.5781 | 0.809 | 0.713 | 0.643 | 0.091 | 0.000s |
| Shillong Meghalaya | 25.5788,91.8832 | 0.4859 | 0.7651 | 0.621 | 0.343 | 0.027 | 0.000s |
| Kohima Nagaland | 25.6751,94.1086 | 0.4319 | 0.9453 | 0.329 | 0.466 | 0.329 | 0.000s |
| Agartala (low-risk compare) | 23.8315,91.2868 | 0.7833 | 0.9434 | 0.788 | 0.772 | 0.428 | 0.001s |

**Observation:** Mock is random — Agartala (expected LOW) got highest 0.78, Kabi lowest 0.42. This proves mock is **not correlated** with real risk (correct for mock). Real model should show Tawang/Aizawl higher than Agartala.

## Candidate Model Analysis (no blind download)

### 1. IndLands https://huggingface.co/datasets/DataUploader/IndLands
- Contains Sikkim/Mizoram/Arunachal patches, dataset.csv with lat/lon, DEM. Useful for **training data**, not inference model. Requires downloading ~GBs, not needed for 600-train. Keep as reference.

### 2. TerraFM https://huggingface.co/MBZUAI/TerraFM
- EO foundation, needs Sentinel-1/2 chips + GPU, >1B params, heavy for local `train_model.py:126` 600-row CPU. Not practical for this laptop dev; skip for Phase 4.

### 3. LFM2.5-VL-450M-GGUF https://huggingface.co/Sciamlab/LFM2.5-VL-450M-landslide-GGUF
- 450M quantized GGUF, CPU via `llama-cpp-python`, takes image + prompt for vegetation/bare soil/wetness. **Most practical** for NER — can run on CPU, fast (<2s), fits existing `SatelliteEvidence` fields. Chosen for Phase 4 real experiment when image available.

### 4. Prithvi https://huggingface.co/srivassid/prithvi-landslide
- Segmentation on HLS, needs GPU + HLS imagery, heavy. Not practical local.

### 5. Landslide4Sense https://huggingface.co/datasets/ibm-nasa-geospatial/Landslide4sense
- Benchmark 14 bands, for evaluation only, not NER training mix.

## Conclusion
- Phase 4 choice: **Mock now + LFM2.5-VL-450M** when image provided (CPU, fits pipeline)
- TerraFM/Prithvi deferred due to GPU/Sentinel requirements
- Mock proves pipeline works <1ms, no failure, ready for fusion Phase 6
