"""Alerts - Emergency alert management."""
from __future__ import annotations

import os

import httpx
import pandas as pd
import streamlit as st

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
API_PREFIX = os.environ.get("API_PREFIX", "/api/v1")

st.set_page_config(page_title="Alerts - NER", page_icon="A", layout="wide")


@st.cache_data(ttl=10)
def api_get(path: str):
    try:
        r = httpx.get(f"{API_BASE}{API_PREFIX}{path}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return [str(e)]


def api_post(path: str, payload: dict):
    try:
        r = httpx.post(f"{API_BASE}{API_PREFIX}{path}", json=payload, timeout=15.0)
        return r.status_code, r.json() if r.status_code < 500 else {"error": r.text}
    except Exception as e:
        return 0, {"error": str(e)}


st.markdown("# Emergency Alerts - NER")
st.markdown("**Active alerts — Simple for everyone: 🟢 Safe, 🟡 Caution, 🟠 Danger, 🔴 Emergency**")
st.info("👋 For common people: If you see HIGH/CRITICAL alert for your area, stay away from hill slopes, don't travel, listen to radio/official SMS. This page shows all active danger alerts.")
try:
    from components import geolocation_autofill
except Exception:
    from frontend.components import geolocation_autofill
auto_lat, auto_lon = geolocation_autofill("alerts")
with st.sidebar:
    st.markdown("### 📍 Trigger Alert for Your Location")
    st.caption("Allow location → auto-fill → test your area")
    def_lat = float(auto_lat) if auto_lat else 26.14
    def_lon = float(auto_lon) if auto_lon else 91.74
    c1, c2 = st.columns(2)
    lat = c1.number_input("Lat", value=def_lat, format="%.4f", key="alert_lat", help="Use 📍 above")
    lon = c2.number_input("Lon", value=def_lon, format="%.4f", key="alert_lon", help="Use 📍 above")
    if st.button("Fire Test Alert", use_container_width=True, type="primary"):
        with st.spinner("Scoring location..."):
            code, body = api_post("/predictions", {"latitude": lat, "longitude": lon, "save": True})
            if code in (200, 201) and body.get("risk_level") in ("HIGH", "CRITICAL"):
                st.success(f"Alert fired! Risk: {body['risk_score']} ({body['risk_level']})")
            elif code in (200, 201):
                st.info(f"Risk is {body['risk_level']} (score {body['risk_score']}). No alert fires (need HIGH/CRITICAL).")
            else:
                st.error(f"Failed: {body}")
            st.cache_data.clear()
            st.rerun()
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

alerts = api_get("/alerts")
if not isinstance(alerts, list):
    alerts = []
if alerts and isinstance(alerts[0], str):
    st.error(f"API Error: {alerts[0]}")
    alerts = []

st.markdown(f"### Active Alerts ({len(alerts)})")
if alerts:
    df = pd.DataFrame(alerts)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(df))
    c2.metric("CRITICAL", int((df["severity"] == "CRITICAL").sum()))
    c3.metric("HIGH", int((df["severity"] == "HIGH").sum()))
    if len(df) > 0:
        c4.metric("Most recent", str(df.iloc[0].get("created_at", "n/a"))[:19])
    else:
        c4.metric("Most recent", "n/a")
    # Efficiency: work on numbers
    st.markdown("#### 📊 Alert Efficiency — Make numbers useful")
    try:
        # Fetch predictions to compute conversion
        import httpx, os
        API_BASE2 = os.environ.get("API_BASE", "http://127.0.0.1:8000")
        API_PREFIX2 = os.environ.get("API_PREFIX", "/api/v1")
        risks = httpx.get(f"{API_BASE2}{API_PREFIX2}/risk/current", timeout=8).json() if True else []
        if isinstance(risks, list) and risks:
            total_pred = len(risks)
            high_crit = sum(1 for r in risks if r.get("risk_level") in ("HIGH","CRITICAL"))
            conv = (len(df)/high_crit*100) if high_crit else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Predictions (live)", total_pred)
            c2.metric("High/Critical zones", high_crit)
            c3.metric("Alert conversion", f"{conv:.0f}%")
            st.caption("Efficient handling: alerts fire only when score ≥60 (HIGH/CRITICAL). This reduces noise — only 15-25% of predictions become alerts. Prioritise P1 first.")
        else:
            st.caption("Efficiency: HIGH/CRITICAL → alert, LOW/MODERATE → monitor (saves SMS cost, avoids fatigue)")
    except Exception:
        pass

    st.markdown("---")
    st.markdown("### Alert List")
    display = df[["id", "severity", "message", "language", "created_at"]].copy()
    display.columns = ["ID", "Severity", "Message", "Lang", "Created"]
    st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### Delivery Status")
    sel = st.selectbox("Select alert to inspect", df["id"].tolist())
    if st.button("Load Deliveries"):
        deliveries = api_get(f"/alerts/{int(sel)}/deliveries")
        if isinstance(deliveries, list) and deliveries and not isinstance(deliveries[0], str):
            ddf = pd.DataFrame(deliveries)
            st.dataframe(ddf, use_container_width=True, hide_index=True)
        else:
            st.info("No delivery records for this alert")
else:
    st.info("No alerts. Trigger one using the sidebar.")
    st.markdown("---")
    st.markdown("### How alerts work")
    st.markdown(
        "- Score 0-30 = **LOW** (no alert)\n"
        "- Score 31-60 = **MODERATE** (no alert)\n"
        "- Score 61-80 = **HIGH** (alert fires to all channels)\n"
        "- Score 81-100 = **CRITICAL** (alert fires, all recipients notified)\n\n"
        "**Currently configured channels:** log (always), sms (stub), push (stub)"
    )
