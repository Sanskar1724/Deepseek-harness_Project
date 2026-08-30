"""Public Awareness & Education - user-friendly guide for citizens."""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Awareness - NER Landslide Safety", page_icon="A", layout="wide")

st.markdown("# Public Awareness & Safety Guide")
st.write("**Learn how to stay safe during landslides in the North Eastern Region**")

# Language selector
lang = st.selectbox("Language / भाषा / ভাষা", ["English", "Hindi", "Assamese"])

st.markdown("---")

# Hero info
if lang == "English":
    st.markdown("""
    ## What is a Landslide?
    A landslide is the movement of rock, debris, or earth down a slope. In NER, 
    they are commonly triggered by heavy rainfall, earthquakes, or human activities 
    like hill cutting. They can happen suddenly and cause severe damage.
    """)
    st.warning("**If you are in immediate danger, call 1077 (NDRF Helpline) or your local emergency number**")
elif lang == "Hindi":
    st.markdown("""
    ## भूस्खलन क्या है?
    भूस्खलन चट्टान, मलबे या मिट्टी का ढलान से नीचे की ओर गिरना है। 
    उत्तर-पूर्वी क्षेत्र में, ये आमतौर पर भारी बारिश, भूकंप या पहाड़ी कटाई से होते हैं।
    """)
    st.warning("**यदि आप तत्काल खतरे में हैं, तो 1077 (NDRF हेल्पलाइन) पर कॉल करें**")
else:
    st.markdown("""
    ## ভূধান কি?
    ভূধান হৈছে শিল, আৱৰ্জন বা মাটি পাহাৰৰ ঢাল বেয়ে তললৈ যোৱা। 
    উত্তৰ-পূব অঞ্চলত, সাধাৰণতে ধাৰাসাৰ বৰষুণ, ভূমিকম্প বা পাহাৰ কটাৰ ফলত এই ঘটনা ঘটে।
    """)
    st.warning("**যদি আপুনি ততালিকে বিপদত আছে, 1077 (NDRF হেল্পলাইন) ফোন কৰক**")

st.markdown("---")

# Warning signs
st.markdown("## Warning Signs (Before a Landslide)")
c1, c2 = st.columns(2)
with c1:
    st.markdown("### Visual Signs")
    st.write("- New cracks in walls, floors, or roads")
    st.write("- Trees, fences, walls tilting")
    st.write("- Water seeping from hillsides")
    st.write("- Unusual sounds: rumbling, cracking")
    st.write("- Soil moving away from foundations")
with c2:
    st.markdown("### Environmental Signs")
    st.write("- Sudden change in stream flow")
    st.write("- Muddy or discolored water")
    st.write("- Sticking doors and windows")
    st.write("- Cracks appearing in ground")
    st.write("- Bulging ground at base of slopes")

st.markdown("---")

# What to do
st.markdown("## What to Do During a Landslide")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### If Indoors")
    st.write("- Stay inside, take cover under sturdy furniture")
    st.write("- Stay away from windows")
    st.write("- Listen to emergency broadcasts")
    st.write("- Keep emergency kit ready")
with c2:
    st.markdown("### If Outdoors")
    st.write("- Move to high ground, away from slope")
    st.write("- Stay away from rivers/streams (debris flow)")
    st.write("- Watch for falling rocks/debris")
    st.write("- Do not cross bridges if water is high")
with c3:
    st.markdown("### If Driving")
    st.write("- Pull over to safe area")
    st.write("- Do not try to outrun landslide")
    st.write("- Turn off engine if stuck")
    st.write("- Stay inside vehicle or evacuate uphill")

st.markdown("---")

# Emergency contacts
st.markdown("## Emergency Contacts (NER)")
contacts = [
    {"Service": "NDRF Helpline", "Number": "1077", "Available": "24/7"},
    {"Service": "State Emergency (Assam)", "Number": "1070", "Available": "24/7"},
    {"Service": "Fire Service", "Number": "101", "Available": "24/7"},
    {"Service": "Ambulance", "Number": "108", "Available": "24/7"},
    {"Service": "Police", "Number": "100", "Available": "24/7"},
    {"Service": "Disaster Mgmt (India)", "Number": "1078", "Available": "24/7"},
]
st.dataframe(contacts, use_container_width=True, hide_index=True)

st.markdown("---")

# Before/during/after
st.markdown("## Before, During, After - Safety Checklist")
t1, t2, t3 = st.tabs(["BEFORE", "DURING", "AFTER"])

with t1:
    st.markdown("### Prepare Your Family & Home")
    st.write("- Know your area landslide risk (check this app)")
    st.write("- Plan evacuation routes to high ground")
    st.write("- Pack emergency kit: water, food, flashlight, first aid")
    st.write("- Keep important documents in waterproof bag")
    st.write("- Maintain house drainage systems")
    st.write("- Plant deep-rooted trees on slopes if possible")
    st.write("- Subscribe to local emergency alerts")
    st.write("- Identify safe zones: high ground, sturdy buildings")

with t2:
    st.markdown("### During the Event")
    st.write("- Stay calm, move to safety immediately")
    st.write("- Do NOT cross rivers or streams")
    st.write("- Listen for emergency instructions")
    st.write("- Help neighbors, especially elderly/disabled")
    st.write("- Stay away from landslide area (rescue may be needed)")
    st.write("- Keep phone charged for emergency calls")
    st.write("- Do NOT go back for belongings")

with t3:
    st.markdown("### After the Landslide")
    st.write("- Stay away from affected areas")
    st.write("- Check for injured people, call for help")
    st.write("- Watch for secondary landslides (common!)")
    st.write("- Avoid driving through debris")
    st.write("- Report damage to local authorities")
    st.write("- Document damage with photos for insurance")
    st.write("- Help community recovery efforts")
    st.write("- **Use this app to submit geo-tagged reports of damage")

st.markdown("---")
st.markdown("## Submit a Report")
st.info("**See something? Say something!** Use the **Report** page to submit geo-tagged reports of cracks, road blockages, slope movement, or any landslide observations. Your reports help authorities respond faster and help AI models learn.")

if st.button("Go to Report Page", use_container_width=True, type="primary"):
    st.switch_page("pages/3_Reports.py")

st.markdown("---")
st.markdown("## How This AI System Helps You")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### Before")
    st.write("AI predicts risk 24-48 hours ahead based on weather + terrain. You get advance warning.")
with c2:
    st.markdown("### During")
    st.write("Real-time alerts tell you which roads are blocked, which villages are at risk. Helps you make real-time decisions.")
with c3:
    st.markdown("### After")
    st.write("Your geo-tagged reports help authorities and train the AI to be smarter for next time.")
