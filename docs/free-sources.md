# Free Data Sources (No API Key Required)

All sources below are **completely free** and require **no API key**.
They have been integrated into the project as provider classes.

## Currently Integrated

| Source | Provider Class | What It Gives | Use Case |
|--------|---------------|---------------|----------|
| **Open-Meteo** | `OpenMeteoWeatherProvider`, `OpenMeteoRainfallProvider` | Hourly weather + 7-day forecast | Real rainfall and temperature |
| **NASA POWER** | `NasaPowerSoilProvider` | Daily precipitation | Soil moisture proxy |
| **Open-Elevation** | `OpenElevationTerrainProvider` | Real elevation for any lat/lon | Real DEM, slope, aspect |
| **OpenStreetMap Overpass** | `osm_overpass.sync_infrastructure()` | Hospitals, schools, roads, bridges, villages | Real infrastructure exposure |
| **USGS Earthquakes** | `usgs_earthquakes.fetch_earthquakes_near()` | Recent earthquakes (M2.5+) | Seismic trigger feature |
| **Nominatim** | `nominatim.geocode()` | Place name → lat/lon | Field report by district name |
| **GDACS** | `gdacs.fetch_recent_alerts()` | Global disaster alerts (floods, quakes) | Regional hazard context |
| **NASA COOLR** | `ml/datasets/loaders/nasa_coolr.py` | Historical landslide events (CSV) | Real training data |

## How to Enable Each

### Weather (Open-Meteo) — 5 minutes
```bash
# In .env:
WEATHER_PROVIDER=open_meteo
RAINFALL_PROVIDER=open_meteo
```
No code changes needed. Already integrated.

### Elevation (Open-Elevation) — 5 minutes
```bash
# In .env:
TERRAIN_PROVIDER=open_elevation
```
Already integrated. No API key.

### Soil Moisture Proxy (NASA POWER) — 5 minutes
```bash
# In .env:
SOIL_PROVIDER=nasa_power
```
Already integrated. No API key.

### Infrastructure from OSM — 10 minutes
```bash
# Fetch and insert real infrastructure into the DB:
python scripts/sync_osm_infrastructure.py

# This adds:
# - All hospitals in NER
# - All schools
# - All bridges
# - All villages and towns
# - Power infrastructure
```

### Historical Landslides (NASA COOLR) — 30 minutes
1. Download from https://data.nasa.gov/ (search "Global Landslide Catalog")
2. Save as `data/raw/nasa_coolr.csv`
3. Train:
```bash
python -m ml.scripts.train_model --loader nasa_coolr --data data/raw/nasa_coolr.csv
```

## Optional: Add Seismic Risk Feature

The USGS earthquake feed can be added as a feature to the risk model:

```python
from app.providers.usgs_earthquakes import count_recent_earthquakes

def get_earthquake_count(point):
    return count_recent_earthquakes(point, radius_km=100, days=7, min_magnitude=2.5)
```

## Optional: Geocode Field Reports

When a field worker submits a report by place name:

```python
from app.providers.nominatim import geocode

point = geocode("Imphal West")
if point:
    # Use point.latitude, point.longitude
    ...
```

## Quick Wins Checklist

- [ ] Enable Open-Meteo weather (5 min)
- [ ] Enable Open-Elevation (5 min)
- [ ] Enable NASA POWER soil (5 min)
- [ ] Sync OSM infrastructure (10 min)
- [ ] Download NASA COOLR data (30 min)
- [ ] Train on real data (10 min)
- [ ] Add USGS earthquake count as feature (20 min)
- [ ] Add Nominatim geocoding to report form (15 min)

**Total: ~1.5 hours to make the project fully real-data-driven**

## What This Means for Your Project

After enabling these, your project will have:
- ✅ **Real** weather data for any NER location
- ✅ **Real** elevation and slope from a global DEM
- ✅ **Real** hospitals, schools, bridges from OpenStreetMap
- ✅ **Real** historical landslides for training (if you download COOLR)
- ✅ **Real** earthquake data for risk features
- ✅ **Real** disaster alerts from GDACS
- ✅ **Real** geocoding for field reports

**Only remaining as mock/synthetic:**
- NDVI / land cover (no free real-time option)
- True soil moisture (SMAP requires separate download)
- Rainfall forecast beyond 7 days (free APIs max out at 7-16 days)
