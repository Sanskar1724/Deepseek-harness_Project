# Architecture

## Overview

Modular monolith (FastAPI + Streamlit) with replaceable data providers,
PostgreSQL/PostGIS-compatible schema on SQLite+SpatiaLite, real ML pipeline,
and Streamlit dashboard.

## Components

- `backend/app/` - FastAPI application
  - `core/` - config, logging, errors
  - `db/` - SQLAlchemy + GeoAlchemy2 engine, session, base
  - `models/` - ORM models (Location, WeatherData, LandslideEvent, RiskPrediction,
    FieldReport, Infrastructure, Sensor, SensorReading, Alert, AlertDelivery, ModelRegistry)
  - `api/v1/` - REST endpoints (health, locations, predictions, risk, priority, reports, alerts)
  - `schemas/` - Pydantic v2 request/response models
  - `services/` - risk_engine, priority_engine, alert_engine
  - `providers/` - abstract interfaces + mock/OpenMeteo/NASA POWER implementations
- `ml/` - ML pipeline
  - `datasets/` - synthetic builder + real-data loader interface
  - `features.py` - feature schema + transformation
  - `train.py` - RF + XGBoost training with metrics
  - `predict.py` - model loading + inference
  - `scripts/` - build_dataset, train_model CLIs
- `frontend/` - Streamlit multi-page app
  - `app.py` - Home page
  - `pages/1_Map.py` - Leaflet risk map
  - `pages/2_Dashboard.py` - Authority dashboard
  - `pages/3_Reports.py` - Field reports
  - `pages/4_Alerts.py` - Alerts
  - `i18n/` - en, hi, as translation files
- `data/` - raw + processed data (gitignored)
- `scripts/` - bootstrap, check_db
- `tests/` - pytest suite
- `alembic/` - DB migrations

## Data Flow

```
Providers -> Risk Engine (model.proba -> score 0-100 -> level) -> API -> Streamlit
                    |
                    v
              Priority Engine (exposure + risk -> P1/P2/P3)
                    |
                    v
              Alert Engine (threshold -> alert -> delivery)
```