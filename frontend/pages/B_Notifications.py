"""Multilingual Notifications - for SMS/app alerts in local languages."""
from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Multilingual Notifications", page_icon="N", layout="wide")

ROOT = Path(__file__).resolve().parents[2]
I18N_DIR = ROOT / "frontend" / "i18n"

# Load translations
@st.cache_data
def load_translations():
    translations = {}
    for f in I18N_DIR.glob("*.json"):
        lang = f.stem
        try:
            translations[lang] = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            translations[lang] = {}
    return translations


TRANSLATIONS = load_translations()
LANG_NAMES = {"en": "English", "hi": "Hindi", "as": "Assamese"}

st.markdown("# Multilingual Notifications")
st.write("Configure alert messages in local languages. Sent via SMS, app notifications, or web alerts.")

st.markdown("---")

# Tabs for each language
if TRANSLATIONS:
    available = list(TRANSLATIONS.keys())
    tabs = st.tabs([LANG_NAMES.get(l, l) for l in available])

    for i, lang in enumerate(available):
        with tabs[i]:
            st.markdown("### Alert Templates (" + LANG_NAMES.get(lang, lang) + ")")
            t = TRANSLATIONS[lang]

            for key, value in t.items():
                label = key.replace("_", " ").title()
                st.text_area(label, value=str(value), key=f"{lang}_{key}", height=68)

    st.markdown("---")
    st.markdown("### Preview Alert")

    c1, c2, c3 = st.columns(3)
    with c1:
        risk_level = st.selectbox("Risk Level", ["LOW", "MODERATE", "HIGH", "CRITICAL"])
    with c2:
        location = st.text_input("Location name", value="Guwahati")
    with c3:
        language = st.selectbox("Language", [LANG_NAMES.get(l, l) for l in available])

    lang_code = [k for k, v in LANG_NAMES.items() if v == language][0] if language in LANG_NAMES.values() else "en"
    t = TRANSLATIONS.get(lang_code, {})

    # Build preview
    if risk_level == "LOW":
        template = t.get("risk_low", "Risk is low at {location}.")
    elif risk_level == "MODERATE":
        template = t.get("risk_moderate", "Moderate risk at {location}.")
    elif risk_level == "HIGH":
        template = t.get("risk_high", "HIGH RISK at {location}! Take precautions.")
    else:
        template = t.get("risk_critical", "CRITICAL RISK at {location}! Evacuate immediately.")

    try:
        message = template.format(location=location)
    except Exception:
        message = template

    st.text_area("Preview", value=message, height=100)

    st.markdown("---")
    st.markdown("### Delivery Channels")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Currently Active**")
        st.write("- In-app dashboard alerts (active)")
        st.write("- Log channel (active)")
    with c2:
        st.markdown("**Configurable (need API keys)**")
        st.write("- SMS via MSG91 (Indian SMS gateway)")
        st.write("- Push via Firebase")
        st.write("- Email via SMTP")

    st.info("To enable SMS/Push notifications, add MSG91_API_KEY or FIREBASE_CREDENTIALS to .env")
else:
    st.warning("No translation files found. Add files to " + str(I18N_DIR))
