"""Road Connectivity Status - critical for NER where landslides block highways."""
from __future__ import annotations

import os
import httpx
import pandas as pd
import streamlit as st

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
API_PREFIX = os.environ.get("API_PREFIX", "/api/v1")

st.set_page_config(page_title="Road Connectivity - NER", page_icon="R", layout="wide")


@st.cache_data(ttl=15)
def api_get(path):
    try:
        r = httpx.get(f"{API_BASE}{API_PREFIX}{path}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=15)
def api_post(path, payload):
    try:
        r = httpx.post(f"{API_BASE}{API_PREFIX}{path}", json=payload, timeout=15.0)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


st.markdown("# Road Connectivity Status")
st.write("Real-time status of roads, highways, and critical infrastructure across NER")

# Major highways in NER
HIGHWAYS = [
    {"name": "NH-6 (Mizoram)", "from": "Guwahati", "to": "Aizawl", "key_towns": ["Shillong", "Aizawl"], "critical": True},
    {"name": "NH-37 (Assam)", "from": "Guwahati", "to": "Imphal", "key_towns": ["Nagaon", "Dimapur", "Imphal"], "critical": True},
    {"name": "NH-31 (Assam)", "from": "Guwahati", "to": "Silchar", "key_towns": ["Haflong", "Silchar"], "critical": True},
    {"name": "NH-29 (Nagaland)", "from": "Kohima", "to": "Mizoram", "key_towns": ["Kohima", "Imphal"], "critical": True},
    {"name": "NH-2 (Manipur)", "from": "Imphal", "to": "Moreh", "key_towns": ["Imphal", "Moreh"], "critical": False},
    {"name": "NH-44 (Meghalaya)", "from": "Guwahati", "to": "Shillong", "key_towns": ["Guwahati", "Shillong"], "critical": True},
    {"name": "NH-10 (Sikkim)", "from": "Siliguri", "to": "Gangtok", "key_towns": ["Gangtok", "Rangpo"], "critical": True},
    {"name": "NH-15 (Arunachal)", "from": "Tezpur", "to": "Tawang", "key_towns": ["Bomdila", "Tawang"], "critical": True},
]

# Get current risk data
risk_data = api_get("/risk/map")
reports = api_get("/reports")
points = risk_data.get("points", []) if isinstance(risk_data, dict) and "error" not in risk_data else []

# Compute road risk by checking nearest risk point
HIGHWAY_COORDS = {
    "NH-6 (Mizoram)": [(25.5, 92.0), (23.7, 92.7)],
    "NH-37 (Assam)": [(26.14, 91.74), (25.5, 93.0), (24.8, 93.94)],
    "NH-31 (Assam)": [(26.14, 91.74), (25.18, 92.85), (24.83, 92.8)],
    "NH-29 (Nagaland)": [(25.67, 94.11), (25.0, 93.5), (24.8, 93.94)],
    "NH-2 (Manipur)": [(24.8, 93.94), (24.3, 94.3)],
    "NH-44 (Meghalaya)": [(26.14, 91.74), (25.58, 91.88)],
    "NH-10 (Sikkim)": [(26.72, 88.43), (27.33, 88.62)],
    "NH-15 (Arunachal)": [(26.63, 92.79), (27.86, 91.69), (27.59, 91.87)],
}


def nearest_risk_score(coords, points):
    """Find max risk score near any point on the highway."""
    if not points:
        return 0
    max_score = 0
    for hlat, hlon in coords:
        for p in points:
            dlat = abs(p.get("latitude", 0) - hlat)
            dlon = abs(p.get("longitude", 0) - hlon)
            if dlat < 0.5 and dlon < 0.5:
                max_score = max(max_score, p.get("risk_score", 0))
    return max_score


def status_from_score(score):
    if score >= 81:
        return ("BLOCKED", "#e53e3e")
    elif score >= 61:
        return ("HIGH RISK", "#dd6b20")
    elif score >= 31:
        return ("CAUTION", "#d69e2e")
    return ("CLEAR", "#38a169")


# Summary cards
st.markdown("### Network Status Summary")
c1, c2, c3, c4, c5 = st.columns(5)
status_counts = {"CLEAR": 0, "CAUTION": 0, "HIGH RISK": 0, "BLOCKED": 0}
highway_statuses = {}
for hw in HIGHWAYS:
    coords = HIGHWAY_COORDS.get(hw["name"], [])
    score = nearest_risk_score(coords, points)
    status, color = status_from_score(score)
    highway_statuses[hw["name"]] = (status, color, score)
    status_counts[status] = status_counts.get(status, 0) + 1

c1.metric("CLEAR", status_counts["CLEAR"], delta=None)
c2.metric("CAUTION", status_counts["CAUTION"])
c3.metric("HIGH RISK", status_counts["HIGH RISK"])
c4.metric("BLOCKED", status_counts["BLOCKED"])
c5.metric("Total Highways", len(HIGHWAYS))

st.markdown("---")

# Highway status table
st.markdown("### Highway Status")

hw_data = []
for hw in HIGHWAYS:
    status, color, score = highway_statuses[hw["name"]]
    hw_data.append({
        "Highway": hw["name"],
        "Route": f"{hw['from']} <-> {hw['to']}",
        "Key Towns": ", ".join(hw["key_towns"]),
        "Status": status,
        "Max Risk Score": score,
        "Critical": "Yes" if hw["critical"] else "No",
    })

df = pd.DataFrame(hw_data)
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("---")

# Road blockage reports (from citizen reports)
st.markdown("### Active Road Blockages (from field reports)")
if isinstance(reports, list) and reports:
    blockage_reports = [r for r in reports if r.get("report_type") == "ROAD_BLOCKAGE" or "block" in str(r.get("description", "")).lower()]
    if blockage_reports:
        for r in blockage_reports[:10]:
            st.warning(f"**{r.get('location', 'Unknown')}** - {r.get('description', 'No details')} (Status: {r.get('status', 'PENDING')})")
    else:
        st.success("No active road blockages reported.")
else:
    st.info("No reports submitted yet.")

st.markdown("---")

# Check risk at a specific highway
st.markdown("### Check Highway Risk")
col1, col2, col3 = st.columns(3)
with col1:
    selected_hw = st.selectbox("Select Highway", [hw["name"] for hw in HIGHWAYS])
with col2:
    coords = HIGHWAY_COORDS.get(selected_hw, [])
    if coords:
        lat, lon = st.selectbox("Select Point", [(f"{c[0]:.2f}, {c[1]:.2f}", c) for c in coords], format_func=lambda x: x[0] if isinstance(x, tuple) else x)[1]
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Check Risk", use_container_width=True, type="primary"):
        with st.spinner("Scoring..."):
            result = api_post("/predictions", {"latitude": lat, "longitude": lon, "save": False})
            if "risk_score" in result:
                score = result["risk_score"]
                level = result["risk_level"]
                conf = result.get("confidence", 0)
                c = {"CRITICAL": "#e53e3e", "HIGH": "#dd6b20", "MODERATE": "#d69e2e", "LOW": "#38a169"}.get(level, "#3182ce")
                st.markdown(f'<div style="background:{c}20;padding:1rem;border-radius:8px;border-left:4px solid {c}"><h3 style="margin:0;color:{c}">Risk Score: {score}/100 ({level})</h3><p style="margin:0">Confidence: {conf:.0%} | Model: {result.get("model_version", "n/a")}</p></div>', unsafe_allow_html=True)
            else:
                st.error("Failed to score")

st.markdown("---")
st.caption("Data sources: real-time risk predictions + citizen field reports. Highways are key NER corridors connecting state capitals.")
