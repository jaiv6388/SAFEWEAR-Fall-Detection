import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import datetime

# Plotly defaults: white charts with dark, readable labels
import plotly.io as pio
pio.templates["safewear_light"] = pio.templates["plotly_white"]
pio.templates["safewear_light"].layout.update(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(color="#111827", size=14),
    title=dict(font=dict(color="#111827")),
    xaxis=dict(
        color="#111827",
        title_font=dict(color="#111827"),
        tickfont=dict(color="#111827"),
        gridcolor="#E5E7EB",
        zerolinecolor="#CBD5E1"
    ),
    yaxis=dict(
        color="#111827",
        title_font=dict(color="#111827"),
        tickfont=dict(color="#111827"),
        gridcolor="#E5E7EB",
        zerolinecolor="#CBD5E1"
    ),
    legend=dict(font=dict(color="#111827"))
)
pio.templates.default = "safewear_light"


# ============================================================
# SAFEWEAR — FINAL FIREBASE INTEGRATION
# ============================================================

st.set_page_config(page_title="SAFEWEAR", page_icon="🛡️", layout="wide")

# Force a consistent LIGHT UI on local + Streamlit Community Cloud.
st.markdown("""
<style>
:root {
  color-scheme: light !important;
}
html, body, [data-testid="stAppViewContainer"], .stApp,
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {
  background: #ffffff !important;
  color: #171717 !important;
}
[data-testid="stHeader"] {
  background: rgba(255,255,255,0.96) !important;
}
[data-testid="stSidebar"] {
  background: #ffffff !important;
}

/* Text and labels */
.stMarkdown, .stMarkdown p, .stMarkdown span,
label, [data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *,
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
  color: #171717 !important;
}

/* Text inputs / text areas / number inputs */
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div,
.stTextInput input, .stNumberInput input, .stTextArea textarea {
  background-color: #ffffff !important;
  color: #171717 !important;
  -webkit-text-fill-color: #171717 !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
  color: #777777 !important;
  opacity: 1 !important;
}

/* Select boxes */
div[data-baseweb="select"] > div {
  background-color: #ffffff !important;
  color: #171717 !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="select"] input {
  color: #171717 !important;
  -webkit-text-fill-color: #171717 !important;
}

/* Number input +/- controls */
.stNumberInput button {
  background-color: #f5f5f5 !important;
  color: #171717 !important;
}

/* Popovers / dropdown menus */
div[role="listbox"], ul[role="listbox"],
[data-baseweb="popover"], [data-baseweb="menu"] {
  background-color: #ffffff !important;
  color: #171717 !important;
}
div[role="option"], li[role="option"] {
  background-color: #ffffff !important;
  color: #171717 !important;
}

/* Cards / bordered containers */
[data-testid="stVerticalBlockBorderWrapper"] {
  background-color: #ffffff !important;
}

/* Force browser-native form controls to light mode */
input, textarea, select, button {
  color-scheme: light !important;
}
</style>
""", unsafe_allow_html=True)


FIREBASE_URL = "https://safewear-e1b21-default-rtdb.firebaseio.com/sensor_readings.json"
LATITUDE = 28.632468
LONGITUDE = 77.445071
MAPS_LINK = f"https://www.google.com/maps/search/?api=1&query={LATITUDE},{LONGITUDE}"
NTFY_TOPIC = "Safewear-JV-2026"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

def send_ntfy_sos(name):
    """Send the manual SAFEWEAR SOS to the subscribed ntfy phone topic."""
    message = (
        f"Emergency SOS triggered for {name}. Assistance required. "
        f"Location: {MAPS_LINK}"
    )
    r = requests.post(
        NTFY_URL,
        data=message.encode("utf-8"),
        headers={
            "Title": "SAFEWEAR EMERGENCY ALERT",
            "Priority": "urgent",
            "Tags": "rotating_light,warning",
            "Click": MAPS_LINK,
        },
        timeout=8,
    )
    r.raise_for_status()

