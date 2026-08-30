# Limitations & Deviations from Master Prompt

## 1. Synthetic Data

All training data and live features come from mock providers.
No real NER landslide inventory, IMD rainfall, ISRO Bhuvan, or NASA SMAP data is bundled.
The UI displays a prominent **DEMO / SYNTHETIC DATA** banner.

## 2. Database: SQLite + SpatiaLite instead of PostgreSQL + PostGIS

- **Reason**: Zero-install local demo per Phase 0 decision.
- **Impact**: Some PostGIS functions unavailable (raster, ST_ClusterKMeans, geography type).
  We use only `ST_Distance`, `ST_DWithin`, `ST_GeomFromText` which work on both.
- **Migration path**: Change `DATABASE_URL` to `postgresql://...`, run `alembic upgrade head`.

## 3. Frontend: Streamlit instead of React + Leaflet

- **Reason**: Faster delivery per Phase 0 decision (Option A).
- **Impact**: No real-time WebSocket updates, limited offline sync UI (Phase 13 is backend-only).
  Map interactivity is basic (circle markers + heatmap).

## 4. No Computer Vision (Phase 16)

Flagged as deferred. No image classification model included.

## 5. Alert Delivery Stubs

SMS/Push channels log only. Real providers (Twilio, Firebase) need API keys.

## 6. Offline Sync: Backend Only

`FieldReport.sync_status` tracks state. Frontend has no Service Worker / IndexedDB.

## 7. Model Calibration

`score_from_proba(p) = round(p * 100)`. No Platt scaling / isotonic regression.

## 8. Single-Process Deployment

No Docker Compose, no reverse proxy, no HTTPS. Suitable for local demo only.