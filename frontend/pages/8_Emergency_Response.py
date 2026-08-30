"""Emergency Response Dashboard - with P1/P2/P3 priority engine."""
from __future__ import annotations

import os
import httpx
import pandas as pd
import streamlit as st

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
API_PREFIX = os.environ.get("API_PREFIX", "/api/v1")

st.set_page_config(page_title="Emergency Response - NER", page_icon="E", layout="wide")


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


st.markdown("# Emergency Response Dashboard")
st.write("Prioritized response actions for high-risk zones with P1/P2/P3 classification")

# Get data
risk_map = api_get("/risk/map")
reports = api_get("/reports")
alerts = api_get("/alerts")
points = risk_map.get("points", []) if isinstance(risk_map, dict) and "error" not in risk_map else []

# Sidebar controls
with st.sidebar:
    st.markdown("### Quick Actions")
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.markdown("### Priority Guide")
    st.markdown("**P1 = Critical** - Immediate action")
    st.markdown("  - Evacuation required")
    st.markdown("  - Deploy rescue teams")
    st.markdown("  - Close affected roads")
    st.markdown("**P2 = High** - Within 24 hours")
    st.markdown("  - Alert district officials")
    st.markdown("  - Pre-position resources")
    st.markdown("  - Issue public warnings")
    st.markdown("**P3 = Moderate** - Within 72 hours")
    st.markdown("  - Monitor conditions")
    st.markdown("  - Prepare contingency plans")

# Summary
critical_count = sum(1 for p in points if p.get("risk_level") == "CRITICAL")
high_count = sum(1 for p in points if p.get("risk_level") == "HIGH")
moderate_count = sum(1 for p in points if p.get("risk_level") == "MODERATE")

# Emergency status
if critical_count > 0:
    st.error(f"**EMERGENCY ACTIVE** - {critical_count} critical zones require immediate response")
elif high_count > 0:
    st.warning(f"**HIGH ALERT** - {high_count} high-risk zones need attention within 24 hours")
else:
    st.success("**NORMAL** - No critical or high-risk zones at this time")

# Priority counts
st.markdown("### Priority Overview")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("P1 (Critical)", critical_count, delta="IMMEDIATE" if critical_count > 0 else None)
c2.metric("P2 (High)", high_count, delta="24 HOURS" if high_count > 0 else None)
c3.metric("P3 (Moderate)", moderate_count, delta="72 HOURS")
c4.metric("Active Alerts", len(alerts) if isinstance(alerts, list) else 0)
c5.metric("Field Reports", len(reports) if isinstance(reports, list) else 0)
c6.metric("Total Monitored", len(points))

st.markdown("---")

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["Priority Actions", "Response Checklist", "Resource Allocation"])

with tab1:
    st.markdown("### Immediate Priority Actions")
    
    # Sort by risk score
    sorted_points = sorted(points, key=lambda x: -x.get("risk_score", 0))
    
    for p in sorted_points[:10]:
        score = p.get("risk_score", 0)
        level = p.get("risk_level", "LOW")
        if level == "CRITICAL":
            priority = "P1"
            color = "#e53e3e"
            actions = ["EVACUATE", "Deploy rescue", "Close roads", "Alert hospitals"]
        elif level == "HIGH":
            priority = "P2"
            color = "#dd6b20"
            actions = ["Alert officials", "Pre-position", "Public warning", "Evacuate if needed"]
        else:
            priority = "P3"
            color = "#d69e2e"
            actions = ["Monitor", "Prepare contingency", "Community awareness"]
        
        st.markdown(f'<div style="background:{color}15;padding:0.8rem;border-radius:8px;border-left:4px solid {color};margin-bottom:0.5rem">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 3])
        with c1:
            st.markdown(f"**{priority}**")
            st.markdown(f"Score: **{score}**")
        with c2:
            st.markdown(f"**{p.get('name', 'Location')}**")
            st.markdown(f"Lat: {p.get('latitude', 0):.4f}, Lon: {p.get('longitude', 0):.4f}")
        with c3:
            st.markdown("**Recommended Actions:**")
            for a in actions:
                st.markdown(f"- {a}")
        st.markdown("</div>", unsafe_allow_html=True)

with tab2:
    st.markdown("### Standard Response Checklist")
    
    checklist = {
        "P1 - CRITICAL (Score 81-100)": [
            "Issue immediate evacuation order",
            "Deploy NDRF/SDRF teams within 2 hours",
            "Set up emergency shelters",
            "Close all affected roads",
            "Alert hospitals for mass casualties",
            "Activate emergency helpline",
            "Inform state CM and Governor",
            "Deploy mobile medical units",
        ],
        "P2 - HIGH (Score 61-80)": [
            "Alert district collector",
            "Pre-position rescue equipment",
            "Issue public warning via SMS",
            "Increase monitoring frequency",
            "Prepare evacuation routes",
            "Brief local hospitals",
        ],
        "P3 - MODERATE (Score 31-60)": [
            "Monitor weather updates",
            "Community awareness drive",
            "Check supply stocks",
            "Verify communication channels",
            "Update contingency plans",
        ],
    }
    
    for priority, items in checklist.items():
        with st.expander(f"**{priority}**"):
            for item in items:
                col1, col2 = st.columns([1, 9])
                with col1:
                    st.checkbox("", key=f"chk_{item[:20]}_{priority[:5]}")
                with col2:
                    st.write(item)

with tab3:
    st.markdown("### Resource Allocation by Priority")
    
    # Mock resource allocation based on priority
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Required Resources (P1 Zones)")
        st.metric("NDRF Teams", max(1, critical_count * 2))
        st.metric("Medical Units", max(1, critical_count))
        st.metric("Helicopters on Standby", 2)
        st.metric("Shelters to Activate", max(2, critical_count))
        st.metric("Estimated Personnel", critical_count * 50)
    with c2:
        st.markdown("#### Recommended Actions")
        if critical_count > 0:
            st.error("**IMMEDIATE EVACUATION** recommended for all P1 zones")
        if high_count > 0:
            st.warning("**PRE-EVACUATION** recommended for vulnerable areas in P2 zones")
        if moderate_count > 0:
            st.info("**MONITORING** required for P3 zones")
        st.markdown("---")
        st.markdown("#### Communication Channels")
        st.write("- SMS Gateway: Active")
        st.write("- Emergency Helpline: 1077")
        st.write("- District Control Rooms: All online")
        st.write("- Media Briefing: Scheduled as needed")

st.markdown("---")

# Get priority for a specific point
st.markdown("### Get Priority for a Location")
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    lat = st.number_input("Latitude", value=26.14, format="%.4f", key="priority_lat")
with col2:
    lon = st.number_input("Longitude", value=91.74, format="%.4f", key="priority_lon")
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Get Priority", use_container_width=True, type="primary"):
        with st.spinner("Computing priority..."):
            result = api_get(f"/priority/{lat}/{lon}")
            if "priority" in result:
                p = result["priority"]
                rationale = result.get("rationale", "")
                exposed = result.get("exposed_count", 0)
                color = {"P1": "#e53e3e", "P2": "#dd6b20", "P3": "#d69e2e"}.get(p, "#38a169")
                st.markdown(f'<div style="background:{color}20;padding:1rem;border-radius:8px;border-left:4px solid {color}"><h2 style="margin:0;color:{color}">{p}</h2><p>{rationale}</p><p>Exposed infrastructure: {exposed}</p></div>', unsafe_allow_html=True)
            else:
                st.error("Failed to get priority")
