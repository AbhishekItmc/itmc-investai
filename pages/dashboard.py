"""Home — Univest-style markets overview."""
from datetime import datetime

import streamlit as st

from components.charts import line_chart, mood_gauge, sparkline
from components.ui import data_disclaimer, pulse_card, sector_heatmap, standout_cards
from config import (DEFAULT_INDEX, INDICES, NIFTY50, PERIOD_INTERVALS,
                    SPARK_INDICES_GLOBAL, SPARK_INDICES_IN)
from database import db
from services import analytics
from services import market_data as md

# ---- Greeting -----------------------------------------------------------------
from utils.user import display_name  # noqa: E402

hour = datetime.now().hour
part = "Morning" if hour < 12 else "Afternoon" if hour < 17 else "Evening"
name = display_name()
st.markdown(f'<p class="greeting">👋 Good {part}, {name}</p>', unsafe_allow_html=True)
st.markdown(f'<p class="greeting-sub">{datetime.now():%A, %d %B %Y}</p>', unsafe_allow_html=True)

# ---- Index cards with sparklines + Indian/Global toggle --------------------------
try:
    region = st.segmented_control("Markets", ["Indian", "Global"], default="Indian",
                                  label_visibility="collapsed")
except Exception:
    region = st.radio("Markets", ["Indian", "Global"], horizontal=True,
                      label_visibility="collapsed")
region = region or "Indian"
spark_map = SPARK_INDICES_IN if region == "Indian" else SPARK_INDICES_GLOBAL
sparks = analytics.index_sparks(tuple(spark_map.items()))

if not sparks:
    st.warning("Index data unavailable right now.")
else:
    cols = st.columns(len(sparks))
    for col, (idx_name, d) in zip(cols, sparks.items()):
        with col:
            chg = d["change_pct"]
            color = "var(--up)" if chg >= 0 else "var(--down)"
            st.markdown(
                f'<div style="color:var(--t2);font-size:0.8rem;font-weight:600;">{idx_name}</div>',
                unsafe_allow_html=True)
            st.plotly_chart(sparkline(d["series"]), use_container_width=True,
                            config={"displayModeBar": False, "staticPlot": True},
                            key=f"spark_{region}_{idx_name}")
            st.markdown(
                f'<div style="color:var(--t1);font-weight:700;">{d["last"]:,.2f}</div>'
                f'<div style="color:{color};font-size:0.82rem;font-weight:600;">{chg:+.2f}%</div>',
                unsafe_allow_html=True)

st.divider()

# ---- Market movers panel ----------------------------------------------------------
st.subheader("Market movers")
closes = analytics.batch_closes(tuple(NIFTY50))
movers = md.get_movers(tuple(NIFTY50))
g, l, h = st.columns(3)


def _mover_rows(df, ascending, n=5):
    view = df.sort_values("change_pct", ascending=ascending).head(n)
    for _, r in view.iterrows():
        color = "var(--up)" if r["change_pct"] >= 0 else "var(--down)"
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;padding:7px 4px;'
            f'border-bottom:1px solid var(--card-border);">'
            f'<span style="color:var(--t1);font-weight:600;">{r["symbol"]}</span>'
            f'<span style="color:var(--t2);">₹{r["price"]:,.2f}</span>'
            f'<span style="color:{color};font-weight:600;">{r["change_pct"]:+.2f}%</span></div>',
            unsafe_allow_html=True)


with g:
    st.markdown("**🟢 Top gainers**")
    if movers.empty:
        st.caption("Unavailable right now.")
    else:
        _mover_rows(movers, ascending=False)
with l:
    st.markdown("**🔴 Top losers**")
    if movers.empty:
        st.caption("Unavailable right now.")
    else:
        _mover_rows(movers, ascending=True)
with h:
    st.markdown("**🏔️ Near 52-week high**")
    highs = analytics.near_52w_high(closes)
    if highs.empty:
        st.caption("None right now (or data unavailable).")
    else:
        for _, r in highs.head(5).iterrows():
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:7px 4px;'
                f'border-bottom:1px solid var(--card-border);">'
                f'<span style="color:var(--t1);font-weight:600;">{r["symbol"]}</span>'
                f'<span style="color:var(--t2);">₹{r["price"]:,.2f}</span>'
                f'<span style="color:var(--up);font-weight:600;">{r["pct_of_high"]:.0f}% of high</span></div>',
                unsafe_allow_html=True)

st.divider()

# ---- Daily AI suggestions ------------------------------------------------------------
st.subheader("🤖 Today's AI suggestions")
from services import ai, brief  # noqa: E402

if not ai.has_key():
    st.info("Add an API key in ⚙️ Settings (OpenAI, Grok or Groq) to get 5 AI-picked "
            "stocks here every day.")
else:
    cached = brief.cached_today()
    if cached:
        st.caption(f"Updated for this {brief._slot()} session — refreshes automatically "
                   "morning, midday and after market close.")
        st.markdown(cached)
        if st.button("🔄 Regenerate now"):
            with st.spinner("Asking the AI…"):
                ok, text = brief.generate(force=True)
            if ok:
                st.rerun()
            else:
                st.error(text)
    else:
        if st.button("✨ Generate today's 5 AI picks"):
            with st.spinner("Scoring 50 stocks & asking the AI…"):
                ok, text = brief.generate()
            if ok:
                st.rerun()
            else:
                st.error(text)
        st.caption("Generated once per day from real scored data, then cached.")

st.divider()

# ---- Pulse + mood -----------------------------------------------------------------
pc, gc = st.columns([1.4, 1])
with pc:
    pulse = analytics.market_pulse(closes)
    pulse_card(pulse)
    st.caption("Computed from real NIFTY 50 price data (breadth rules) — not a prediction.")
with gc:
    if pulse:
        st.plotly_chart(mood_gauge(pulse["score"]), use_container_width=True,
                        config={"displayModeBar": False})

# ---- Sector heatmap ------------------------------------------------------------------
st.subheader("Sector heatmap")
sector_heatmap(analytics.sector_performance())

st.divider()

# ---- Technical standouts ----------------------------------------------------------------
st.subheader("Technical standouts")
scores = analytics.technical_scores(closes)
standout_cards(scores, n=5)
st.caption("⚠️ Rule-based technical score — mechanical calculation, not advice.")

st.divider()

# ---- Index chart ---------------------------------------------------------------------------
left, right = st.columns([3, 1])
with right:
    idx_name = st.selectbox("Index", list(INDICES), index=list(INDICES).index(DEFAULT_INDEX))
    period = st.select_slider("Period", options=list(PERIOD_INTERVALS), value="6mo")
hist = md.get_history(INDICES[idx_name], period=period, interval=PERIOD_INTERVALS[period])
with left:
    if hist.empty:
        st.warning(f"Could not load history for {idx_name}.")
    else:
        st.plotly_chart(line_chart(hist, f"{idx_name} — {period}"), use_container_width=True)

data_disclaimer()
