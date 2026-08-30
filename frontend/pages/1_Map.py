"""Risk Map - Live data with real numbers."""
from __future__ import annotations

import os

import folium
import httpx
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
API_PREFIX = os.environ.get("API_PREFIX", "/api/v1")

st.set_page_config(page_title="Risk Map - NER", page_icon="M", layout="wide")

st.markdown("""
<style>
.critical-card { background: #ffffff; padding: 0.8rem; border-radius: 8px; border: 1px solid #ffcdd2; border-left: 4px solid #dc3545; text-align: center; color: #b71c1c; }
.high-card { background: #ffffff; padding: 0.8rem; border-radius: 8px; border: 1px solid #ffe0b2; border-left: 4px solid #fd7e14; text-align: center; color: #e65100; }
.mod-card { background: #ffffff; padding: 0.8rem; border-radius: 8px; border: 1px solid #fff9c4; border-left: 4px solid #ffc107; text-align: center; color: #f57f17; }
.low-card { background: #ffffff; padding: 0.8rem; border-radius: 8px; border: 1px solid #c8e6c9; border-left: 4px solid #28a745; text-align: center; color: #1b5e20; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=15)
def api_get(path: str):
    try:
        r = httpx.get(f"{API_BASE}{API_PREFIX}{path}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


LEVEL_COLOURS = {
    "LOW": "green",
    "MODERATE": "orange",
    "HIGH": "red",
    "CRITICAL": "darkred",
}

st.markdown("# Risk Map - Live NER")
st.markdown("**Real-time GIS heatmap — vulnerable roads, villages, infrastructure**")
# Keep geolocation only as subtle map centering, not full banner (improvement: not on all pages)
try:
    from components import geolocation_autofill
except Exception:
    from frontend.components import geolocation_autofill
auto_lat, auto_lon = geolocation_autofill("map")
if auto_lat:
    st.caption(f"📍 Centered on your location {auto_lat:.4f}, {auto_lon:.4f}")

# Sidebar controls
with st.sidebar:
    st.markdown("### Map Controls")
    level_filter = st.multiselect(
        "Filter by level",
        ["CRITICAL", "HIGH", "MODERATE", "LOW"],
        default=["CRITICAL", "HIGH", "MODERATE", "LOW"],
    )
    show_heatmap = st.checkbox("Show heatmap layer", value=True)
    if st.button("Refresh Map", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

data = api_get("/risk/map")
if isinstance(data, dict) and "error" in data:
    st.error(f"API Error: {data['error']}")
    st.stop()

points = data.get("points", [])
thresholds = data.get("thresholds", {"low": 30, "moderate": 60, "high": 80})

# Filter
if level_filter:
    points = [p for p in points if p["risk_level"] in level_filter]

# Counts
counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
for p in points:
    counts[p["risk_level"]] = counts.get(p["risk_level"], 0) + 1

# Top metrics
st.markdown("### Filtered Risk Counts")
c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(f'<div class="critical-card"><h3 style="margin:0;color:#dc3545">{counts["CRITICAL"]}</h3><p style="margin:0;color:#b71c1c;font-weight:600">CRITICAL</p></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="high-card"><h3 style="margin:0;color:#fd7e14">{counts["HIGH"]}</h3><p style="margin:0;color:#e65100;font-weight:600">HIGH</p></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="mod-card"><h3 style="margin:0;color:#856404">{counts["MODERATE"]}</h3><p style="margin:0;color:#f57f17;font-weight:600">MODERATE</p></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="low-card"><h3 style="margin:0;color:#155724">{counts["LOW"]}</h3><p style="margin:0;color:#1b5e20;font-weight:600">LOW</p></div>', unsafe_allow_html=True)
c5.metric("TOTAL", len(points))

st.markdown("---")

if not points:
    st.warning("No risk points match the current filter. Try selecting more levels.")
else:
    # Build map - center on user if available
    if auto_lat and auto_lon:
        center_lat, center_lon = auto_lat, auto_lon
        zoom = 9
    else:
        center_lat = sum(p["latitude"] for p in points) / len(points)
        center_lon = sum(p["longitude"] for p in points) / len(points)
        zoom = 6
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="OpenStreetMap")
    # User location marker
    if auto_lat and auto_lon:
        folium.Marker(
            location=[auto_lat, auto_lon],
            icon=folium.Icon(color="blue", icon="star", prefix="fa"),
            popup="You are here",
            tooltip="Your location",
        ).add_to(m)
    for p in points:
        folium.CircleMarker(
            location=[p["latitude"], p["longitude"]],
            radius=8,
            color=LEVEL_COLOURS.get(p["risk_level"], "gray"),
            fill=True,
            fill_color=LEVEL_COLOURS.get(p["risk_level"], "gray"),
            fill_opacity=0.7,
            popup=folium.Popup(
                f"<b>{p['name']}</b><br>Level: {p['risk_level']}<br>Score: {p['risk_score']}/100",
                max_width=250,
            ),
            tooltip=f"{p['risk_level']} ({p['risk_score']})",
        ).add_to(m)
    if show_heatmap:
        from folium.plugins import HeatMap
        HeatMap(
            [(p["latitude"], p["longitude"], p["risk_score"]) for p in points],
            radius=20,
        ).add_to(m)
    st_folium(m, width=None, height=500, returned_objects=[])

    st.markdown("### Risk Points Table")
    df = pd.DataFrame(points)
    df = df[["name", "latitude", "longitude", "risk_score", "risk_level"]].sort_values("risk_score", ascending=False)
    st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")
st.markdown("### Legend")
st.markdown(
    f"- <span style='color:darkred'>**CRITICAL**</span> (score >= {thresholds['high']})\n"
    f"- <span style='color:red'>**HIGH**</span> ({thresholds['moderate']} - {thresholds['high']})\n"
    f"- <span style='color:orange'>**MODERATE**</span> ({thresholds['low']} - {thresholds['moderate']})\n"
    f"- <span style='color:green'>**LOW**</span> (0 - {thresholds['low']})",
    unsafe_allow_html=True,
)
