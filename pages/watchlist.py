"""Watchlist — track your favourite NSE/BSE stocks."""
import streamlit as st

from components.ui import data_disclaimer
from database import db
from services import market_data as md
from utils.formatters import compact_inr, num, pct
from utils.user import current_user

st.title("⭐ Watchlist")
_u = current_user()
if _u != "local":
    st.caption(f"Your personal watchlist — {_u}")

# ---- Add symbol -------------------------------------------------------------
c1, c2 = st.columns([3, 1])
with c1:
    raw = st.text_input("Add symbol", placeholder="e.g. TCS, HDFCBANK, INFY",
                        label_visibility="collapsed")
with c2:
    if st.button("➕ Add", use_container_width=True) and raw.strip():
        symbol = md.resolve_symbol(raw)
        if md.get_quote(symbol) is None:
            st.error(f"'{symbol}' not found — not added.")
        else:
            try:
                db.add_to_watchlist(symbol, _u)
                st.rerun()
            except Exception as e:
                st.error(f"Could not save: {e}")

symbols = db.get_watchlist(_u)
if not symbols:
    st.info("Your watchlist is empty. Add a symbol above (e.g. **RELIANCE** or **TCS**).")
    st.stop()

# ---- Live table -------------------------------------------------------------
header = st.columns([2, 1.2, 1.2, 1.5, 1.5, 0.6])
for col, label in zip(header, ["Symbol", "Price (₹)", "Change", "Day range", "Mkt cap", ""]):
    col.markdown(f"**{label}**")

for symbol in symbols:
    q = md.get_quote(symbol)
    row = st.columns([2, 1.2, 1.2, 1.5, 1.5, 0.6])
    row[0].write(symbol.replace(".NS", ""))
    if q is None:
        row[1].write("—")
        row[2].write("data unavailable")
        row[3].write("—")
        row[4].write("—")
    else:
        chg = q["change_pct"]
        row[1].write(num(q["price"]))
        row[2].markdown(
            f":{'green' if (chg or 0) >= 0 else 'red'}[{pct(chg)}]" if chg is not None else "—"
        )
        row[3].write(f"{num(q['day_low'])} – {num(q['day_high'])}")
        row[4].write(compact_inr(q["market_cap"]))
    if row[5].button("✕", key=f"rm_{symbol}", help=f"Remove {symbol}"):
        db.remove_from_watchlist(symbol, _u)
        st.rerun()

st.divider()
if st.button("🔄 Refresh quotes"):
    st.cache_data.clear()
    st.rerun()

data_disclaimer()
