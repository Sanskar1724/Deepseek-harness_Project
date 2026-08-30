# Database

## Engine: SQLite + SpatiaLite

Zero-install local demo. Geometry via SpatiaLite ST_* functions.

## Tables (11)

| Table | Purpose |
|-------|---------|
| locations | Monitored locations (lat/lon + terrain attrs + geom POINT) |
| weather_data | Observed + forecast weather snapshots |
| landslide_events | Historical landslide records |
| risk_predictions | Append-only prediction log |
| field_reports | Citizen/field reports (offline-capable) |
| infrastructure | Roads, villages, bridges, hospitals, schools |
| sensors | IoT sensor registry |
| sensor_readings | IoT time-series data |
| alerts | Alert records |
| alert_deliveries | Alert delivery audit trail |
| model_registry | ML model versions + metrics |

## Geometry

- SRID 4326 (WGS84 lat/lon) on all geometry columns.
- `geom` is the spatial column; `latitude`/`longitude` are duplicated for
  fast non-spatial filtering and indexing.

## Migrations

Hand-written initial migration at `backend/alembic/versions/0001_initial.py`.
For subsequent changes: `alembic revision --autogenerate -m "msg"` then edit.

## PostGIS Migration

Change `DATABASE_URL` to `postgresql://...`, run `alembic upgrade head`.
Geometry columns will work unchanged (GeoAlchemy2 abstracts the dialect).