st.markdown("""
<style>
.stApp{background:#f7f7fc;color:#1f2937}
.block-container{max-width:1250px;padding-top:2rem;padding-bottom:4rem}
h1,h2,h3{color:#28175c!important}
div[data-testid="stMetric"]{background:white;border:1px solid #e5e7eb;border-radius:16px;padding:18px}
div[data-testid="stVerticalBlockBorderWrapper"]{background:white;border-radius:18px}
.stButton>button{background:#6d28d9!important;color:white!important;border:none!important;
border-radius:14px!important;min-height:48px!important;font-weight:700!important}
.stButton>button *{color:white!important}
</style>
""", unsafe_allow_html=True)

defaults = {
    "profile": None,
    "setup_complete": False,
    "user_data": {},
    "sos": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def reset_app():
    st.session_state.profile = None
    st.session_state.setup_complete = False
    st.session_state.user_data = {}
    st.session_state.sos = False

def hero(title, subtitle):
    st.markdown(
        f"""<div style="background:linear-gradient(120deg,#4c1d95,#6d28d9,#8b5cf6);
        padding:32px 36px;border-radius:24px;margin-bottom:26px;
        box-shadow:0 12px 30px rgba(76,29,149,.14)">
        <div style="font-size:40px;font-weight:800;color:white">{title}</div>
        <div style="font-size:17px;color:#ede9fe;margin-top:7px">{subtitle}</div></div>""",
        unsafe_allow_html=True,
    )

def section(title):
    st.markdown(f"## {title}")

def safe(data, key, fallback="Not provided"):
    value = data.get(key)
    return fallback if value is None or (isinstance(value, str) and not value.strip()) else value

def style_graph(fig, y_title):
    fig.update_layout(
        template="plotly_white", height=330, paper_bgcolor="#fff", plot_bgcolor="#fff",
        margin=dict(l=40, r=30, t=30, b=40), hovermode="x unified",
        xaxis=dict(title="Sample", gridcolor="#eef2f7"),
        yaxis=dict(title=y_title, gridcolor="#eef2f7"),
    )

@st.cache_data(ttl=1)
def fetch_firebase():
    try:
        r = requests.get(
            FIREBASE_URL,
            params={"orderBy": '"$key"', "limitToLast": 300},
            timeout=15
        )
        r.raise_for_status()
        raw = r.json() or {}
        if not isinstance(raw, dict):
            return pd.DataFrame(), {}, "Unexpected Firebase response"

        rows = []
        for fid, item in raw.items():
            # Keep actual SisFall records; ignore older SW001/demo schema.
            if isinstance(item, dict) and "sample" in item and "acc1_x" in item:
                x = dict(item)
                x["firebase_id"] = fid
                rows.append(x)

        if not rows:
            return pd.DataFrame(), {}, None

        # Firebase push IDs are chronological.
        rows.sort(key=lambda x: x["firebase_id"])
        latest = rows[-1]
        frame = pd.DataFrame(rows[-300:])

        numeric = ["sample","acc1_x","acc1_y","acc1_z","acc2_x","acc2_y","acc2_z",
                   "gyro_x","gyro_y","gyro_z","acc_magnitude_g","max_magnitude_g"]
        for c in numeric:
            if c in frame.columns:
                frame[c] = pd.to_numeric(frame[c], errors="coerce")
        return frame, latest, None
    except Exception as e:
        return pd.DataFrame(), {}, str(e)

# ============================================================
# ELDER CARE ONLY
# ============================================================
st.session_state.profile = "Elderly"

# ============================================================
# ELDERLY PROFILE SETUP
# ============================================================
if not st.session_state.setup_complete:
    hero("⚙️ SAFEWEAR Setup", "Elder Care Profile Configuration")
    section("👴 Wearer Profile")
    st.write("Enter the elderly wearer's personal, medical and emergency information.")
    l, r = st.columns(2, gap="large")
    with l:
        name = st.text_input("Full Name *")
        age = st.number_input("Age *", 1, 120, value=None)
        gender = st.selectbox("Gender", ["Select","Male","Female","Other"])
        height = st.number_input("Height (cm) *", 50.0, 250.0, value=None)
        weight = st.number_input("Weight (kg) *", 10.0, 250.0, value=None)
    with r:
        blood = st.selectbox("Blood Group", ["Unknown","A+","A-","B+","B-","O+","O-","AB+","AB-"])
        emergency = st.text_input("Emergency Contact *")
        doctor = st.text_input("Family Doctor")
        hospital = st.text_input("Preferred Hospital")
        address = st.text_area("Residence Address")
    medical = st.text_area("Important Medical Notes")
    if st.button("Save Profile & Open Dashboard", use_container_width=True):
        if not name.strip() or age is None or height is None or weight is None or not emergency.strip():
            st.error("Please fill all required (*) fields.")
        else:
            st.session_state.user_data = {
                "name":name.strip(),"age":int(age),"gender":gender,"height":float(height),
                "weight":float(weight),"blood_group":blood,"emergency_contact":emergency.strip(),
                "family_doctor":doctor.strip(),"hospital":hospital.strip(),"address":address.strip(),
                "medical_notes":medical.strip()
            }
            st.session_state.setup_complete=True
            st.rerun()
    st.stop()

# Final Cloud UI overrides: consistent light theme, readable text, equal controls.
st.markdown("""
<style>
/* Global readable text */
.stApp, .stApp p, .stApp span, .stApp label,
.stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] * {
    color:#171717 !important;
}

/* Keep hero/banner text white */
.hero, .hero *, .hero-card, .hero-card * {
    color:white !important;
}

/* All form controls: same white appearance and height */
.stTextInput div[data-baseweb="input"],
.stNumberInput div[data-baseweb="input"],
.stSelectbox div[data-baseweb="select"] > div {
    background:#ffffff !important;
    border-color:#9ca3af !important;
    min-height:42px !important;
    height:42px !important;
    border-radius:8px !important;
}
.stTextInput input, .stNumberInput input,
.stSelectbox div[data-baseweb="select"] span {
    color:#171717 !important;
    -webkit-text-fill-color:#171717 !important;
    background:#ffffff !important;
}
.stSelectbox svg { fill:#171717 !important; }

/* Number +/- area */
.stNumberInput button {
    height:40px !important;
    background:#f8fafc !important;
    color:#171717 !important;
}

/* Text areas */
.stTextArea textarea {
    background:#ffffff !important;
    color:#171717 !important;
    -webkit-text-fill-color:#171717 !important;
    border-color:#9ca3af !important;
    border-radius:8px !important;
}

/* Dropdown popup */
div[data-baseweb="popover"], div[role="listbox"],
div[role="option"] {
    background:#ffffff !important;
    color:#171717 !important;
}

/* Metrics: remove browser-selected/dark-looking value backgrounds */
[data-testid="stMetric"] {
    background:#ffffff !important;
    color:#171717 !important;
}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
    color:#171717 !important;
    background:transparent !important;
}

/* Streamlit dataframe/table: light cells */
[data-testid="stDataFrame"], [data-testid="stTable"] {
    background:#ffffff !important;
    color:#171717 !important;
}
[data-testid="stTable"] table,
[data-testid="stTable"] thead,
[data-testid="stTable"] tbody,
[data-testid="stTable"] tr,
[data-testid="stTable"] th,
[data-testid="stTable"] td {
    background:#ffffff !important;
    color:#171717 !important;
    border-color:#e5e7eb !important;
}

/* Plotly charts */
.js-plotly-plot, .plot-container, .svg-container {
    background:#ffffff !important;
}

/* Prevent dark color-scheme inheritance */
html, body, .stApp, input, textarea, select {
    color-scheme:light !important;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# LIVE DASHBOARD
# ============================================================
df, live, firebase_error = fetch_firebase()
u = st.session_state.user_data
profile = st.session_state.profile
display_name = u.get("name") or u.get("worker_name") or "SAFEWEAR User"
fall = bool(live.get("fall", False))

hero("🛡️ SAFEWEAR", f"{display_name} • Elder Care Safety Dashboard")

status, edit = st.columns([4,1])
with status:
    if st.session_state.sos:
        st.error("🚨 SOS ACTIVE — Emergency assistance required.")
    elif fall:
        st.error("🚨 FALL DETECTED — Emergency assistance may be required.")
    elif firebase_error:
        st.warning("⚠️ LIVE DATA OFFLINE — Firebase connection unavailable.")
    elif live:
        st.success("✓ SYSTEM SAFE — No fall detected.")
    else:
        st.warning("⚠️ WAITING FOR SENSOR DATA")
with edit:
    if st.button("⚙️ Edit Profile", use_container_width=True):
        st.session_state.setup_complete = False
        st.rerun()

section("📡 Live Device Status")
c1,c2,c3,c4 = st.columns(4)
c1.metric("Connection", "Online" if live and not firebase_error else "Offline")
c2.metric("Latest Sample", live.get("sample","—"))
mag = live.get("acc_magnitude_g")
c3.metric("Acceleration", f"{float(mag):.3f} g" if mag is not None else "—")
c4.metric("Current Activity", "FALL DETECTED" if fall else ("Normal" if live else "Waiting"))
st.caption("Dashboard refreshed: " + datetime.now().strftime("%I:%M:%S %p"))
if firebase_error:
    st.caption("Firebase error: " + firebase_error)

section("🚨 Emergency Control")
with st.container(border=True):
    if not st.session_state.sos:
        st.warning("Manual emergency alert is inactive.")
        if st.button("🚨 SEND SOS", use_container_width=True):
            try:
                send_ntfy_sos(display_name)
                st.session_state.sos = True
                st.toast("SOS sent to phone successfully.", icon="🚨")
                st.rerun()
            except Exception as e:
                st.error(f"SOS notification could not be sent: {e}")
    else:
        st.error("🚨 Emergency alert is ACTIVE.")
        st.link_button("📍 Open Emergency Location in Google Maps", MAPS_LINK, use_container_width=True)
        if st.button("✓ CANCEL SOS", use_container_width=True):
            st.session_state.sos = False
            st.rerun()

section("👤 Profile & Emergency Information")
l,r = st.columns(2, gap="large")
with l:
    with st.container(border=True):
        st.markdown("### 👴 Wearer Information")
        st.write(f"**Name:** {safe(u,'name')}")
        st.write(f"**Age:** {safe(u,'age')}")
        st.write(f"**Gender:** {safe(u,'gender')}")
        st.write(f"**Blood Group:** {safe(u,'blood_group','Unknown')}")
        st.write(f"**Height:** {u.get('height','—')} cm")
        st.write(f"**Weight:** {u.get('weight','—')} kg")
with r:
    with st.container(border=True):
        st.markdown("### 🚑 Emergency Information")
        st.write(f"**Emergency Contact:** {safe(u,'emergency_contact')}")
        st.write(f"**Family Doctor:** {safe(u,'family_doctor')}")
        st.write(f"**Preferred Hospital:** {safe(u,'hospital')}")
        st.write(f"**Residence:** {safe(u,'address')}")
        st.write(f"**Medical Notes:** {safe(u,'medical_notes','None')}")

section("📍 Current Location")
with st.container(border=True):
    a,b,c = st.columns(3)
    a.metric("Latitude", f"{LATITUDE:.6f}")
    b.metric("Longitude", f"{LONGITUDE:.6f}")
    c.metric("GPS Status", "🟢 Prototype Active")
    st.link_button("📍 Open Location in Google Maps", MAPS_LINK, use_container_width=True)
st.caption("Prototype coordinates; GPS module can replace these values later.")

section("📊 Live Motion Analytics")
if df.empty:
    st.warning("No SisFall readings available in Firebase.")
else:
    g = df.tail(200)
    x = g["sample"]

    st.markdown("### Acceleration Magnitude")
    f1 = go.Figure()
    if "acc_magnitude_g" in g:
        f1.add_trace(go.Scatter(x=x,y=g["acc_magnitude_g"],mode="lines",name="Magnitude"))
    f1.add_hline(y=3.0,line_dash="dash",annotation_text="Fall Threshold (3.0 g)")
    style_graph(f1,"Acceleration (g)")
    st.plotly_chart(f1,use_container_width=True)

    st.markdown("### Accelerometer X / Y / Z")
    f2 = go.Figure()
    for col,name in [("acc1_x","X"),("acc1_y","Y"),("acc1_z","Z")]:
        if col in g:
            f2.add_trace(go.Scatter(x=x,y=g[col],mode="lines",name=name))
    style_graph(f2,"Raw acceleration")
    st.plotly_chart(f2,use_container_width=True)

    st.markdown("### Gyroscope X / Y / Z")
    f3 = go.Figure()
    for col,name in [("gyro_x","X"),("gyro_y","Y"),("gyro_z","Z")]:
        if col in g:
            f3.add_trace(go.Scatter(x=x,y=g[col],mode="lines",name=name))
    style_graph(f3,"Raw angular velocity")
    st.plotly_chart(f3,use_container_width=True)

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Current Magnitude", f"{float(live.get('acc_magnitude_g',0)):.3f} g")
    m2.metric("Maximum Magnitude", f"{float(live.get('max_magnitude_g',0)):.3f} g")
    m3.metric("Sample", live.get("sample","—"))
    m4.metric("Fall", "YES 🚨" if fall else "NO ✓")

section("🕒 Recent Sensor Events")
if not df.empty:
    e = df.tail(20).iloc[::-1]
    events = pd.DataFrame({
        "Sample": e["sample"],
        "Acceleration (g)": e["acc_magnitude_g"].round(3),
        "Event": e["fall"].apply(lambda v:"Fall detected" if bool(v) else "Normal movement"),
        "Status": e["fall"].apply(lambda v:"Emergency" if bool(v) else "Safe"),
    })
    st.dataframe(events,use_container_width=True,hide_index=True)

section("🔧 Device Hardware")
a,b,c,d = st.columns(4)
a.metric("Controller","ESP32")
b.metric("Motion Sensor","MPU6050")
c.metric("GPS Module","Prototype")
d.metric("GSM Module","Ready")

section("⚙️ Dashboard Settings")
a,b = st.columns(2)
with a:
    if st.button("↻ Refresh Live Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with b:
    if st.button("Edit Elder Profile", use_container_width=True):
        st.session_state.setup_complete=False
        st.rerun()

st.divider()
st.markdown("### 🛡️ SAFEWEAR")
st.caption("Elder Care Fall Detection • ESP32 • MPU6050 • MQTT • Node-RED • Firebase")


# Final theme override

st.markdown("""
<style>
/* ===== SAFEWEAR ELDER CARE — NAVY + TEAL THEME ===== */
:root { color-scheme: light !important; }

html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMain"], [data-testid="stMainBlockContainer"] {
    background:#F5F8FA !important;
    color:#172033 !important;
}

/* Hero/header */
.hero, .hero-card {
    background:linear-gradient(120deg,#0B1F33 0%,#123A52 55%,#0F766E 100%) !important;
    border:none !important;
    box-shadow:0 14px 34px rgba(11,31,51,.14) !important;
}
.hero *, .hero-card * { color:#FFFFFF !important; }

/* Headings and normal copy */
.stApp h1,.stApp h2,.stApp h3,.stApp h4 {
    color:#102A43 !important;
}
.stApp p,.stApp label,
[data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] * {
    color:#26384A !important;
}

/* Cards */
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stMetric"] {
    background:#FFFFFF !important;
    border-color:#DCE5EA !important;
    box-shadow:0 4px 14px rgba(16,42,67,.05) !important;
}
[data-testid="stMetricLabel"],[data-testid="stMetricLabel"] *,
[data-testid="stMetricValue"],[data-testid="stMetricValue"] * {
    color:#102A43 !important;
    background:transparent !important;
}

/* Inputs: identical visual treatment */
.stTextInput div[data-baseweb="input"],
.stNumberInput div[data-baseweb="input"],
.stSelectbox div[data-baseweb="select"] > div {
    background:#FFFFFF !important;
    border:1px solid #B8C7D1 !important;
    border-radius:9px !important;
    min-height:44px !important;
    height:44px !important;
    box-shadow:none !important;
}
.stTextInput input,.stNumberInput input,
.stSelectbox div[data-baseweb="select"] span {
    color:#172033 !important;
    -webkit-text-fill-color:#172033 !important;
    background:#FFFFFF !important;
}
.stSelectbox svg { fill:#172033 !important; }
.stNumberInput button {
    background:#EDF4F6 !important;
    color:#102A43 !important;
    height:42px !important;
}
.stTextArea textarea {
    background:#FFFFFF !important;
    color:#172033 !important;
    -webkit-text-fill-color:#172033 !important;
    border:1px solid #B8C7D1 !important;
    border-radius:9px !important;
}

/* Dropdown popup */
div[data-baseweb="popover"],div[role="listbox"],div[role="option"] {
    background:#FFFFFF !important;
    color:#172033 !important;
}

/* Buttons */
.stButton > button {
    background:#0F766E !important;
    color:#FFFFFF !important;
    border:1px solid #0F766E !important;
    border-radius:10px !important;
    font-weight:700 !important;
}
.stButton > button:hover {
    background:#115E59 !important;
    border-color:#115E59 !important;
    color:#FFFFFF !important;
}

/* Table */
[data-testid="stTable"],[data-testid="stDataFrame"] {
    background:#FFFFFF !important;
    color:#172033 !important;
}
[data-testid="stTable"] table,
[data-testid="stTable"] thead,
[data-testid="stTable"] tbody,
[data-testid="stTable"] tr,
[data-testid="stTable"] th,
[data-testid="stTable"] td {
    background:#FFFFFF !important;
    color:#172033 !important;
    border-color:#DCE5EA !important;
}

/* Captions */
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] * {
    color:#61758A !important;
}

/* Keep native controls in light rendering */
input,textarea,select,button { color-scheme:light !important; }
</style>
""", unsafe_allow_html=True)


# High-contrast Elder Care theme — final override

st.markdown("""
<style>
/* ===== SAFEWEAR — HIGH-CONTRAST ELDER CARE THEME ===== */
:root { color-scheme: light !important; }

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background:#F7F8FA !important;
    color:#111827 !important;
}

/* Warm yellow header: dark text for maximum readability */
.hero, .hero-card {
    background:#F4D35E !important;
    border:1px solid #D7B83E !important;
    box-shadow:0 8px 22px rgba(17,24,39,.10) !important;
}
.hero *, .hero-card * {
    color:#111827 !important;
    text-shadow:none !important;
}

/* Headings / body */
.stApp h1,.stApp h2,.stApp h3,.stApp h4,
.stApp p,.stApp label,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] * {
    color:#111827 !important;
}

