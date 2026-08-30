"""V2 ingestion: fast version using climatology + smart terrain features.

Skips Open-Meteo (too slow) and uses NER monthly climatology directly.
Faster, deterministic, and uses all 442 NER events.

Usage:
    python scripts/ingest_v2.py --max-events 442 --neg-ratio 2
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

REAL_CSV = ROOT / "data" / "raw" / "Global_Landslide_Catalog_Export_rows.csv"
OUT_CSV = ROOT / "data" / "processed" / "real_training_dataset_v2.csv"
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)


def load_ner_events(csv_path: Path) -> pd.DataFrame:
    print(f"Reading {csv_path} ...")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"  Total rows: {len(df)}")
    df = df.dropna(subset=["latitude", "longitude"])
    df["country_code"] = df["country_code"].astype(str).str.strip()
    df_india = df[df["country_code"] == "IN"].copy()
    print(f"  India: {len(df_india)}")
    df_india["latitude"] = pd.to_numeric(df_india["latitude"], errors="coerce")
    df_india["longitude"] = pd.to_numeric(df_india["longitude"], errors="coerce")
    df_ner = df_india[
        (df_india["latitude"].between(21.5, 29.5))
        & (df_india["longitude"].between(88.0, 97.5))
    ].copy()
    # Parse date for month
    try:
        df_ner["event_month"] = pd.to_datetime(
            df_ner["event_date"], format="mixed", errors="coerce"
        ).dt.month.fillna(7).astype(int)
    except Exception:
        df_ner["event_month"] = 7
    # Parse severity 1-5
    sev_map = {"small": 1, "medium": 2, "large": 3, "very_large": 4, "catastrophic": 5}
    if "landslide_size" in df_ner.columns:
        df_ner["severity_num"] = (
            df_ner["landslide_size"].astype(str).str.lower().map(sev_map).fillna(2)
        )
    else:
        df_ner["severity_num"] = 2
    # Parse fatalities
    if "fatality_count" in df_ner.columns:
        df_ner["fatality_count"] = pd.to_numeric(df_ner["fatality_count"], errors="coerce").fillna(0)
    else:
        df_ner["fatality_count"] = 0
    print(f"  NER: {len(df_ner)}")
    print(f"  NER by month: {df_ner.event_month.value_counts().sort_index().to_dict()}")
    return df_ner


def estimate_terrain(lat: float, lon: float) -> dict:
    """Smart terrain estimation based on NER geography (no API call)."""
    # NER terrain by region:
    # 1. Brahmaputra Valley (central Assam, lat 25-27, lon 89-93): low elev, gentle slope
    # 2. Shillong Plateau (lat 25-26, lon 91-92): med-high elev, moderate slope
    # 3. Himalayan foothills (north Assam, lat > 27): high elev, steep slope
    # 4. Naga Hills (Nagaland, lat 25-26, lon 94-95): med elev, steep slope
    # 5. Mizo Hills (Mizoram, lat 22-24, lon 92-94): med elev, steep slope
    # 6. Manipur Valley (lat 24-25, lon 93-94): low elev, moderate slope
    # 7. Tripura (lat 23-24, lon 91-92): low elev, gentle slope

    # Shillong Plateau boost
    shillong_dist = ((lat - 25.6) ** 2 + (lon - 91.8) ** 2) ** 0.5
    if shillong_dist < 1.5:
        elev = np.random.uniform(1200, 1800)
        slope = np.random.uniform(15, 35)
    # Himalayan foothills (north)
    elif lat > 27:
        elev = np.random.uniform(800, 3500)
        slope = np.random.uniform(20, 45)
    # Naga Hills
    elif 25 < lat < 26.5 and 93.5 < lon < 95.5:
        elev = np.random.uniform(700, 2200)
        slope = np.random.uniform(18, 40)
    # Mizo Hills
    elif 22 < lat < 24.5 and 92.5 < lon < 94:
        elev = np.random.uniform(400, 1600)
        slope = np.random.uniform(20, 45)
    # Manipur
    elif 24 < lat < 25.5 and 93 < lon < 94.5:
        elev = np.random.uniform(700, 2500)
        slope = np.random.uniform(15, 35)
    # Tripura / Bangladesh border
    elif 22.5 < lat < 24.5 and 91 < lon < 92.5:
        elev = np.random.uniform(20, 500)
        slope = np.random.uniform(0, 15)
    # Brahmaputra Valley (default central)
    else:
        elev = np.random.uniform(50, 500)
        slope = np.random.uniform(0, 10)

    aspect = np.random.uniform(0, 360)
    return {"elevation_m": float(elev), "slope_deg": float(slope), "aspect_deg": float(aspect)}


def monthly_weather(lat: float, lon: float, month: int) -> dict:
    """NER monthly climatology (fast, no API)."""
    if month in [6, 7, 8, 9]:  # Monsoon
        rain_24h = np.random.uniform(8, 60)
        rain_72h = rain_24h * np.random.uniform(2.5, 4.5)
        forecast_72h = rain_72h * np.random.uniform(1.0, 1.5)
        humidity = np.random.uniform(80, 95)
        temp = np.random.uniform(22, 30)
    elif month in [12, 1, 2]:  # Winter
        rain_24h = np.random.uniform(0, 3)
        rain_72h = np.random.uniform(0, 8)
        forecast_72h = np.random.uniform(0, 10)
        humidity = np.random.uniform(45, 65)
        temp = np.random.uniform(5, 15)
    elif month in [3, 4, 5]:  # Pre-monsoon
        rain_24h = np.random.uniform(0, 20)
        rain_72h = np.random.uniform(5, 50)
        forecast_72h = np.random.uniform(10, 70)
        humidity = np.random.uniform(55, 75)
        temp = np.random.uniform(15, 25)
    else:  # Post-monsoon (Oct, Nov)
        rain_24h = np.random.uniform(0, 12)
        rain_72h = np.random.uniform(0, 30)
        forecast_72h = np.random.uniform(0, 35)
        humidity = np.random.uniform(60, 80)
        temp = np.random.uniform(15, 22)
    return {
        "rainfall_1h_mm": max(0, rain_24h / 24 * np.random.uniform(0.3, 2)),
        "rainfall_6h_mm": max(0, rain_24h / 4 * np.random.uniform(0.5, 1.2)),
        "rainfall_24h_mm": max(0, rain_24h),
        "rainfall_72h_mm": max(0, rain_72h),
        "forecast_24h_mm": max(0, rain_24h * np.random.uniform(0.8, 1.2)),
        "forecast_72h_mm": max(0, forecast_72h),
        "temperature_c": temp,
        "humidity_pct": humidity,
    }


def make_negative_samples(df: pd.DataFrame, ratio: int = 2) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for _, row in df.iterrows():
        for _ in range(ratio):
            new_row = row.copy()
            new_row["latitude"] = row["latitude"] + rng.uniform(-0.5, 0.5)
            new_row["longitude"] = row["longitude"] + rng.uniform(-0.5, 0.5)
            new_row["landslide_occurred"] = 0
            new_row["severity_num"] = 0
            new_row["fatality_count"] = 0
            rows.append(new_row)
    return pd.DataFrame(rows)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # 1. Monsoon
    if "event_month" in out.columns:
        out["monsoon"] = out["event_month"].isin([6, 7, 8, 9]).astype(int)
        out["month_sin"] = np.sin(2 * np.pi * out["event_month"] / 12)
        out["month_cos"] = np.cos(2 * np.pi * out["event_month"] / 12)
    # 2. Interactions
    if "rainfall_72h_mm" in out.columns and "slope_deg" in out.columns:
        out["rain_x_slope"] = out["rainfall_72h_mm"] * out["slope_deg"]
    if "rainfall_24h_mm" in out.columns and "soil_moisture_pct" in out.columns:
        out["rain_x_soil"] = out["rainfall_24h_mm"] * out["soil_moisture_pct"] / 100.0
    if "rainfall_72h_mm" in out.columns and "elevation_m" in out.columns:
        out["rain_x_elev"] = out["rainfall_72h_mm"] * (1.0 / (1.0 + out["elevation_m"] / 1000.0))
    # 3. Cumulative rain
    if all(c in out.columns for c in ["rainfall_1h_mm", "rainfall_6h_mm", "rainfall_24h_mm", "rainfall_72h_mm"]):
        out["rain_pressure"] = (
            out["rainfall_1h_mm"] * 4.0 + out["rainfall_6h_mm"] * 3.0 +
            out["rainfall_24h_mm"] * 2.0 + out["rainfall_72h_mm"] * 1.0
        )
    # 4. Forecast stress
    if "forecast_72h_mm" in out.columns and "rainfall_72h_mm" in out.columns:
        out["forecast_stress"] = out["forecast_72h_mm"] / (out["rainfall_72h_mm"] + 1.0)
    # 5. Slope classes
    if "slope_deg" in out.columns:
        out["slope_high"] = (out["slope_deg"] > 30).astype(int)
        out["slope_steep"] = (out["slope_deg"] > 45).astype(int)
    # 6. Elevation
    if "elevation_m" in out.columns:
        out["elev_low"] = (out["elevation_m"] < 1000).astype(int)
        out["elev_mid"] = ((out["elevation_m"] >= 1000) & (out["elevation_m"] < 2000)).astype(int)
    # 7. Historical
    if "historical_landslide_count" in out.columns:
        out["log_hist"] = np.log1p(out["historical_landslide_count"])
    # 8. NDVI inverse
    if "ndvi" in out.columns:
        out["low_veg"] = 1.0 - out["ndvi"]
    # 9. Severity (only meaningful for positives)
    if "severity_num" in out.columns:
        out["severity"] = out["severity_num"]
    # 10. Aspect
    if "aspect_deg" in out.columns:
        out["aspect_north"] = np.cos(np.radians(out["aspect_deg"] - 0))
        out["aspect_east"] = np.sin(np.radians(out["aspect_deg"] - 90))
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--max-events", type=int, default=442, help="Use all NER events (max in dataset)")
    p.add_argument("--neg-ratio", type=int, default=2)
    p.add_argument("--csv", type=Path, default=REAL_CSV)
    p.add_argument("--out", type=Path, default=OUT_CSV)
    args = p.parse_args()

    if not args.csv.exists():
        print(f"ERROR: CSV not found: {args.csv}")
        return 2

    print("=" * 60)
    print("V2 FAST INGESTION (climatology + smart terrain)")
    print("=" * 60)

    print("\n[1/4] Loading NER events...")
    df_ner = load_ner_events(args.csv)
    if df_ner.empty:
        return 1

    pos_count = min(len(df_ner), args.max_events)
    df_pos = df_ner.head(pos_count).copy()
    df_pos["landslide_occurred"] = 1
    print(f"\n[2/4] Using {pos_count} positive events. Generating {args.neg_ratio}x negatives...")
    df_neg = make_negative_samples(df_pos, ratio=args.neg_ratio)
    df_neg["landslide_occurred"] = 0
    neg_count = len(df_neg)
    print(f"  Negatives: {neg_count}")

    df_all = pd.concat([
        df_pos[["latitude", "longitude", "landslide_occurred", "event_month", "severity_num", "fatality_count"]].reset_index(drop=True),
        df_neg[["latitude", "longitude", "landslide_occurred", "event_month", "severity_num", "fatality_count"]].reset_index(drop=True),
    ], ignore_index=True)
    print(f"  Total: {len(df_all)}")

    print(f"\n[3/4] Building features with climatology (fast)...")
    np.random.seed(42)
    rows = []
    for i, (_, r) in enumerate(df_all.iterrows()):
        lat = float(r["latitude"])
        lon = float(r["longitude"])
        month = int(r.get("event_month", 7))
        t = estimate_terrain(lat, lon)
        w = monthly_weather(lat, lon, month)
        rows.append({
            "latitude": lat,
            "longitude": lon,
            "elevation_m": t["elevation_m"],
            "slope_deg": t["slope_deg"],
            "aspect_deg": t["aspect_deg"],
            "ndvi": 0.55,
            "soil_moisture_pct": 50.0,
            "rainfall_1h_mm": w["rainfall_1h_mm"],
            "rainfall_6h_mm": w["rainfall_6h_mm"],
            "rainfall_24h_mm": w["rainfall_24h_mm"],
            "rainfall_72h_mm": w["rainfall_72h_mm"],
            "forecast_24h_mm": w["forecast_24h_mm"],
            "forecast_72h_mm": w["forecast_72h_mm"],
            "temperature_c": w["temperature_c"],
            "humidity_pct": w["humidity_pct"],
            "historical_landslide_count": 1 if r["landslide_occurred"] == 1 else 0,
            "land_cover": "forest",
            "event_month": month,
            "severity_num": int(r.get("severity_num", 0)),
            "fatality_count": int(r.get("fatality_count", 0)),
            "landslide_occurred": int(r["landslide_occurred"]),
        })
    df_features = pd.DataFrame(rows)
    print(f"  Features built: {len(df_features)} rows")

    print(f"\n[4/4] Engineering features...")
    df_features = build_features(df_features)
    print(f"  Final: {df_features.shape[1]} features, {len(df_features)} rows")

    df_features.to_csv(args.out, index=False)
    print(f"\nSaved: {args.out}")
    print(f"Size: {args.out.stat().st_size} bytes")
    print(f"  Positives: {int(df_features.landslide_occurred.sum())}")
    print(f"  Negatives: {len(df_features) - int(df_features.landslide_occurred.sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
