"""Landing page - user-friendly introduction."""
from __future__ import annotations

import os
import httpx
import streamlit as st

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
API_PREFIX = os.environ.get("API_PREFIX", "/api/v1")

st.set_page_config(page_title="Welcome - NER Landslide Early Warning", page_icon="W", layout="wide")


@st.cache_data(ttl=10)
def api_get(path):
    try:
        r = httpx.get(f"{API_BASE}{API_PREFIX}{path}", timeout=5.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


st.markdown("""
<style>
.hero { background: linear-gradient(135deg, #1e3a5f, #2c5282, #3182ce); 
        color: white; padding: 3rem; border-radius: 12px; margin-bottom: 2rem; }
.hero h1 { color: white; font-size: 2.5rem; margin: 0; }
.hero p { color: #e2e8f0; font-size: 1.1rem; }
.card { background: white; padding: 1.5rem; border-radius: 8px; 
         border-left: 4px solid #3182ce; box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
         margin-bottom: 1rem; }
.metric-box { text-align: center; padding: 1rem; background: #f7fafc; 
               border-radius: 8px; }
.metric-number { font-size: 2rem; font-weight: 700; color: #1e3a5f; }
</style>
"", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>Landslide Early Warning System</h1>
    <p>AI-powered real-time monitoring and prediction for the North Eastern Region of India</p>
    <p style="font-size:0.9rem;opacity:0.8;">Protecting lives, infrastructure, and connectivity across 8 states</p>
</div>
"", unsafe_allow_html=True)

# System status
health = api_get("/health")
if health.get("status") == "ok":
    st.success(f"System Online | {health.get('app')} v{health.get('version')}")
else:
    st.warning("System status unknown - check API connection")

# Quick stats
risk_map = api_get("/risk/map")
locations = api_get("/locations")
alerts = api_get("/alerts")
reports = api_get("/reports")

points = risk_map.get("points", []) if isinstance(risk_map, dict) else []
counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
for p in points:
    counts[p.get("risk_level", "LOW")] = counts.get(p.get("risk_level", "LOW"), 0) + 1

st.markdown("### Current Status Snapshot")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Locations", len(locations) if isinstance(locations, list) else 0)
c2.metric("CRITICAL", counts["CRITICAL"])
c3.metric("HIGH", counts["HIGH"])
c4.metric("MODERATE", counts["MODERATE"])
c5.metric("LOW", counts["LOW"])
c6.metric("Reports", len(reports) if isinstance(reports, list) else 0)

st.markdown("---")
st.markdown("## What This Platform Does")

c1, c2 = st.columns(2)
with c1:
    st.markdown("### AI-Powered Risk Prediction")
    st.write("Machine learning models trained on real NASA landslide data predict risk 0-100 with confidence scores.")
    st.markdown("### Live Data Integration")
    st.write("Connects to Open-Meteo, OpenStreetMap, NASA COOLR, USGS earthquakes, GDACS alerts.")
    st.markdown("### Field Reporting")
    st.write("Citizens and field workers submit geo-tagged reports of cracks, rockfalls, road blockages. Mobile-friendly, offline-capable.")
with c2:
    st.markdown("### Interactive Risk Mapping")
    st.write("Leaflet maps with color-coded risk zones, infrastructure overlay (roads, hospitals, schools).")
    st.markdown("### Automatic Early Warnings")
    st.write("Alerts fire automatically when risk exceeds thresholds. SMS, push, log delivery. Multilingual: English, Hindi, Assamese.")
    st.markdown("### Emergency Prioritization")
    st.write("P1/P2/P3 priority engine considers risk + infrastructure exposure for evacuation planning.")

st.markdown("---")
st.markdown("## Who Uses This Platform")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**State Disaster Management**")
    st.write("Assam, Manipur, Meghalaya, Nagaland, Tripura, Mizoram, Arunachal Pradesh, Sikkim SDMA")
with c2:
    st.markdown("**District Authorities**")
    st.write("Deputy Commissioners, District Disaster Control Rooms, Emergency Operations Centres")
with c3:
    st.markdown("**Field Personnel & Public**")
    st.write("NHAI/PWD engineers, local community members, disaster response teams, geo-tagged citizen reports")

st.markdown("---")
st.markdown("## Quick Actions")
q1, q2, q3, q4 = st.columns(4)
with q1:
    if st.button("VIEW RISK MAP", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Map.py")
with q2:
    if st.button("DASHBOARD", use_container_width=True):
        st.switch_page("pages/2_Dashboard.py")
with q3:
    if st.button("REPORT INCIDENT", use_container_width=True):
        st.switch_page("pages/3_Reports.py")
with q4:
    if st.button("CITIZEN HELP", use_container_width=True):
        st.switch_page("pages/6_Common_People_Help.py")

st.markdown("---")
st.markdown("## Problem We Solve")
st.info("""
The North Eastern Region (NER) frequently faces landslides, flash floods, and road blockages. Currently, monitoring is mostly reactive. This AI platform:
- Predicts high-risk zones BEFORE disaster strikes
- Delivers early warnings to authorities and communities
- Integrates citizen reports for ground-truth data
- Works in multilingual mode (English, Hindi, Assamese)
- Supports offline operation for remote areas
""")

st.caption("Click the navigation in the sidebar to explore all features.")