/* White cards with visible borders */
[data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stMetric"] {
    background:#FFFFFF !important;
    border:1px solid #CBD5E1 !important;
    box-shadow:0 3px 10px rgba(17,24,39,.05) !important;
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] *,
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
    color:#111827 !important;
    background:transparent !important;
}

/* Equal, high-contrast form controls */
.stTextInput div[data-baseweb="input"],
.stNumberInput div[data-baseweb="input"],
.stSelectbox div[data-baseweb="select"] > div {
    background:#FFFFFF !important;
    border:2px solid #94A3B8 !important;
    border-radius:8px !important;
    min-height:46px !important;
    height:46px !important;
    box-shadow:none !important;
}
.stTextInput input,.stNumberInput input,
.stSelectbox div[data-baseweb="select"] span {
    color:#111827 !important;
    -webkit-text-fill-color:#111827 !important;
    background:#FFFFFF !important;
    font-size:16px !important;
}
.stSelectbox svg { fill:#111827 !important; }

.stNumberInput button {
    background:#EEF2F7 !important;
    color:#111827 !important;
    height:44px !important;
    border-color:#CBD5E1 !important;
}

.stTextArea textarea {
    background:#FFFFFF !important;
    color:#111827 !important;
    -webkit-text-fill-color:#111827 !important;
    border:2px solid #94A3B8 !important;
    border-radius:8px !important;
    font-size:16px !important;
}

/* Dropdown menus */
div[data-baseweb="popover"],
div[role="listbox"],
div[role="option"] {
    background:#FFFFFF !important;
    color:#111827 !important;
}

/* Accessible blue action buttons */
.stButton > button {
    background:#2457A6 !important;
    color:#FFFFFF !important;
    border:2px solid #1E4788 !important;
    border-radius:9px !important;
    font-weight:700 !important;
    min-height:46px !important;
}
.stButton > button:hover {
    background:#1E4788 !important;
    color:#FFFFFF !important;
}

/* Light readable tables */
[data-testid="stTable"], [data-testid="stDataFrame"] {
    background:#FFFFFF !important;
    color:#111827 !important;
}
[data-testid="stTable"] table,
[data-testid="stTable"] thead,
[data-testid="stTable"] tbody,
[data-testid="stTable"] tr,
[data-testid="stTable"] th,
[data-testid="stTable"] td {
    background:#FFFFFF !important;
    color:#111827 !important;
    border-color:#CBD5E1 !important;
}

/* Secondary text */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {
    color:#475569 !important;
}

/* Native browser controls */
input,textarea,select,button { color-scheme:light !important; }
</style>
""", unsafe_allow_html=True)



# ===== FINAL DRY-RUN VISUAL FIXES =====
st.markdown("""
<style>
/* Purple SAFEWEAR banner stays purple; all banner text is white */
.hero, .hero-card {
    background: linear-gradient(110deg,#6420C7 0%,#8B4CF6 100%) !important;
    border: none !important;
}
.hero *, .hero-card *,
.hero h1, .hero h2, .hero h3, .hero p,
.hero-card h1, .hero-card h2, .hero-card h3, .hero-card p {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
}

/* Every normal Streamlit button: blue with white readable text */
.stButton > button,
.stButton > button *,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-secondary"] *,
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primary"] * {
    background:#2457A6 !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    border-color:#1E4788 !important;
    font-weight:700 !important;
}
.stButton > button:hover,
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background:#1E4788 !important;
    color:#FFFFFF !important;
}

