# Setup Guide

## Prerequisites

- Python 3.11+
- SpatiaLite extension:
  - Windows: OSGeo4W (install `spatialite` package), add `C:\OSGeo4W64\bin` to PATH
  - macOS: `brew install spatialite-tools`
  - Linux: `sudo apt install libsqlite3-mod-spatialite`

## Installation

```bash
cd S:\SIH_Meta\deepseek try
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
# Edit .env if needed (SPATIALITE_PATH, etc.)
alembic -c backend/alembic.ini upgrade head
python scripts/check_db.py
```

## Running

Terminal 1 (API):
```bash
uvicorn app.main:app --reload --port 8000
```

Terminal 2 (UI):
```bash
streamlit run frontend/app.py
```

## Verification

```bash
curl http://127.0.0.1:8000/api/v1/health
pytest -q
```