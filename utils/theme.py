"""Aurora design system — light & dark themes via CSS variables.

The active theme is stored in SQLite ("theme" setting, default "light").
Components reference var(--t1), var(--t2), var(--card-bg) etc., so both
themes share one component stylesheet.
"""
import streamlit as st

from database import db

# Accent palette (shared)
PRIMARY = "#4F8CFF"
SECONDARY = "#7C5CFF"
AI_GLOW = "#00B8D9"
SUCCESS = "#16A34A"
DANGER = "#E11D48"
WARNING = "#D97706"

_LIGHT_VARS = """
:root {
  --t1: #0F172A;            /* primary text */
  --t2: #5B6472;            /* secondary text */
  --card-bg: rgba(255,255,255,0.78);
  --card-border: rgba(15,23,42,0.08);
  --card-shadow: 0 8px 28px rgba(15,23,42,0.08);
  --glow-shadow: 0 0 28px rgba(79,140,255,0.14), 0 8px 28px rgba(15,23,42,0.08);
  --input-bg: rgba(255,255,255,0.9);
  --ring-inner: #FFFFFF;
  --up: #16A34A;
  --down: #E11D48;
  --neut: #D97706;
  --glow: #0891B2;
}
.stApp {
  background:
    radial-gradient(900px 500px at 85% -10%, rgba(124,92,255,0.10), transparent 60%),
    radial-gradient(800px 450px at -10% 15%, rgba(79,140,255,0.10), transparent 60%),
    radial-gradient(700px 500px at 50% 110%, rgba(8,145,178,0.06), transparent 60%),
    #F6F8FC;
}
[data-testid="stSidebar"] {
  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(18px);
  border-right: 1px solid rgba(15,23,42,0.08);
}
"""

_DARK_VARS = """
:root {
  --t1: #FFFFFF;
  --t2: #98A2B3;
  --card-bg: rgba(22,33,51,0.55);
  --card-border: rgba(255,255,255,0.08);
  --card-shadow: 0 8px 32px rgba(0,0,0,0.35);
  --glow-shadow: 0 0 32px rgba(0,229,255,0.12), 0 8px 32px rgba(0,0,0,0.35);
  --input-bg: rgba(22,33,51,0.6);
  --ring-inner: #101826;
  --up: #1DD75B;
  --down: #FF5C73;
  --neut: #FFB547;
  --glow: #00E5FF;
}
.stApp {
  background:
    radial-gradient(900px 500px at 85% -10%, rgba(124,92,255,0.16), transparent 60%),
    radial-gradient(800px 450px at -10% 15%, rgba(79,140,255,0.14), transparent 60%),
    radial-gradient(700px 500px at 50% 110%, rgba(0,229,255,0.07), transparent 60%),
    #070B14;
}
[data-testid="stSidebar"] {
  background: rgba(16,24,38,0.75);
  backdrop-filter: blur(18px);
  border-right: 1px solid rgba(255,255,255,0.08);
}
"""

