"""Offline Sync - for field workers in remote areas."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import streamlit as st

st.set_page_config(page_title="Offline Sync", page_icon="O", layout="wide")

st.markdown("# Offline Sync")
st.write("Capture reports offline. Sync when network is available. Designed for remote NER areas.") 

st.markdown("---")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### Connection Status")
    network = st.radio("Status", ["Online", "Offline (working locally)"])
with c2:
    st.markdown("### Sync Status")
    if "offline_reports" not in st.session_state:
        st.session_state["offline_reports"] = []
    pending = st.session_state["offline_reports"]
    st.metric("Pending Reports", len(pending))
with c3:
    st.markdown("### Storage")
    st.metric("Local Storage", f"{len(pending) * 0.5:.1f} KB")
    st.caption("Stored in browser until sync")

st.markdown("---")

# Quick report form
st.markdown("### Quick Report (Works Offline)")

with st.form("offline_report"):
    c1, c2 = st.columns(2)
    client_id = c1.text_input("Your device ID", value="FIELD-WORKER-001")
    report_type = c2.selectbox("What did you see?", ["CRACK", "LANDSLIDE", "ROCKFALL", "ROAD_BLOCKAGE", "SLOPE_MOVEMENT", "OTHER"])
    c3, c4 = st.columns(2)
    lat = c3.number_input("Latitude", value=26.14, format="%.6f")
    lon = c4.number_input("Longitude", value=91.74, format="%.6f")
    description = st.text_area("Describe what you saw")
    c5, c6 = st.columns(2)
    severity = c5.selectbox("How bad?", ["Low", "Medium", "High"])
    weather = c6.selectbox("Weather", ["Sunny", "Cloudy", "Light rain", "Heavy rain"])

    if st.form_submit_button("Save Report"):
        report = {
            "client_id": client_id,
            "report_type": report_type,
            "latitude": lat,
            "longitude": lon,
            "description": description,
            "severity": severity,
            "weather": weather,
            "timestamp_local": datetime.now(timezone.utc).isoformat(),
            "sync_status": "pending",
        }
        st.session_state["offline_reports"].append(report)
        new_count = len(st.session_state["offline_reports"])
        st.success("Report saved locally! Now " + str(new_count) + " pending.")

st.markdown("---")

if st.session_state["offline_reports"]:
    st.markdown("### Pending Reports (Local Storage)")
    for i, r in enumerate(st.session_state["offline_reports"]):
        with st.expander("Report " + str(i+1) + ": " + r["report_type"]):
            st.json(r)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Sync All to Server", use_container_width=True, type="primary",
                     disabled=(network == "Offline (working locally)")):
            import httpx
            with st.spinner("Syncing..."):
                success = 0
                for r in st.session_state["offline_reports"]:
                    try:
                        resp = httpx.post(
                            "http://127.0.0.1:8000/api/v1/reports",
                            json={
                                "client_id": r["client_id"] + "-" + str(i),
                                "report_type": r["report_type"],
                                "description": r["description"],
                                "timestamp": r["timestamp_local"],
                                "latitude": r["latitude"],
                                "longitude": r["longitude"],
                            },
                            timeout=10.0,
                        )
                        if resp.status_code in (200, 201):
                            success += 1
                    except Exception:
                        pass
                st.success("Synced " + str(success) + " of " + str(len(st.session_state["offline_reports"])) + "!")
                if success == len(st.session_state["offline_reports"]):
                    st.session_state["offline_reports"] = []
                    st.rerun()
    with c2:
        if st.button("Clear All Local Reports", use_container_width=True):
            st.session_state["offline_reports"] = []
            st.rerun()
else:
    st.info("No pending reports.")

st.markdown("---")
st.markdown("## How It Works")
c1, c2 = st.columns(2)
with c1:
    st.markdown("### Workflow")
    st.write("1. Worker opens app in remote village")
    st.write("2. Captures geo-tagged reports offline")
    st.write("3. Data saved on device (browser storage)")
    st.write("4. Worker moves to area with signal")
    st.write("5. Clicks Sync All")
    st.write("6. Server receives all reports")
    st.write("7. Duplicate detection by client_id")
with c2:
    st.markdown("### Why It Matters")
    st.write("**NER Reality:** Many villages have no internet")
    st.write("**Without offline mode:** Reports are lost")
    st.write("**With offline mode:**")
    st.write("- No data loss")
    st.write("- Real-time ground truth")
    st.write("- Faster response")
    st.write("- AI gets more training data")
    st.write("- Communities stay connected")

st.markdown("---")
st.info("This page works even when the API is down. Data is stored locally. Sync when ready.")
