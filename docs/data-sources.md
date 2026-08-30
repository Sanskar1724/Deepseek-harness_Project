# Data Sources

## Current (Mock)

All providers return deterministic synthetic data seeded by (lat, lon).
This lets the pipeline run end-to-end without external dependencies.

## Real Providers (Configured in .env)

| Category | Free | Key Required | Configured? |
|----------|------|--------------|-------------|
| Weather (rainfall, temp, humidity) | Open-Meteo | No | Yes (open_meteo) |
| Soil moisture proxy | NASA POWER | No | Yes (nasa_power) |
| DEM (elevation, slope) | None (see below) | - | No |
| Satellite (NDVI, land cover) | ESA WorldCover (static) | No | No |
| Historical landslides | GSI Bhukosh / NASA COOLR | Auth | No |
| Soil moisture (real) | NASA SMAP | No | No |

## Adding a Real Provider

1. Implement the interface in `backend/app/providers/`.
2. Add to the registry map in `backend/app/providers/registry.py`.
3. Set the env var: `WEATHER_PROVIDER=open_meteo`.
4. Test with the real API.

## Data Card for Synthetic Dataset

- **Source**: `ml/datasets/synthetic.py` + mock providers.
- **Labels**: Noisy logistic function of risk-relevant features.
- **Size**: Configurable via `--n-points` (default 600).
- **Use**: Pipeline testing only. Not for real-world accuracy claims.