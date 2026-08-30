"""Help for Common People - Simple, multilingual, user-friendly."""
from __future__ import annotations

import os

import httpx
import streamlit as st

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
API_PREFIX = os.environ.get("API_PREFIX", "/api/v1")

st.set_page_config(page_title="Help for Common People", page_icon="H", layout="wide")


@st.cache_data(ttl=15)
def api_get(path):
    try:
        r = httpx.get(f"{API_BASE}{API_PREFIX}{path}", timeout=10.0)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


st.markdown("# Help for Common People")
st.write("**Simple help in your language. No technical words.**")

st.markdown("---")

# Language selector
lang = st.radio("Choose your language", ["English", "Hindi", "Assamese"], horizontal=True)

st.markdown("---")

# Simple risk check
st.markdown("## Is My Area Safe? Check Now")

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    lat = st.number_input("Latitude", value=26.14, format="%.4f", key="c_lat")
with col2:
    lon = st.number_input("Longitude", value=91.74, format="%.4f", key="c_lon")
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    check = st.button("Check", use_container_width=True, type="primary")

if check:
    with st.spinner("Checking..."):
        try:
            r = httpx.post(
                f"{API_BASE}{API_PREFIX}/predictions",
                json={"latitude": lat, "longitude": lon, "save": False},
                timeout=15.0,
            )
            r.raise_for_status()
            data = r.json()
            score = data.get("risk_score", 0)
            level = data.get("risk_level", "UNKNOWN")
            conf = data.get("confidence", 0) * 100
            if level == "CRITICAL":
                color, message = "#e53e3e", "DANGER! Leave the area NOW!"
            elif level == "HIGH":
                color, message = "#dd6b20", "HIGH RISK. Be ready to leave."
            elif level == "MODERATE":
                color, message = "#d69e2e", "MODERATE. Stay alert."
            else:
                color, message = "#38a169", "LOW RISK. Area is relatively safe."
            st.markdown(f'<div style="background:{color}20;padding:2rem;border-radius:12px;border-left:6px solid {color};text-align:center"><h1 style="color:{color};margin:0">{level}</h1><h2 style="margin:0">Score: {score}/100</h2><p>{message}</p><p>Confidence: {conf:.0f}%</p></div>', unsafe_allow_html=True)
        except Exception as e:
            st.error("Could not check. Please try again. Error: " + str(e))

st.markdown("---")

# Three big buttons
st.markdown("## What Do You Need?")

b1, b2, b3 = st.columns(3)
with b1:
    if st.button("REPORT A PROBLEM", use_container_width=True, type="primary"):
        st.switch_page("pages/3_Reports.py")
with b2:
    if st.button("SEE DANGER ZONES", use_container_width=True):
        st.switch_page("pages/1_Map.py")
with b3:
    if st.button("EMERGENCY HELP", use_container_width=True):
        st.switch_page("pages/9_Awareness.py")

st.markdown("---")

# Emergency contacts
st.markdown("## Emergency Phone Numbers")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown("### NDRF")
    st.markdown("# **1077**")
    st.caption("National Disaster Response Force")
with c2:
    st.markdown("### Police")
    st.markdown("# **100**")
    st.caption("Police Emergency")
with c3:
    st.markdown("### Fire")
    st.markdown("# **101**")
    st.caption("Fire Service")
with c4:
    st.markdown("### Ambulance")
    st.markdown("# **108**")
    st.caption("Medical Emergency")

st.markdown("---")

# Safety tips in selected language
if lang == "English":
    st.markdown("## Safety Tips")
    tips = [
        "If you see cracks in the ground or walls, move to higher ground",
        "Stay away from rivers and streams during heavy rain",
        "Listen to local FM radio for warnings",
        "Keep your phone charged for emergencies",
        "Help elderly and children first if evacuation is needed",
        "Don't believe rumors - check this app or official sources",
    ]
elif lang == "Hindi":
    st.markdown("## सुरक्षा सुझाव")
    tips = [
        "यदि जमीन या दीवारों में दरारें दिखें, ऊंची जगह जाएं",
        "भारी बारिश में नदियों से दूर रहें",
        "चेतावनी के लिए FM रेडियो सुनें",
        "फोन चार्ज रखें",
        "बुजुर्गों और बच्चों की पहले मदद करें",
        "अफवाहों पर विश्वास न करें",
    ]
else:
    st.markdown("## সুৰক্ষা পৰামৰ্শ")
    tips = [
        "মাটি বা দেৱালত ফাট দেখিলে ওখৰ ঠাইলৈ যাওক",
        "ধাৰাসাৰ বৰষুণৰ সময়ত নৈৰ পৰা আঁতৰত থাকক",
        "সতৰ্কবাৰ্তাৰ বাবে স্থানীয় FM ৰেডিঅ শুনক",
        "ফোন চাৰ্জ কৰি ৰাখক",
        "বয়সীয়া আৰু শিশুক প্ৰথমে সহায় কৰক",
        "গুজবত বিশ্বাস নকৰিব",
    ]

for tip in tips:
    st.markdown("- " + tip)

st.markdown("---")

# Quick navigation
st.markdown("## Other Pages")
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("View Map", use_container_width=True):
        st.switch_page("pages/1_Map.py")
    if st.button("Report Incident", use_container_width=True):
        st.switch_page("pages/3_Reports.py")
with c2:
    if st.button("Alerts & Warnings", use_container_width=True):
        st.switch_page("pages/4_Alerts.py")
    if st.button("Offline Mode", use_container_width=True):
        st.switch_page("pages/A_Offline_Sync.py")
with c3:
    if st.button("Awareness Guide", use_container_width=True):
        st.switch_page("pages/9_Awareness.py")
    if st.button("Road Status", use_container_width=True):
        st.switch_page("pages/7_Road_Connectivity.py")

st.markdown("---")
st.caption("This page is for everyone. If you find it useful, share it with your community.")