_COMPONENTS = """
html, body, .stApp, [data-testid="stAppViewContainer"] { color: var(--t1); }
h1, h2, h3 { color: var(--t1) !important; letter-spacing: -0.02em; }
p, label, .stCaption, [data-testid="stCaptionContainer"] { color: var(--t2); }
hr { border-color: var(--card-border); }
[data-testid="stSidebarNav"] a { border-radius: 14px; color: var(--t1); }
[data-testid="stSidebarNav"] a:hover { background: rgba(79,140,255,0.12); }
[data-testid="stSidebar"] * { color: var(--t1); }
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small { color: var(--t2); }

[data-testid="stMetric"] {
  background: var(--card-bg);
  backdrop-filter: blur(14px);
  border: 1px solid var(--card-border);
  border-radius: 24px;
  padding: 16px 18px;
  box-shadow: var(--card-shadow);
  transition: transform .2s ease, box-shadow .2s ease;
}
[data-testid="stMetric"]:hover { transform: translateY(-2px); box-shadow: var(--glow-shadow); }
[data-testid="stMetricLabel"] { color: var(--t2) !important; }
[data-testid="stMetricValue"] { color: var(--t1) !important; }

.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  background: linear-gradient(135deg, #4F8CFF 0%, #7C5CFF 100%);
  color: #fff !important; border: none; border-radius: 999px;
  padding: 0.5rem 1.3rem; font-weight: 600;
  box-shadow: 0 4px 18px rgba(79,140,255,0.35);
  transition: transform .15s ease, box-shadow .15s ease;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 24px rgba(124,92,255,0.45); }

[data-baseweb="input"], [data-baseweb="select"] > div, .stTextInput input {
  background: var(--input-bg) !important;
  border-radius: 14px !important;
  border-color: var(--card-border) !important;
  color: var(--t1) !important;
}
[data-testid="stExpander"] {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 20px;
  overflow: hidden;
}
[data-testid="stDataFrame"] {
  border: 1px solid var(--card-border);
  border-radius: 18px;
  overflow: hidden;
}

.aurora-card {
  background: var(--card-bg);
  backdrop-filter: blur(14px);
  border: 1px solid var(--card-border);
  border-radius: 24px;
  padding: 20px 22px;
  box-shadow: var(--card-shadow);
  margin-bottom: 12px;
  color: var(--t1);
}
.aurora-glow { box-shadow: var(--glow-shadow); }

.greeting {
  font-size: 2rem; font-weight: 700; margin-bottom: 0;
  background: linear-gradient(90deg, var(--t1) 30%, #4F8CFF 70%, var(--glow) 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.greeting-sub { color: var(--t2); margin-top: 2px; }

.pulse-label { font-size: 1.6rem; font-weight: 700; }
.pulse-bull { color: var(--up); }
.pulse-bear { color: var(--down); }
.pulse-neut { color: var(--neut); }
.pulse-dot {
  display: inline-block; width: 10px; height: 10px; border-radius: 50%;
  margin-right: 8px; animation: pulse 1.8s infinite;
}
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(79,140,255,0.5); }
  70% { box-shadow: 0 0 0 10px rgba(79,140,255,0); }
  100% { box-shadow: 0 0 0 0 rgba(79,140,255,0); }
}

.sector-grid { display: flex; flex-wrap: wrap; gap: 10px; }
.sector-tile {
  flex: 1 1 130px; border-radius: 18px; padding: 14px 16px;
  border: 1px solid var(--card-border);
  backdrop-filter: blur(10px);
  transition: transform .15s ease;
}
.sector-tile:hover { transform: translateY(-2px); }
.sector-name { color: var(--t1); font-weight: 600; font-size: 0.9rem; }
.sector-chg { font-size: 1.05rem; font-weight: 700; margin-top: 2px; }

.standout { text-align: center; position: relative; }
.ss-sym { color: var(--t1); font-weight: 700; font-size: 1.05rem; }
.ss-ring {
  width: 74px; height: 74px; border-radius: 50%;
  margin: 12px auto; display: flex; align-items: center; justify-content: center;
  background: conic-gradient(var(--glow) calc(var(--p) * 1%), var(--card-border) 0);
}
.ss-ring > div {
  width: 58px; height: 58px; border-radius: 50%;
  background: var(--ring-inner); display: flex; align-items: center; justify-content: center;
  color: var(--t1); font-weight: 700; font-size: 1.1rem;
}
.ss-tag { display: inline-block; border-radius: 999px; padding: 3px 12px;
          font-size: 0.78rem; font-weight: 600; }
.ss-tag.bull { background: rgba(22,163,74,0.14); color: var(--up); }
.ss-tag.bear { background: rgba(225,29,72,0.14); color: var(--down); }
.ss-tag.neut { background: rgba(217,119,6,0.14); color: var(--neut); }
.ss-sub { color: var(--t2); font-size: 0.78rem; margin-top: 8px; }

.chip {
  display: inline-block; border-radius: 999px; padding: 4px 14px; margin: 3px;
  background: rgba(79,140,255,0.12); color: var(--t1);
  border: 1px solid var(--card-border); font-size: 0.82rem;
}
"""


def current_theme() -> str:
    try:
        t = db.get_setting("theme", "light") or "light"
    except Exception:
        t = "light"
    return t if t in ("light", "dark") else "light"


def is_light() -> bool:
    return current_theme() == "light"


def inject() -> None:
    theme_vars = _LIGHT_VARS if is_light() else _DARK_VARS
    st.markdown(f"<style>{theme_vars}{_COMPONENTS}</style>", unsafe_allow_html=True)
