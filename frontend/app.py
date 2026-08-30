"""Streamlit entrypoint - Professional Authority Dashboard."""
from __future__ import annotations

import os
import time

import httpx
import pandas as pd
import streamlit as st

try:
    from components import common_people_tags, geolocation_autofill, language_selector, risk_legend, t, weather_tracking_card
except Exception:
    from frontend.components import common_people_tags, geolocation_autofill, language_selector, risk_legend, t, weather_tracking_card

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
API_PREFIX = os.environ.get("API_PREFIX", "/api/v1")

st.set_page_config(
    page_title="Landslide Early Warning - NER",
    page_icon="L",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS - works on light & dark (fix invisible on dark background)
st.markdown("""
<style>
.main-header { font-size: 2.2rem; font-weight: 700; color: #0d47a1; margin-bottom: 0.2rem; }
@media (prefers-color-scheme: dark) { .main-header { color: #90caf9 !important; } }
.sub-header { font-size: 1rem; color: #555; margin-bottom: 1.5rem; }
@media (prefers-color-scheme: dark) { .sub-header { color: #b0bec5 !important; } }
.metric-card { background: #ffffff; padding: 1rem; border-radius: 8px; border: 1px solid #e0e0e0; border-left: 4px solid #1e3a5f; color: #212529; }
.critical-card { background: #ffffff; padding: 1rem; border-radius: 8px; border: 1px solid #ffcdd2; border-left: 4px solid #dc3545; color: #b71c1c; }
.high-card { background: #ffffff; padding: 1rem; border-radius: 8px; border: 1px solid #ffe0b2; border-left: 4px solid #fd7e14; color: #e65100; }
.mod-card { background: #ffffff; padding: 1rem; border-radius: 8px; border: 1px solid #fff9c4; border-left: 4px solid #ffc107; color: #f57f17; }
.low-card { background: #ffffff; padding: 1rem; border-radius: 8px; border: 1px solid #c8e6c9; border-left: 4px solid #28a745; color: #1b5e20; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=300)
def api_get(path: str) -> dict | list | None:
    try:
        r = httpx.get(f"{API_BASE}{API_PREFIX}{path}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=300)
def api_post(path: str, payload: dict) -> dict | None:
    try:
        r = httpx.post(f"{API_BASE}{API_PREFIX}{path}", json=payload, timeout=15.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# Sidebar - System status + Language
with st.sidebar:
    try:
        language_selector()
    except Exception:
        pass
    st.markdown("### System Status")
    health = api_get("/health")
    if isinstance(health, dict) and health.get("status") == "ok":
        st.success(f"API Online\n\n{health.get('app', 'app')} v{health.get('version', '?')}")
    else:
        st.error("API Offline")

    # Live data counts
    risk_map = api_get("/risk/map")
    if isinstance(risk_map, dict) and "points" in risk_map:
        pts = risk_map["points"]
        counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
        for p in pts:
            counts[p["risk_level"]] = counts.get(p["risk_level"], 0) + 1
        st.markdown("### Live Risk Counts")
        st.metric("CRITICAL", counts["CRITICAL"])
        st.metric("HIGH", counts["HIGH"])
        st.metric("MODERATE", counts["MODERATE"])
        st.metric("LOW", counts["LOW"])
        st.caption(f"Total: {len(pts)} locations monitored")

    st.markdown("---")
    st.markdown("### Quick Actions")
    if st.button("Refresh All Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("### Navigation")
    st.markdown("- **Home** (this page)")
    st.markdown("- **Map** - Live risk zones")
    st.markdown("- **Dashboard** - Analytics")
    st.markdown("- **Reports** - Field intel")
    st.markdown("- **Alerts** - Emergency alerts")
    st.markdown("- **Real Data** - Live API flow")

# Main page
st.markdown('<div class="main-header">Landslide Early Warning System - North East India</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-powered risk monitoring for the North Eastern Region | Real-time data from Open-Meteo, Open-Elevation, NASA COOLR, and OpenStreetMap</div>', unsafe_allow_html=True)

# For common people - friendly tags
common_people_tags()
risk_legend()
with st.expander("📖 Read in simple words (English / हिंदी / অসমীয়া)"):
    st.markdown(
        "**English:** This system tells you if your area has landslide risk today. Green = safe, Yellow = be careful, Orange/Red = danger - follow government advice.\n\n"
        "**हिंदी:** यह सिस्टम बताता है कि आज आपके क्षेत्र में भूस्खलन का जोखिम है या नहीं। हरा = सुरक्षित, पीला = सावधान, नारंगी/लाल = खतरा।\n\n"
        "**অসমীয়া:** এই প্ৰণালীয়ে আজি আপোনাৰ অঞ্চলত ভূমিস্খলনৰ আশংকা আছে নে নাই কয়। সেউজীয়া = নিৰাপদ, হালধীয়া = সাৱধান, কমলা/ৰঙা = বিপদ।"
    )

# Top metrics row - all real numbers
c1, c2, c3, c4, c5, c6 = st.columns(6)

locations = api_get("/locations")
risks = api_get("/risk/current")
alerts = api_get("/alerts")
reports = api_get("/reports")

loc_count = len(locations) if isinstance(locations, list) else 0
risk_count = len(risks) if isinstance(risks, list) else 0
alert_count = len(alerts) if isinstance(alerts, list) else 0
report_count = len(reports) if isinstance(reports, list) else 0

c1.metric("Monitored Locations", loc_count, delta=None)
c2.metric("Risk Predictions", risk_count, delta=None)
c3.metric("Active Alerts", alert_count, delta=None)
c4.metric("Field Reports", report_count, delta=None)
infra = api_get("/risk/map")
infra_count = len(infra.get("points", [])) if isinstance(infra, dict) else 0
c5.metric("On Map", infra_count, delta=None)
c6.metric("System", "ONLINE", delta="Real-time")

st.markdown("---")

# Live risk breakdown - 4 cards with real numbers
st.markdown("### Current Risk Distribution (Live)")
if isinstance(risk_map, dict) and "points" in risk_map:
    pts = risk_map["points"]
    counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
    for p in pts:
        counts[p["risk_level"]] = counts.get(p["risk_level"], 0) + 1

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="critical-card"><h2 style="margin:0;color:#dc3545">{counts["CRITICAL"]}</h2><p style="margin:0;color:#b71c1c;font-weight:600">CRITICAL ZONES</p></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="high-card"><h2 style="margin:0;color:#fd7e14">{counts["HIGH"]}</h2><p style="margin:0;color:#e65100;font-weight:600">HIGH RISK ZONES</p></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="mod-card"><h2 style="margin:0;color:#856404">{counts["MODERATE"]}</h2><p style="margin:0;color:#f57f17;font-weight:600">MODERATE ZONES</p></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="low-card"><h2 style="margin:0;color:#155724">{counts["LOW"]}</h2><p style="margin:0;color:#1b5e20;font-weight:600">LOW RISK ZONES</p></div>', unsafe_allow_html=True)

st.markdown("---")

# Quick action: Get a risk prediction - with one-click location for common people
st.markdown("### 📍 Quick Risk Check (Live API) — For Everyone")
st.info("💡 Tip: Click 'Use My Current Location' → allow permission → coordinates auto-fill. Or type place name via search.")
# Geolocation autofill for common people
auto_lat, auto_lon = geolocation_autofill("home")
# Optional place search (reverse lookup helper)
with st.expander("🔍 Search by place name (e.g. Guwahati, Shillong)"):
    q = st.text_input("Place name:", key="home_place")
    if q:
        try:
            r = httpx.get(f"{API_BASE}{API_PREFIX}/geocode/search", params={"place": q}, timeout=8)
            if r.status_code == 200 and r.json().get("found"):
                j = r.json()
                st.success(f"Found: {j['display_name']} → {j['latitude']:.4f}, {j['longitude']:.4f}")
                if st.button("Use this place", key="use_place_home"):
                    st.query_params["lat"] = str(j["latitude"])
                    st.query_params["lon"] = str(j["longitude"])
                    st.query_params["geo"] = "home"
                    st.rerun()
            else:
                st.warning("Place not found, try district name")
        except Exception as e:
            st.warning(f"Search failed: {e}")

col1, col2, col3 = st.columns([2, 2, 1])
default_lat = float(auto_lat) if auto_lat is not None else 26.1445
default_lon = float(auto_lon) if auto_lon is not None else 91.7362
with col1:
    lat = st.number_input("Latitude", value=default_lat, format="%.4f", key="home_lat", help="Your north-south position. Use 📍 button to auto-fill")
with col2:
    lon = st.number_input("Longitude", value=default_lon, format="%.4f", key="home_lon", help="Your east-west position. Use 📍 button to auto-fill")
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    check = st.button("Get Risk Score", type="primary", use_container_width=True, help="Checks live rain + slope + soil for your location")
# New connection: toggle to use improved satellite-fused prediction
use_improved = st.checkbox("✨ Use improved (satellite AI + fusion) — new connection", value=False, help="When on, calls /assess?improved=true → fused satellite+env evidence, shows 🛰️ signals. Off = existing RF/XGB only. You can compare.")
st.caption("New backend connection: `improved=false` → existing model, `improved=true` → satellite-fused (additive, fallback to existing if satellite unavailable)")

if check:
    with st.spinner(f"Calling {'improved satellite-fused' if use_improved else 'strong connected'} backend..."):
        # Best prediction via /assess (new connection: improved uses fusion)
        try:
            ar = httpx.get(f"{API_BASE}{API_PREFIX}/assess", params={"latitude": lat, "longitude": lon, "improved": str(use_improved).lower()}, timeout=12)
            if ar.status_code == 200:
                a = ar.json()
                score = a["risk_score"]; level = a["risk_level"]; conf = a["confidence"]
                color = {"CRITICAL": "#dc3545", "HIGH": "#fd7e14", "MODERATE": "#ffc107", "LOW": "#28a745"}.get(level, "#6c757d")
                level_t = t(f"risk_levels.{level}") if level in ["LOW","MODERATE","HIGH","CRITICAL"] else level
                src = t("live_source") if a.get("is_live") else t("synthetic_source")
                st.markdown(f'<div class="metric-card" style="border-left-color: {color};background:#ffffff;border:1px solid #e0e0e0;color:#212529"><h2 style="margin:0;color:{color}">{t("risk_score")}: {score}/100 ({level_t}) — {a["priority"]}</h2><p style="margin:4px 0 0 0;color:#424242">{t("confidence")}: <b>{conf}%</b> • {a["place_name"] or ""} • Model: {a.get("model_version","")} • {src}</p><p style="margin:4px 0 0 0;color:#1b5e20"><b>Action:</b> {a.get("action","")}</p></div>', unsafe_allow_html=True)
                st.progress(conf/100, text=f"{t('confidence')}: {conf}% • {a['rationale']}")
                if level in ("HIGH","CRITICAL") and a.get("alternatives"):
                    st.warning("🔀 Impactful alternative — go to nearby safe LOW zone instead:")
                    for alt in a["alternatives"][:3]:
                        st.markdown(f"- **{alt['name']}** {alt['distance_km']}km → {alt['risk_level']} ({alt['risk_score']}/100)")
                st.caption(f"Strong backend: risk Engine + priority + geocode + weather in one call. Thresholds 30/60/80. Previous predictions still work.")
                # Also save to DB via predictions for history
                api_post("/predictions", {"latitude": lat, "longitude": lon, "save": True})
            else:
                raise Exception(ar.text)
        except Exception as e:
            # fallback to old
            result = api_post("/predictions", {"latitude": lat, "longitude": lon, "save": True})
            if result and "risk_score" in result:
                score = result["risk_score"]; level = result["risk_level"]; prob = result.get("probability", score/100); conf = int(round(prob*100))
                color = {"CRITICAL": "#dc3545", "HIGH": "#fd7e14", "MODERATE": "#ffc107", "LOW": "#28a745"}.get(level, "#6c757d")
                level_t = t(f"risk_levels.{level}") if level in ["LOW","MODERATE","HIGH","CRITICAL"] else level
                src = t("live_source") if not result.get("is_synthetic", True) else t("synthetic_source")
                st.markdown(f'<div class="metric-card" style="border-left-color: {color};background:#ffffff;border:1px solid #e0e0e0;color:#212529"><h2 style="margin:0;color:{color}">{t("risk_score")}: {score}/100 ({level_t})</h2><p style="margin:4px 0 0 0;color:#424242">{t("confidence")}: <b>{conf}%</b> • Model: {result.get("model_version", "n/a")} • {src}</p></div>', unsafe_allow_html=True)
                st.progress(conf/100, text=f"{t('confidence')}: {conf}%")
                weather_tracking_card(lat, lon, API_BASE, API_PREFIX, improved=use_improved)
            else:
                st.error(f"Failed: {e} / {result if 'result' in locals() else ''}")
            # Alert handling perspective - work on numbers efficiently
            if 'level' in locals():
                st.markdown("#### 🚨 Alert Handling — Efficiency Numbers")
                st.info(f"Score {score} → Level {level_t}. Efficiency: Alerts fire only at HIGH/CRITICAL (≥60). This one: {'will alert authorities + SMS' if level in ['HIGH','CRITICAL'] else 'no alert, just monitor'}. P1/P2/P3 prioritisation uses road exposure.")
# Show weather tracking even without click if auto-located
if auto_lat is not None and not check:
    st.markdown("#### 🌦️ Live Weather Tracking for Your Location")
    weather_tracking_card(auto_lat, auto_lon, API_BASE, API_PREFIX, improved=use_improved)

st.markdown("---")

# Recent data table - show actual locations
st.markdown("### Monitored Locations (Top 10 by Risk)")
if isinstance(risks, list) and risks:
    df = pd.DataFrame(risks)
    if "risk_score" in df.columns:
        df = df.sort_values("risk_score", ascending=False).head(10)
        display = df[["latitude", "longitude", "risk_score", "risk_level", "model_version"]].copy()
        display.columns = ["Lat", "Lon", "Score", "Level", "Model"]
        st.dataframe(display, use_container_width=True, hide_index=True)
else:
    st.info("No data yet. Try clicking buttons on other pages first.")

st.markdown("---")
st.caption("All data above is fetched live from running services. Click sidebar buttons to refresh.")
# Note: do not call stcli.main() here - Streamlit runs this file directly via `streamlit run frontend/app.py`
