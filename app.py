"""ITMC InvestAI — entry point (optional Google login + Univest-style sidebar)."""
import streamlit as st

from config import APP_ICON, APP_NAME, VERSION
from database.db import init_db
from utils import theme
from utils.logger import get_logger

log = get_logger("app")

st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

theme.inject()

try:
    init_db()
except Exception as e:
    st.error(f"Database initialisation failed: {e}")


# ---- Optional Google login (activates when .streamlit/secrets.toml has [auth]) ----
def _auth_configured() -> bool:
    try:
        return "auth" in st.secrets
    except Exception:
        return False


if _auth_configured():
    if not st.user.is_logged_in:
        st.markdown(
            f"""
            <div style="max-width:520px;margin:8vh auto;text-align:center;">
              <div class="aurora-card aurora-glow" style="padding:44px 36px;">
                <div style="font-size:2.6rem;">📈</div>
                <p class="greeting" style="font-size:2.2rem;">{APP_NAME}</p>
                <p style="color:var(--t2);margin-top:6px;">
                  AI-assisted Indian market research — real data, honest analysis.<br>
                  Dashboard · Trade ideas · Screener · Portfolio · AI Copilot
                </p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _, mid, _ = st.columns([1, 1, 1])
        with mid:
            if st.button("🔐 Sign in with Google", use_container_width=True):
                st.login()
        st.stop()
else:
    log.info("Auth not configured — running without login (see secrets.toml.example).")

pages = st.navigation([
    st.Page("pages/dashboard.py", title="Home", icon="🏠", default=True),
    st.Page("pages/market_explorer.py", title="Market Explorer", icon="🔍"),
    st.Page("pages/trade_ideas.py", title="Trade Ideas", icon="💡"),
    st.Page("pages/screener.py", title="Screener", icon="🔎"),
    st.Page("pages/watchlist.py", title="Watchlist", icon="⭐"),
    st.Page("pages/technical_analysis.py", title="Technical Analysis", icon="📐"),
    st.Page("pages/portfolio.py", title="Portfolio", icon="💼"),
    st.Page("pages/ai_copilot.py", title="AI Copilot", icon="🤖"),
    st.Page("pages/settings.py", title="Settings", icon="⚙️"),
])

with st.sidebar:
    st.markdown(f"### {APP_ICON} {APP_NAME}")

    # Account chip (when logged in via Google)
    if _auth_configured() and st.user.is_logged_in:
        st.caption(f"👤 {st.user.name or st.user.email}")
        if st.button("Log out", use_container_width=True):
            st.logout()

    # Global stock search — jumps to Market Explorer
    def _go_search():
        q = st.session_state.get("global_search", "").strip()
        if q:
            st.session_state["explorer_prefill"] = q
            st.session_state["global_search"] = ""   # allowed inside callback
            st.session_state["_jump_explorer"] = True

    st.text_input("🔍 Search a stock", placeholder="TCS, Infosys, HDFC Bank…",
                  key="global_search", on_change=_go_search)
    if st.session_state.pop("_jump_explorer", False):
        st.switch_page("pages/market_explorer.py")

    # Watchlist snapshot
    try:
        from database import db as _db
        wl = _db.get_watchlist()[:5]
        if wl:
            st.caption("⭐ Watchlist")
            from services import market_data as _md
            for s in wl:
                _q = _md.get_quote(s)
                base = s.replace(".NS", "")
                if _q and _q["change_pct"] is not None:
                    color = "var(--up)" if _q["change_pct"] >= 0 else "var(--down)"
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;font-size:0.85rem;">'
                        f'<span style="color:var(--t1);">{base}</span>'
                        f'<span style="color:{color};">{_q["change_pct"]:+.2f}%</span></div>',
                        unsafe_allow_html=True)
                else:
                    st.markdown(f'<span style="font-size:0.85rem;color:var(--t2);">{base} —</span>',
                                unsafe_allow_html=True)
    except Exception as e:
        log.warning("sidebar watchlist failed: %s", e)

    st.divider()
    st.caption(f"v{VERSION} · NSE/BSE")

pages.run()
