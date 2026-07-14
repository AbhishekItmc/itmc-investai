"""Trade Ideas — mechanical long setups, Univest-style cards."""
import streamlit as st

from components.ui import data_disclaimer
from config import NIFTY50
from services import ideas as idea_svc

st.title("💡 Trade Ideas")
st.caption("Long setups where ≥4 of 5 trend rules hold on real NIFTY 50 price data. "
           "Levels are ATR arithmetic (stop = entry − 2×ATR, target = entry + 3×ATR).")

st.warning("⚠️ **These are rule-based calculations for study — not SEBI-registered "
           "investment advice.** No analyst has reviewed them. Markets can invalidate "
           "any setup at any time.", icon="⚠️")

min_rules = st.radio("Setup strictness", [5, 4], index=1, horizontal=True,
                     format_func=lambda v: f"{v}/5 rules")

with st.spinner("Scanning NIFTY 50…"):
    ohlc = idea_svc.batch_ohlc(tuple(NIFTY50))
    setups = idea_svc.generate_ideas(ohlc, min_rules=min_rules)

if ohlc == {}:
    st.error("Could not fetch market data. Check your connection and retry.")
    st.stop()
if setups.empty:
    st.info(f"No stocks currently satisfy {min_rules}/5 rules. That itself is information — "
            "the market may be weak. Try 4/5 or check back later.")
    st.stop()

st.caption(f"Scanned {len(ohlc)} stocks · {len(setups)} setups found")

for i in range(0, len(setups), 3):
    cols = st.columns(3)
    for col, (_, s) in zip(cols, setups.iloc[i:i + 3].iterrows()):
        with col:
            st.markdown(
                f"""
                <div class="aurora-card aurora-glow" style="text-align:left;">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="color:var(--t1);font-weight:700;font-size:1.1rem;">{s['symbol']}</span>
                    <span class="ss-tag bull">LONG SETUP · {s['rules_matched']}/5</span>
                  </div>
                  <div style="margin-top:14px;display:flex;justify-content:space-between;">
                    <div><div style="color:var(--t2);font-size:0.75rem;">ENTRY</div>
                         <div style="color:var(--t1);font-weight:600;">₹{s['entry']:,}</div></div>
                    <div><div style="color:var(--t2);font-size:0.75rem;">TARGET</div>
                         <div style="color:var(--up);font-weight:600;">₹{s['target']:,}
                           <span style="font-size:0.75rem;">({s['target_pct']:+.1f}%)</span></div></div>
                    <div><div style="color:var(--t2);font-size:0.75rem;">STOPLOSS</div>
                         <div style="color:var(--down);font-weight:600;">₹{s['stop']:,}
                           <span style="font-size:0.75rem;">({s['stop_pct']:+.1f}%)</span></div></div>
                  </div>
                  <div style="margin-top:12px;color:var(--t2);font-size:0.78rem;">
                    R:R 1.5 · ATR ₹{s['atr']} · RSI {s['rsi']}<br>
                    ✓ {' · '.join(s['rules'])}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

data_disclaimer()
