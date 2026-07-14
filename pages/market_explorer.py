"""Market Explorer — Univest-style stock detail: verdict, ratios, peers, chart."""
import pandas as pd
import streamlit as st

from components.charts import candlestick_chart
from components.ui import data_disclaimer
from config import PERIOD_INTERVALS, SECTOR_MAP
from services import indicators as ta
from services import market_data as md
from utils.formatters import compact_inr, num, pct

st.title("🔍 Market Explorer")

c1, c2, c3 = st.columns([2, 1, 1])
_default = st.session_state.pop("explorer_prefill", None) or "RELIANCE"
with c1:
    raw = st.text_input("Search stock", value=_default,
                        help="Type an NSE code (TCS) or a company name (Infosys, HDFC Bank) and press Enter.")
with c2:
    period = st.selectbox("Period", list(PERIOD_INTERVALS), index=3)
with c3:
    show_ma = st.multiselect("Moving averages", [20, 50, 100, 200], default=[20, 50])

symbol = md.resolve_symbol(raw)
if not symbol:
    st.info("Enter a stock code or company name to begin.")
    st.stop()

quote = md.get_quote(symbol)
info = md.get_info(symbol)
if quote is None:
    st.error(f"No data found for **{symbol}**. Check the symbol and your connection.")
    st.stop()

name = info.get("longName") or info.get("shortName") or symbol
st.subheader(name)
if info.get("sector"):
    st.caption(f"{info.get('sector', '')} · {info.get('industry', '')}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Price", num(quote["price"]),
          pct(quote["change_pct"]) if quote["change_pct"] is not None else None)
m2.metric("Day range", f"{num(quote['day_low'])} – {num(quote['day_high'])}")
m3.metric("52-week range", f"{num(quote['year_low'])} – {num(quote['year_high'])}")
m4.metric("Market cap", compact_inr(quote["market_cap"]))

# ---- Verdict card (mechanical) -------------------------------------------------
hist = md.get_history(symbol, period="1y", interval="1d")
peer_group, peers = None, []
for group, members in SECTOR_MAP.items():
    if symbol in members:
        peer_group = group
        peers = [p for p in members if p != symbol]
        break

verdict_bits = []
if not hist.empty and len(hist) > 60:
    c = hist["Close"]
    s50 = ta.sma(c, 50).iloc[-1]
    r = float(ta.rsi(c).iloc[-1])
    trend = "Uptrend" if pd.notna(s50) and c.iloc[-1] > s50 else "Below 50-day trend"
    verdict_bits.append(trend)
    verdict_bits.append(f"RSI {r:.0f}")
    if quote.get("year_high"):
        pos = quote["price"] / quote["year_high"] * 100
        verdict_bits.append(f"{pos:.0f}% of 52-week high")

pe = info.get("trailingPE")
peer_pes = [md.get_info(p).get("trailingPE") for p in peers] if peers else []
peer_pes = [x for x in peer_pes if x]
if pe and peer_pes:
    median_pe = sorted(peer_pes)[len(peer_pes) // 2]
    rel = "below" if pe < median_pe else "above"
    verdict_bits.append(f"P/E {pe:.1f} ({rel} peer median {median_pe:.1f})")

if verdict_bits:
    st.markdown(
        f"""
        <div class="aurora-card aurora-glow">
          <div style="color:var(--t2);font-size:0.8rem;">SNAPSHOT (computed from data)</div>
          <div style="color:var(--t1);font-weight:600;font-size:1.05rem;margin-top:4px;">
            {' · '.join(verdict_bits)}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---- Chart ---------------------------------------------------------------------
chart_hist = md.get_history(symbol, period=period, interval=PERIOD_INTERVALS[period])
if chart_hist.empty:
    st.warning("Price history unavailable for this period.")
else:
    st.plotly_chart(
        candlestick_chart(chart_hist, f"{symbol} — {period}", mas=tuple(show_ma)),
        use_container_width=True,
    )

# ---- Key ratios ------------------------------------------------------------------
st.subheader("Key ratios")
r1 = st.columns(4)
r1[0].metric("P/E (TTM)", num(info.get("trailingPE"), 1))
r1[1].metric("P/B", num(info.get("priceToBook"), 1))
roe = info.get("returnOnEquity")
r1[2].metric("ROE", f"{roe * 100:.1f}%" if roe is not None else "—")
de = info.get("debtToEquity")
r1[3].metric("Debt/Equity", num(de / 100, 2) if de is not None else "—")
r2 = st.columns(4)
dy = info.get("dividendYield")
r2[0].metric("Dividend yield", f"{num(dy)}%" if dy is not None else "—")
pm = info.get("profitMargins")
r2[1].metric("Profit margin", f"{pm * 100:.1f}%" if pm is not None else "—")
rg = info.get("revenueGrowth")
r2[2].metric("Revenue growth", f"{rg * 100:.1f}%" if rg is not None else "—")
r2[3].metric("Beta", num(info.get("beta"), 2))

# ---- Peer comparison ---------------------------------------------------------------
if peers:
    st.subheader(f"Peers — {peer_group}")
    rows = []
    for p in [symbol] + peers:
        q, i = md.get_quote(p), md.get_info(p)
        if q is None:
            continue
        roe_p = i.get("returnOnEquity")
        rows.append({
            "Symbol": p.replace(".NS", "") + (" ◀" if p == symbol else ""),
            "Price": round(q["price"], 2),
            "Day %": round(q["change_pct"], 2) if q["change_pct"] is not None else None,
            "MCap": compact_inr(q["market_cap"]),
            "P/E": round(i["trailingPE"], 1) if i.get("trailingPE") else None,
            "ROE %": round(roe_p * 100, 1) if roe_p is not None else None,
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

with st.expander("About the company"):
    if info.get("longBusinessSummary"):
        st.write(info["longBusinessSummary"])
    else:
        st.caption("No description available.")

data_disclaimer()
