"""Field Reports - Submit and view citizen/field reports."""
from __future__ import annotations

import os

import httpx
import pandas as pd
import streamlit as st

try:
    from components import geolocation_autofill, weather_tracking_card
except Exception:
    from frontend.components import geolocation_autofill, weather_tracking_card

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
API_PREFIX = os.environ.get("API_PREFIX", "/api/v1")

st.set_page_config(page_title="Field Reports - NER", page_icon="R", layout="wide")


@st.cache_data(ttl=10)
def api_get(path: str):
    try:
        r = httpx.get(f"{API_BASE}{API_PREFIX}{path}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def api_post(path: str, payload: dict):
    try:
        r = httpx.post(f"{API_BASE}{API_PREFIX}{path}", json=payload, timeout=10.0)
        return r.status_code, r.json() if r.status_code < 500 else {"error": r.text}
    except Exception as e:
        return 0, {"error": str(e)}


def api_patch(path: str, payload: dict):
    try:
        r = httpx.patch(f"{API_BASE}{API_PREFIX}{path}", json=payload, timeout=10.0)
        return r.status_code, r.json() if r.status_code < 500 else {"error": r.text}
    except Exception as e:
        return 0, {"error": str(e)}


st.markdown("# Field Reports - NER")
st.markdown("**Submit and track field observations — Made simple for common people**")
st.info("📱 Common people: See a crack, fallen rock, or blocked road? Tap 📍 to auto-fill your location, choose type, add photo link, submit. Your report helps save lives.")
st.markdown("**Tags:** `CRACK`=ground crack `LANDSLIDE`=mud/rock slide `ROCKFALL`=stones falling `ROAD_BLOCKAGE`=road closed `SLOPE_MOVEMENT`=hill moving")

# Sidebar
with st.sidebar:
    st.markdown("### Quick Reports")
    st.markdown("Use the buttons below to file sample reports.")
    if st.button("File: Crack in Imphal", use_container_width=True):
        import uuid
        payload = {
            "client_id": str(uuid.uuid4()),
            "report_type": "CRACK",
            "description": "Visible ground crack after recent rain",
            "timestamp": "2024-06-15T12:00:00Z",
            "latitude": 24.82, "longitude": 93.94,
        }
        code, _ = api_post("/reports", payload)
        if code in (200, 201):
            st.cache_data.clear()
            st.success("Filed!")
            st.rerun()
    if st.button("File: Road Blockage in Shillong", use_container_width=True):
        import uuid
        payload = {
            "client_id": str(uuid.uuid4()),
            "report_type": "ROAD_BLOCKAGE",
            "description": "Rockslide blocking NH-6",
            "timestamp": "2024-06-15T12:00:00Z",
            "latitude": 25.58, "longitude": 91.88,
        }
        code, _ = api_post("/reports", payload)
        if code in (200, 201):
            st.cache_data.clear()
            st.success("Filed!")
            st.rerun()
    if st.button("File: Rockfall in Guwahati", use_container_width=True):
        import uuid
        payload = {
            "client_id": str(uuid.uuid4()),
            "report_type": "ROCKFALL",
            "description": "Large boulder fell on road",
            "timestamp": "2024-06-15T12:00:00Z",
            "latitude": 26.14, "longitude": 91.74,
        }
        code, _ = api_post("/reports", payload)
        if code in (200, 201):
            st.cache_data.clear()
            st.success("Filed!")
            st.rerun()
    if st.button("Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Geolocation autofill for reports (common people)
st.markdown("### 📍 Your Location (one-click)")
auto_lat, auto_lon = geolocation_autofill("reports")
if auto_lat is not None:
    weather_tracking_card(auto_lat, auto_lon, API_BASE, API_PREFIX)

# Submit form
st.markdown("### Submit New Report — Simple Form")
with st.form("report_form"):
    c1, c2 = st.columns(2)
    client_id = c1.text_input("Client ID (UUID)", value="", help="Auto ID - leave blank")
    if not client_id:
        import uuid
        client_id = str(uuid.uuid4())
        c1.caption(f"Auto-generated: {client_id[:8]}...")
    report_type = c2.selectbox(
        "Report Type (choose tag)",
        ["CRACK", "LANDSLIDE", "ROCKFALL", "ROAD_BLOCKAGE", "SLOPE_MOVEMENT", "OTHER"],
        help="Pick what you saw: Crack, Landslide, Rockfall, Road blocked, Hill moving",
    )
    c3, c4 = st.columns(2)
    def_lat = float(auto_lat) if auto_lat is not None else 26.14
    def_lon = float(auto_lon) if auto_lon is not None else 91.74
    latitude = c3.number_input("Latitude *", value=def_lat, format="%.6f", help="Tap 📍 above to auto-fill")
    longitude = c4.number_input("Longitude *", value=def_lon, format="%.6f", help="Tap 📍 above to auto-fill")
    description = st.text_area("Description (simple words)", placeholder="e.g. Big crack near road after rain, water flowing...")
    image_url = st.text_input("Image URL (optional)", help="Paste photo link if you have")
    if st.form_submit_button("Submit Report", type="primary"):
        payload = {
            "client_id": client_id,
            "report_type": report_type,
            "description": description,
            "image_url": image_url,
            "timestamp": "2024-06-15T12:00:00Z",
            "latitude": latitude,
            "longitude": longitude,
        }
        code, resp = api_post("/reports", payload)
        if code in (200, 201):
            st.success(f"Report filed! ID: {resp.get('id', '?')}")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(f"Failed: {resp}")

st.markdown("---")

# All reports
reports = api_get("/reports")
if isinstance(reports, list) and reports:
    st.markdown(f"### All Reports ({len(reports)} total)")
    df = pd.DataFrame(reports)
    c1, c2, c3, c4 = st.columns(4)
    type_counts = df["report_type"].value_counts()
    c1.metric("Total", len(df))
    c2.metric("CRACK", type_counts.get("CRACK", 0))
    c3.metric("LANDSLIDE", type_counts.get("LANDSLIDE", 0))
    c4.metric("ROAD_BLOCKAGE", type_counts.get("ROAD_BLOCKAGE", 0))
    display = df[["id", "client_id", "report_type", "description", "timestamp", "status", "latitude", "longitude"]]
    st.dataframe(display, use_container_width=True, hide_index=True)

    # Status update section
    st.markdown("### Update Report Status")
    c1, c2 = st.columns(2)
    report_id = c1.number_input("Report ID", min_value=1, value=1, step=1)
    new_status = c2.selectbox("New Status", ["RECEIVED", "VERIFIED", "REJECTED", "DUPLICATE"])
    if st.button("Update Status"):
        code, resp = api_patch(f"/reports/{int(report_id)}", {"status": new_status})
        if code in (200, 201):
            st.success("Status updated!")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error(f"Failed: {resp}")
else:
    st.info("No reports yet. Use the form above or click sidebar buttons to file some.")
