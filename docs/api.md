# API Reference

Base URL: `http://127.0.0.1:8000/api/v1`

Full OpenAPI spec at `/docs` when the API is running.

## Health

### `GET /health`
Liveness probe.
```json
{"status": "ok", "app": "landslide-ner", "env": "development", "version": "0.1.0"}
```

## Locations

### `POST /locations`
Create a monitored location.
```json
{"name": "Test Hill", "state": "Manipur", "district": "Imphal West", "latitude": 24.817, "longitude": 93.937}
```
Returns `201` with the created location.

### `GET /locations`
List locations, filterable by `?state=...&district=...&limit=200`.

### `GET /locations/{id}`
Get a single location.

## Predictions

### `POST /predictions`
```json
{"latitude": 24.817, "longitude": 93.937, "save": true}
```
Returns a risk response with `risk_score` (0-100), `risk_level` (LOW/MODERATE/HIGH/CRITICAL), `model_version`, `probability`, `is_synthetic`.

## Risk

### `GET /risk/current`
Latest prediction per location.

### `GET /risk/map`
Map-ready risk points with thresholds and model version.

### `GET /risk/{location_id}`
Latest prediction for a specific location.

## Priority

### `GET /priority/{latitude}/{longitude}`
Get P1/P2/P3 priority for a coordinate.

### `GET /priority`
List all locations sorted by priority.

## Reports

### `POST /reports`
Submit a field report. `client_id` makes it idempotent.
```json
{"client_id": "uuid-here", "report_type": "CRACK", "description": "...", "timestamp": "2024-06-15T12:00:00Z", "latitude": 25.0, "longitude": 93.0}
```

### `GET /reports`
List reports, filterable by `?status=...&report_type=...&limit=100`.

### `PATCH /reports/{id}`
Update report status (RECEIVED, VERIFIED, REJECTED, DUPLICATE).

## Alerts

### `GET /alerts`
List alerts, filterable by `?severity=HIGH|CRITICAL&limit=100`.

### `GET /alerts/{id}/deliveries`
List delivery attempts for an alert.

## Sensors (IoT)

### `POST /sensors/data`
Ingest a sensor reading. Auto-creates sensor if new.
```json
{"sensor_id": "SM-001", "kind": "soil_moisture", "latitude": 27.58, "longitude": 91.86, "timestamp": "2024-06-15T12:00:00Z", "soil_moisture": 81.4}
```

### `GET /sensors`
List registered sensors.
