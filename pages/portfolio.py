"""Portfolio — holdings, live P&L, allocation, health."""
from datetime import date

import streamlit as st

from components.charts import allocation_donut
from components.ui import data_disclaimer
from database import db
from services import market_data as md
from utils.formatters import inr, num, pct
from utils.user import current_user

st.title("💼 Portfolio")
_u = current_user()
if _u != "local":
    st.caption(f"Your personal portfolio — {_u}")

# ---- Add holding -------------------------------------------------------------
with st.expander("➕ Add holding"):
    with st.form("add_holding", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        raw = c1.text_input("Symbol", placeholder="e.g. TCS")
        qty = c2.number_input("Quantity", min_value=0.0, step=1.0)
        price = c3.number_input("Buy price (₹)", min_value=0.0, step=0.05)
        bdate = c4.date_input("Buy date", value=date.today())
        if st.form_submit_button("Add"):
            symbol = md.resolve_symbol(raw)
            if not raw.strip() or qty <= 0 or price <= 0:
                st.error("Enter a symbol, quantity > 0 and buy price > 0.")
            elif md.get_quote(symbol) is None:
                st.error(f"'{symbol}' not found — not added.")
            else:
                try:
                    db.add_holding(symbol, qty, price, str(bdate), user=_u)
                    st.success(f"Added {symbol}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not save: {e}")

holdings = db.get_portfolio(_u)
if not holdings:
    st.info("No holdings yet. Add your first one above.")
    st.stop()

# ---- Live valuation -----------------------------------------------------------
rows, missing = [], []
for h in holdings:
    q = md.get_quote(h["symbol"])
    if q is None:
        missing.append(h["symbol"])
        continue
    invested = h["quantity"] * h["buy_price"]
    current = h["quantity"] * q["price"]
    day_pnl = h["quantity"] * (q["change"] or 0)
    rows.append({**h, "price": q["price"], "invested": invested, "current": current,
                 "pnl": current - invested,
                 "pnl_pct": (current / invested - 1) * 100 if invested else 0,
                 "day_pnl": day_pnl})

if missing:
    st.warning(f"No live data for: {', '.join(missing)} — excluded from totals.")
if not rows:
    st.stop()

invested = sum(r["invested"] for r in rows)
current = sum(r["current"] for r in rows)
pnl = current - invested
day_pnl = sum(r["day_pnl"] for r in rows)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Invested", inr(invested, 0))
m2.metric("Current value", inr(current, 0))
m3.metric("Total P&L", inr(pnl, 0), pct(pnl / invested * 100 if invested else 0))
m4.metric("Today's P&L", inr(day_pnl, 0))

st.divider()

# ---- Holdings table ------------------------------------------------------------
hcols = st.columns([1.6, 1, 1.1, 1.1, 1.3, 1.3, 0.5])
for col, label in zip(hcols, ["Symbol", "Qty", "Avg buy", "Price", "P&L", "Today", ""]):
    col.markdown(f"**{label}**")
for r in rows:
    c = st.columns([1.6, 1, 1.1, 1.1, 1.3, 1.3, 0.5])
    c[0].write(r["symbol"].replace(".NS", ""))
    c[1].write(num(r["quantity"], 0))
    c[2].write(num(r["buy_price"]))
    c[3].write(num(r["price"]))
    color = "green" if r["pnl"] >= 0 else "red"
    c[4].markdown(f":{color}[{inr(r['pnl'], 0)} ({r['pnl_pct']:+.1f}%)]")
    dcolor = "green" if r["day_pnl"] >= 0 else "red"
    c[5].markdown(f":{dcolor}[{inr(r['day_pnl'], 0)}]")
    if c[6].button("✕", key=f"del_{r['id']}", help="Remove holding"):
        db.remove_holding(r["id"], _u)
        st.rerun()

st.divider()

# ---- Allocation + health --------------------------------------------------------
a, b = st.columns([1.2, 1])
with a:
    st.subheader("Allocation")
    st.plotly_chart(
        allocation_donut([r["symbol"].replace(".NS", "") for r in rows],
                         [r["current"] for r in rows]),
        use_container_width=True, config={"displayModeBar": False},
    )
with b:
    st.subheader("Portfolio health")
    n = len(rows)
    max_w = max(r["current"] for r in rows) / current * 100 if current else 0
    health = 50
    health += 20 if n >= 5 else 10 if n >= 3 else 0
    health += 20 if max_w <= 30 else 10 if max_w <= 50 else -10
    health += 10 if pnl >= 0 else 0
    health = max(0, min(100, health))
    label = "Good" if health >= 70 else "Fair" if health >= 50 else "Needs attention"
    st.markdown(
        f"""
        <div class="aurora-card aurora-glow">
          <div style="font-size:2.2rem;font-weight:700;color:var(--glow);">{health}%</div>
          <div style="color:var(--t1);font-weight:600;">{label}</div>
          <div style="color:var(--t2);font-size:0.85rem;margin-top:8px;">
            {n} holdings · largest position {max_w:.0f}% of portfolio
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("⚠️ Mechanical score from holding count, concentration and P&L — not advice.")

data_disclaimer()
