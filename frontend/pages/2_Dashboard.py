"""Authority Dashboard - Analytics with real numbers."""
from __future__ import annotations

import os
from datetime import datetime

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
API_PREFIX = os.environ.get("API_PREFIX", "/api/v1")

st.set_page_config(page_title="Authority Dashboard - NER", page_icon="D", layout="wide")


@st.cache_data(ttl=15)
def api_get(path: str):
    try:
        r = httpx.get(f"{API_BASE}{API_PREFIX}{path}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=15)
def api_post(path: str, payload: dict):
    try:
        r = httpx.post(f"{API_BASE}{API_PREFIX}{path}", json=payload, timeout=15.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


st.markdown("# Authority Dashboard - NER India")
st.markdown("**Operational view for authorities — connected risk, roads, weather, priority**")
st.caption("For common people, see Home & Help pages for simple guide — this dashboard is the strong backend view")

# Sidebar actions
with st.sidebar:
    st.markdown("### Quick Actions")
    if st.button("Refresh Dashboard", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("### Test Coordinates")
    if st.button("Test: Guwahati (26.14, 91.74)"):
        with st.spinner("Scoring Guwahati..."):
            r = api_post("/predictions", {"latitude": 26.14, "longitude": 91.74, "save": True})
            if r and "risk_score" in r:
                st.session_state.last_test = f"Guwahati: {r['risk_score']} ({r['risk_level']})"
    if st.button("Test: Imphal (24.82, 93.94)"):
        with st.spinner("Scoring Imphal..."):
            r = api_post("/predictions", {"latitude": 24.82, "longitude": 93.94, "save": True})
            if r and "risk_score" in r:
                st.session_state.last_test = f"Imphal: {r['risk_score']} ({r['risk_level']})"
    if st.button("Test: Shillong (25.58, 91.88)"):
        with st.spinner("Scoring Shillong..."):
            r = api_post("/predictions", {"latitude": 25.58, "longitude": 91.88, "save": True})
            if r and "risk_score" in r:
                st.session_state.last_test = f"Shillong: {r['risk_score']} ({r['risk_level']})"
    if hasattr(st.session_state, "last_test"):
        st.success(st.session_state.last_test)

# Load all data
risk_map = api_get("/risk/map")
risks = api_get("/risk/current")
locations = api_get("/locations")
reports = api_get("/reports")
alerts = api_get("/alerts")

# Top KPIs - 6 columns
st.markdown("### Key Performance Indicators (Live)")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Locations", len(locations) if isinstance(locations, list) else 0)
c2.metric("Risk Points", len(risks) if isinstance(risks, list) else 0)
c3.metric("Alerts", len(alerts) if isinstance(alerts, list) else 0)
c4.metric("Reports", len(reports) if isinstance(reports, list) else 0)

if isinstance(risk_map, dict) and "points" in risk_map:
    pts = risk_map["points"]
    counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
    for p in pts:
        counts[p["risk_level"]] = counts.get(p["risk_level"], 0) + 1
    c5.metric("Critical", counts["CRITICAL"])
    c6.metric("High", counts["HIGH"])
else:
    c5.metric("Critical", 0)
    c6.metric("High", 0)

st.markdown("---")

# Risk distribution chart
st.markdown("### Risk Score Distribution")
if isinstance(risks, list) and risks:
    df = pd.DataFrame(risks)
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.histogram(
            df, x="risk_score", nbins=20,
            title="Distribution of Risk Scores",
            color_discrete_sequence=["#1e3a5f"],
        )
        fig1.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        level_counts = df["risk_level"].value_counts().reset_index()
        level_counts.columns = ["level", "count"]
        colors = {"CRITICAL": "#dc3545", "HIGH": "#fd7e14", "MODERATE": "#ffc107", "LOW": "#28a745"}
        fig2 = px.pie(
            level_counts, values="count", names="level",
            title="Risk Level Breakdown",
            color="level",
            color_discrete_map=colors,
        )
        fig2.update_layout(height=350)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    # Road connectivity + weather forecast (from existing data)
    st.markdown("### 🛣️ Road Connectivity Status (from field reports + risk)")
    if isinstance(reports, list) and reports:
        road_reports = [r for r in reports if r.get("report_type") in ("ROAD_BLOCKAGE","LANDSLIDE","ROCKFALL")]
        if road_reports:
            st.warning(f"{len(road_reports)} road-affecting reports — check Map for blocked segments")
            st.dataframe(pd.DataFrame(road_reports)[["report_type","latitude","longitude","status"]].head(10), use_container_width=True, hide_index=True)
        else:
            st.success("No road blockages reported — all monitored roads appear open (based on last 100 reports)")
    else:
        st.caption("No reports yet — road status unknown")
    # Prioritised response (P1/P2/P3) from priority_engine
    st.markdown("### 🚨 Emergency Response Prioritisation (P1/P2/P3)")
    try:
        pri = api_get("/priority?limit=5")
        if isinstance(pri, list) and pri:
            pdf = pd.DataFrame(pri)
            pdf["priority_tag"] = pdf["priority"].map({"P1":"🔴 P1-Critical","P2":"🟠 P2-High","P3":"🟢 P3-Low"})
            st.dataframe(pdf[["name","state","risk_level","priority_tag","rationale"]], use_container_width=True, hide_index=True)
            st.caption("Notation: P1 = act now (HIGH/CRITICAL + hospitals/schools nearby), P2 = prepare, P3 = monitor")
        else:
            st.caption("No priority data yet")
    except Exception:
        pass
    # Weather-linked forecast (uses Open-Meteo real)
    st.markdown("### 🌦️ Weather-linked Risk Forecast (24h/72h)")
    st.caption("Live forecast from Open-Meteo (free IMD alternative) is already in risk score: rainfall_24h/72h + soil moisture")
    st.markdown("---")

    # Locations table
    st.markdown("### All Monitored Locations")
    display = df[["latitude", "longitude", "risk_score", "risk_level", "model_version"]].sort_values("risk_score", ascending=False)
    display.columns = ["Lat", "Lon", "Score", "Level", "Model"]
    st.dataframe(display, use_container_width=True, hide_index=True)
else:
    st.info("No risk data. Run the seed script or make some predictions first.")
