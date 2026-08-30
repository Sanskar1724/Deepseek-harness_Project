"""Real data flow: show real NASA COOLR data + live API features."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st

try:
    from components import geolocation_autofill, weather_tracking_card
except Exception:
    from frontend.components import geolocation_autofill, weather_tracking_card

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
API_PREFIX = os.environ.get("API_PREFIX", "/api/v1")

ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "data" / "raw" / "Global_Landslide_Catalog_Export_rows.csv"
PROC_CSV = ROOT / "data" / "processed" / "real_training_dataset.csv"

st.set_page_config(page_title="Real Data Flow - NER", page_icon="R", layout="wide")

st.markdown("> **REAL DATA MODE** - This page shows the live data ingestion pipeline.")
st.title("Real Data Flow")

tab1, tab2, tab3 = st.tabs(["1. NASA COOLR Raw", "2. Processed Training Data", "3. Live Prediction"])

with tab1:
    st.subheader("NASA COOLR Raw Data (Global Landslide Catalog)")
    if not RAW_CSV.exists():
        st.error(f"Raw CSV not found: {RAW_CSV}")
        st.stop()
    size_mb = RAW_CSV.stat().st_size / (1024 * 1024)
    st.info(f"File: {RAW_CSV.name} ({size_mb:.1f} MB)")
    if st.button("Analyze raw data"):
        with st.spinner("Reading CSV..."):
            df = pd.read_csv(RAW_CSV, low_memory=False)
            st.write(f"Total rows: **{len(df)}**")
            df_india = df[df["country_code"] == "IN"]
            st.write(f"India entries: **{len(df_india)}**")
            df_ner = df_india[
                (pd.to_numeric(df_india["latitude"], errors="coerce").between(21.5, 29.5))
                & (pd.to_numeric(df_india["longitude"], errors="coerce").between(88, 97.5))
            ]
            st.write(f"NER entries: **{len(df_ner)}**")
            state_counts = df_ner["admin_division_name"].value_counts().head(10)
            st.bar_chart(state_counts)
            st.write("Sample NER events:")
            st.dataframe(
                df_ner[["event_id", "event_date", "latitude", "longitude", "admin_division_name", "landslide_size"]].head(20),
                use_container_width=True,
            )

with tab2:
    st.subheader("Processed Training Data (with live API features)")
    if not PROC_CSV.exists():
        st.warning("No processed dataset yet. Run the ingestion script first.")
        st.code("python scripts/ingest_real_data.py --max-events 50")
        if st.button("Run ingestion now (30 events)"):
            with st.spinner("Fetching live features from Open-Meteo + Open-Elevation..."):
                result = subprocess.run(
                    [sys.executable, "scripts/ingest_real_data.py", "--max-events", "30"],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0:
                    st.success("Ingestion complete!")
                    st.code(result.stdout[-2000:])
                else:
                    st.error(f"Failed: {result.stderr[-1000:]}")
    else:
        df = pd.read_csv(PROC_CSV)
        size_kb = PROC_CSV.stat().st_size / 1024
        st.info(f"File: {PROC_CSV.name} ({size_kb:.1f} KB, {len(df)} rows)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", len(df))
        c2.metric("Positives", int(df["landslide_occurred"].sum()))
        c3.metric("Negatives", len(df) - int(df["landslide_occurred"].sum()))
        c4.metric("Data source", df["source"].iloc[0] if "source" in df.columns else "n/a")
        st.dataframe(df.head(50), use_container_width=True)
        st.line_chart(df[["rainfall_24h_mm", "rainfall_72h_mm"]].head(50))
        st.bar_chart(df[["elevation_m", "slope_deg"]].head(30))

with tab3:
    st.subheader("Live Risk Prediction (real APIs) — One-click for common people")
    st.info("📍 Allow location permission → coordinates auto-fill → get weather-linked risk instantly. Tags show what to do.")
    auto_lat, auto_lon = geolocation_autofill("realdata")
    if auto_lat is not None:
        weather_tracking_card(auto_lat, auto_lon, API_BASE, API_PREFIX)
        st.caption("👆 Live weather tracking for your current location (auto-updated)")
    c1, c2 = st.columns(2)
    def_lat = float(auto_lat) if auto_lat is not None else 26.1445
    def_lon = float(auto_lon) if auto_lon is not None else 91.7362
    lat = c1.number_input("Latitude", value=def_lat, format="%.6f", help="Use 📍 button above")
    lon = c2.number_input("Longitude", value=def_lon, format="%.6f", help="Use 📍 button above")
    if st.button("Get real risk prediction", type="primary"):
        with st.spinner("Calling real APIs (weather + elevation)..."):
            try:
                r = httpx.post(
                    f"{API_BASE}{API_PREFIX}/predictions",
                    json={"latitude": lat, "longitude": lon, "save": True},
                    timeout=15.0,
                )
                if r.status_code == 200:
                    data = r.json()
                    s1, s2, s3 = st.columns(3)
                    s1.metric("Risk Score", f"{data['risk_score']} / 100")
                    s2.metric("Risk Level", data["risk_level"])
                    s3.metric("Model", data["model_version"])
                    st.write(f"Source: {data.get('is_synthetic', True) and 'synthetic' or 'REAL live APIs'}")
                    weather_tracking_card(lat, lon, API_BASE, API_PREFIX)
                    with st.expander("Full response + notation"):
                        st.json(data)
                        st.markdown("**Notation:** LOW=Safe, MODERATE=Caution, HIGH=Avoid slopes, CRITICAL=Follow evacuation")
                else:
                    st.error(f"API error: {r.status_code} - {r.text}")
            except Exception as e:
                st.error(f"Failed: {e}")
