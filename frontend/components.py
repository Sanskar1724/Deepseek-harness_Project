"""Reusable UI components for common people - geolocation, weather tracking, tags."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

# --- i18n helper ---
I18N_DIR = Path(__file__).parent / "i18n"

def get_lang() -> str:
    return st.session_state.get("lang", "en")

def set_lang(lang: str):
    st.session_state["lang"] = lang

def t(key: str) -> str:
    """Translate key like 'app_title' or 'risk_levels.LOW'."""
    lang = get_lang()
    try:
        data = json.loads((I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))
    except Exception:
        data = {}
    # fallback to en
    if lang != "en":
        try:
            en_data = json.loads((I18N_DIR / "en.json").read_text(encoding="utf-8"))
        except Exception:
            en_data = {}
    else:
        en_data = data
    parts = key.split(".")
    cur = data
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            cur = None
            break
    if cur is None or isinstance(cur, dict):
        # fallback en
        cur = en_data
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                return key
        if isinstance(cur, dict):
            return key
    return str(cur)

def language_selector():
    lang = st.sidebar.selectbox(
        "🌐 Language / भाषा / ভাষা",
        options=["en", "hi", "as"],
        format_func=lambda x: {"en": "English", "hi": "हिंदी", "as": "অসমীয়া"}[x],
        index=["en", "hi", "as"].index(get_lang()),
        key="lang_selector",
    )
    if lang != get_lang():
        set_lang(lang)
        st.rerun()
    return lang


def geolocation_autofill(key_prefix: str = "geo") -> tuple[float | None, float | None]:
    """One-click location permission that autofills lat/lon via query_params.

    Returns (lat, lon) if user just allowed, else (None, None).
    The HTML button asks for browser permission and reloads page with ?lat&lon.
    """
    # Read any existing query params (after reload)
    lat_q = st.query_params.get("lat")
    lon_q = st.query_params.get("lon")
    auto_lat = None
    auto_lon = None
    if lat_q and lon_q:
        try:
            auto_lat = float(lat_q if isinstance(lat_q, str) else lat_q[0] if isinstance(lat_q, list) else lat_q)
            auto_lon = float(lon_q if isinstance(lon_q, str) else lon_q[0] if isinstance(lon_q, list) else lon_q)
        except Exception:
            pass

    # HTML + JS: permission prompt and reload with coords
    components.html(
        f"""
        <div style="margin:4px 0;">
        <button id="geoBtn_{key_prefix}" style="background:#1e3a5f;color:white;border:none;padding:8px 14px;border-radius:6px;cursor:pointer;width:100%;font-weight:600;">
        📍 Use My Current Location (allow permission)
        </button>
        <div id="geoStatus_{key_prefix}" style="font-size:0.8rem;color:#555;margin-top:4px;"></div>
        <script>
        document.getElementById('geoBtn_{key_prefix}').onclick = function() {{
            const s = document.getElementById('geoStatus_{key_prefix}');
            s.innerText = "Requesting location... please allow permission";
            if (!navigator.geolocation) {{ s.innerText = "Geolocation not supported"; return; }}
            navigator.geolocation.getCurrentPosition(
                function(pos) {{
                    const lat = pos.coords.latitude.toFixed(6);
                    const lon = pos.coords.longitude.toFixed(6);
                    s.innerText = "Got: " + lat + ", " + lon + " - reloading...";
                    const url = new URL(window.parent.location.href);
                    url.searchParams.set('lat', lat);
                    url.searchParams.set('lon', lon);
                    url.searchParams.set('geo', '{key_prefix}');
                    window.parent.location.href = url.toString();
                }},
                function(err) {{ s.innerText = "Failed: " + err.message + " - please enter manually"; }},
                {{enableHighAccuracy:true, timeout:10000}}
            );
        }};
        </script>
        </div>
        """,
        height=70,
    )
    # Also offer clear button if autofilled
    if auto_lat is not None and st.query_params.get("geo") == key_prefix:
        st.success(f"📍 Location detected: {auto_lat:.5f}, {auto_lon:.5f} (auto-filled below)")
        if st.button("Clear auto location", key=f"clear_{key_prefix}"):
            st.query_params.clear()
            st.rerun()
        return auto_lat, auto_lon
    return None, None


def weather_tracking_card(lat: float, lon: float, api_base: str, api_prefix: str, improved: bool = False):
    """Show live weather for given coords - uses strong connected /assess."""
    import httpx

    # Try strong connected assess first (risk + priority + alternatives + place in one call)
    # improved=True uses satellite-fused prediction (new connection)
    try:
        r = httpx.get(f"{api_base}{api_prefix}/assess", params={"latitude": lat, "longitude": lon, "improved": str(improved).lower()}, timeout=12)
        if r.status_code == 200:
            d = r.json()
            score = d["risk_score"]
            level = d["risk_level"]
            color = {"LOW": "#28a745", "MODERATE": "#ffc107", "HIGH": "#fd7e14", "CRITICAL": "#dc3545"}.get(level, "#6c757d")
            st.markdown(
                f'<div style="background:#ffffff;padding:12px;border-radius:8px;border:1px solid #e0e0e0;border-left:5px solid {color}">'
                f'<b style="color:#212529">Live Risk at {lat:.4f}, {lon:.4f}</b> {d.get("place_name","")[:60]}<br>'
                f'<span style="color:#212529">Score </span><span style="color:{color};font-size:1.4rem">{score}/100</span> <span style="color:#212529">— <b>{level}</b> • {d["priority"]} • {d["confidence"]}% confidence</span><br>'
                f'<span style="font-size:0.85rem;color:#424242">{"LIVE" if d.get("is_live") else "Demo"} • {d.get("model_version","")} • {d.get("rationale","")}</span><br>'
                f'<span style="font-size:0.85rem;color:#1b5e20"><b>Action:</b> {d.get("action","")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            # Impactful alternative when HIGH/CRITICAL
            if level in ("HIGH", "CRITICAL") and d.get("alternatives"):
                st.warning(f"⚠️ Alternative safe options within 20km (connected backend found {len(d['alternatives'])}):")
                for alt in d["alternatives"][:3]:
                    st.markdown(f"- **{alt['name']}** — {alt['distance_km']}km away, {alt['risk_level']} ({alt['risk_score']}/100) at {alt['latitude']:.4f},{alt['longitude']:.4f}")
                st.caption("Impact: Take alternative route to LOW zone instead of risk zone — saves time & life")
            elif level in ("HIGH", "CRITICAL"):
                st.info("No nearby LOW zone in DB — stay put, follow official alert, use Help page shelters")
            else:
                st.success("No alternative needed — your area is safe")
            notation = {
                "LOW": "✅ Safe. Normal activities. Stay informed.",
                "MODERATE": "⚠️ Be alert. Avoid steep slopes after rain.",
                "HIGH": "🟠 High risk. Avoid travel on hills, keep emergency kit ready.",
                "CRITICAL": "🔴 CRITICAL! Stay away from slopes, follow official alerts, evacuate if told.",
            }
            st.info(notation.get(level, ""))
            if d.get("place_name"):
                st.caption(f"📍 Place: {d['place_name'][:120]}")
            # Satellite evidence - optional, additive (Phase 10)
            sat = d.get("satellite_evidence")
            if sat and sat.get("available"):
                st.markdown("#### 🛰️ Satellite Evidence")
                st.caption(f"Model: {sat.get('source')} | Landslide signal {sat.get('landslide_probability',0)*100:.0f}% | Confidence {sat.get('confidence',0)*100:.0f}%")
                sig = sat.get("signals", {})
                if sig:
                    cols = st.columns(4)
                    cols[0].metric("Wetness", f"{sig.get('wetness',0):.2f}")
                    cols[1].metric("Veg stress", f"{sig.get('vegetation_stress',0):.2f}")
                    cols[2].metric("Bare soil", f"{sig.get('bare_soil',0):.2f}")
                    cols[3].metric("Steep", f"{sig.get('steep_terrain',0):.2f}")
            elif sat and not sat.get("available"):
                st.caption("🛰️ Satellite Evidence: Currently unavailable — using environmental model")
            return d
    except Exception:
        pass
    # Fallback to old predictions if assess fails
    try:
        r = httpx.post(f"{api_base}{api_prefix}/predictions", json={"latitude": lat, "longitude": lon, "save": False}, timeout=12)
        if r.status_code == 200:
            d = r.json()
            score = d["risk_score"]
            level = d["risk_level"]
            color = {"LOW": "#28a745", "MODERATE": "#ffc107", "HIGH": "#fd7e14", "CRITICAL": "#dc3545"}.get(level, "#6c757d")
            st.markdown(
                f'<div style="background:#ffffff;padding:12px;border-radius:8px;border:1px solid #e0e0e0;border-left:5px solid {color}">'
                f'<b style="color:#212529">Live Weather-linked Risk at {lat:.4f}, {lon:.4f}</b><br>'
                f'<span style="color:#212529">Score </span><span style="color:{color};font-size:1.4rem">{score}/100</span> <span style="color:#212529">— <b>{level}</b></span><br>'
                f'<span style="font-size:0.85rem;color:#424242">Source: {"Real live APIs (Open-Meteo)" if not d.get("is_synthetic") else "Demo (synthetic)"} • Model {d.get("model_version","")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            notation = {
                "LOW": "✅ Safe. Normal activities. Stay informed.",
                "MODERATE": "⚠️ Be alert. Avoid steep slopes after rain.",
                "HIGH": "🟠 High risk. Avoid travel on hills, keep emergency kit ready.",
                "CRITICAL": "🔴 CRITICAL! Stay away from slopes, follow official alerts, evacuate if told.",
            }
            st.info(notation.get(level, ""))
            try:
                gr = httpx.get(f"{api_base}{api_prefix}/geocode/reverse", params={"latitude": lat, "longitude": lon}, timeout=8)
                if gr.status_code == 200 and gr.json().get("display_name"):
                    st.caption(f"📍 Place: {gr.json()['display_name'][:120]}")
            except Exception:
                pass
            return d
    except Exception as e:
        st.warning(f"Weather tracking failed: {e}")
    return None


def common_people_tags():
    st.markdown("#### 👨‍👩‍👧‍👦 For Common People — Simple Guide")
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        '<div style="background:#e8f5e9;padding:10px;border-radius:8px;text-align:center;border:1px solid #c8e6c9">'
        '<b style="color:#1b5e20">🌾 Farmers</b><br><span style="font-size:0.85rem;color:#2e7d32">Check before going to fields on slopes. If MODERATE+ after heavy rain, postpone.</span></div>',
        unsafe_allow_html=True,
    )
    c2.markdown(
        '<div style="background:#fff3e0;padding:10px;border-radius:8px;text-align:center;border:1px solid #ffe0b2">'
        '<b style="color:#e65100">🚗 Travelers</b><br><span style="font-size:0.85rem;color:#ef6c00">Check route risk before hill travel. HIGH/CRITICAL = take alternate road.</span></div>',
        unsafe_allow_html=True,
    )
    c3.markdown(
        '<div style="background:#e3f2fd;padding:10px;border-radius:8px;text-align:center;border:1px solid #bbdefb">'
        '<b style="color:#0d47a1">🏠 Families</b><br><span style="font-size:0.85rem;color:#1565c0">Keep phone charged, keep 3-day kit, know nearest safe shelter.</span></div>',
        unsafe_allow_html=True,
    )


def risk_legend():
    st.markdown("#### 🏷️ Risk Tags — What it means")
    st.markdown(
        """
        <div style="display:flex;gap:8px;flex-wrap:wrap">
        <span style="background:#28a745;color:white;padding:4px 8px;border-radius:12px;font-size:0.8rem">LOW 0-30 ✅ Safe</span>
        <span style="background:#ffc107;color:#333;padding:4px 8px;border-radius:12px;font-size:0.8rem">MODERATE 30-60 ⚠️ Caution</span>
        <span style="background:#fd7e14;color:white;padding:4px 8px;border-radius:12px;font-size:0.8rem">HIGH 60-80 🟠 Avoid slopes</span>
        <span style="background:#dc3545;color:white;padding:4px 8px;border-radius:12px;font-size:0.8rem">CRITICAL 80-100 🔴 Evacuate if advised</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("ℹ️ Notation — How to read"):
        st.markdown(
            "- **Score 0-100**: AI risk from rain + slope + soil + history\n"
            "- **LOW/MODERATE**: normal, just stay updated\n"
            "- **HIGH/CRITICAL**: government alert will also be sent (SMS/log). Follow official instructions.\n"
            "- **Is Synthetic?** Demo data vs Real live APIs (Open-Meteo, Open-Elevation)"
        )