/* Links styled as buttons (e.g. map/location) */
.stLinkButton a,
.stLinkButton a *,
[data-testid="stLinkButton"] a,
[data-testid="stLinkButton"] a * {
    background:#2457A6 !important;
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
    border-color:#1E4788 !important;
    font-weight:700 !important;
}

/* Plotly graph containers remain white */
.js-plotly-plot, .plot-container, .plotly {
    background:#FFFFFF !important;
}

/* Recent Sensor Events dataframe/table: light surface + dark text */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div,
[data-testid="stDataFrame"] iframe,
[data-testid="stTable"],
[data-testid="stTable"] table,
[data-testid="stTable"] thead,
[data-testid="stTable"] tbody,
[data-testid="stTable"] tr,
[data-testid="stTable"] th,
[data-testid="stTable"] td {
    background:#FFFFFF !important;
    color:#111827 !important;
    -webkit-text-fill-color:#111827 !important;
    border-color:#CBD5E1 !important;
}
[data-testid="stTable"] th {
    background:#EAF0F7 !important;
    color:#111827 !important;
    font-weight:700 !important;
}

/* Keep dashboard setting/action buttons blue, force white labels */
.stButton p, .stButton span {
    color:#FFFFFF !important;
    -webkit-text-fill-color:#FFFFFF !important;
}
</style>
""", unsafe_allow_html=True)
