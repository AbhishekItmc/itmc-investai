"""Smart Screener — chip filters over NIFTY 50 fundamentals + technicals."""
import streamlit as st

from components.ui import data_disclaimer
from config import NIFTY50
from services import screener as scr

st.title("🔎 Smart Screener")
st.caption("Filter NIFTY 50 stocks by real fundamentals (yfinance) and technicals. "
           "First load fetches fundamentals for ~50 stocks and can take a minute; "
           "after that it's cached for an hour.")

try:
    selected = st.pills("Filters", list(scr.FILTERS), selection_mode="multi")
except Exception:  # older Streamlit without st.pills
    selected = st.multiselect("Filters", list(scr.FILTERS))

with st.spinner("Building screener universe…"):
    table = scr.screener_table(tuple(NIFTY50))

if table.empty:
    st.error("Could not fetch screener data. Check your connection and retry.")
    st.stop()

result = scr.apply_filters(table, list(selected or []))
st.caption(f"{len(result)} of {len(table)} stocks match")

st.dataframe(
    result.sort_values("MCap (Cr)", ascending=False),
    hide_index=True, use_container_width=True, height=520,
)

st.caption("Some fundamental fields can be missing on Yahoo Finance — rows with missing "
           "values are excluded by filters that need them.")
data_disclaimer()
