"""Technical Analysis — indicators computed from real price history."""
import pandas as pd
import streamlit as st

from components.charts import technical_chart
from components.ui import data_disclaimer
from database import db
from services import indicators as ta
from services import market_data as md

st.title("📐 Technical Analysis")

from utils.user import current_user  # noqa: E402

watchlist = [s.replace(".NS", "") for s in db.get_watchlist(current_user())]

st.session_state.setdefault("ta_text", "RELIANCE")


def _pick_from_watchlist():
    v = st.session_state.get("ta_pick")
    if v:
        st.session_state["ta_text"] = v
        st.session_state["ta_pick"] = None


c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    raw = st.text_input("Search stock", key="ta_text",
                        help="NSE code (TCS) or company name (Infosys, HDFC Bank) — press Enter.")
with c2:
    period = st.selectbox("Period", ["6mo", "1y", "2y", "5y"], index=1)
with c3:
    show_bb = st.checkbox("Bollinger Bands", value=True)
    show_ma = st.checkbox("SMA 50/200", value=True)

if watchlist:
    try:
        st.pills("⭐ Quick pick", watchlist, key="ta_pick", on_change=_pick_from_watchlist)
    except Exception:  # older Streamlit without st.pills
        cols = st.columns(min(len(watchlist), 8))
        for col, w in zip(cols, watchlist[:8]):
            if col.button(w, key=f"ta_wl_{w}"):
                st.session_state["ta_text"] = w
                st.rerun()

symbol = md.resolve_symbol(raw)
hist = md.get_history(symbol, period=period, interval="1d")

if hist.empty:
    st.error(f"No price history for **{symbol}**. Check the symbol and your connection.")
    st.stop()

df = ta.enrich(hist)

# ---- Signal summary ---------------------------------------------------------
st.subheader("Indicator readings")
rows = ta.signal_summary(df)
if rows:
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.caption(
        "⚠️ These are mechanical, textbook indicator readings computed from price data — "
        "not predictions and not investment advice."
    )

# ---- Chart ------------------------------------------------------------------
st.plotly_chart(
    technical_chart(df, f"{symbol} — {period}", show_bb=show_bb, show_ma=show_ma),
    use_container_width=True,
)

with st.expander("Latest values"):
    cols = ["Close", "SMA20", "SMA50", "SMA200", "RSI", "macd", "signal", "ATR", "stoch_k"]
    present = [c for c in cols if c in df.columns]
    st.dataframe(df[present].tail(10).round(2), use_container_width=True)

data_disclaimer()
