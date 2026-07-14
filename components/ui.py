"""Small UI helpers shared across pages."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.formatters import num, pct


def index_card(col, name: str, quote: dict | None) -> None:
    """Render one index metric card into a st.columns column."""
    with col:
        if quote is None:
            st.metric(name, "—", help="Data unavailable right now")
            return
        st.metric(
            name,
            num(quote["price"]),
            pct(quote["change_pct"]) if quote["change_pct"] is not None else None,
        )


def movers_table(df: pd.DataFrame, ascending: bool, n: int = 5) -> None:
    """Top gainers/losers table."""
    if df.empty:
        st.caption("No data available.")
        return
    view = df.sort_values("change_pct", ascending=ascending).head(n).copy()
    view["price"] = view["price"].map(lambda v: f"{v:,.2f}")
    view["change_pct"] = view["change_pct"].map(lambda v: f"{v:+.2f}%")
    view.columns = ["Symbol", "Price (₹)", "Change"]
    st.dataframe(view, hide_index=True, use_container_width=True)


def pulse_card(pulse: dict | None) -> None:
    """Market Pulse glass card (breadth-based, computed)."""
    if pulse is None:
        st.markdown('<div class="aurora-card">Market pulse unavailable right now.</div>',
                    unsafe_allow_html=True)
        return
    cls = {"Bullish": "pulse-bull", "Bearish": "pulse-bear"}.get(pulse["label"], "pulse-neut")
    dot = {"Bullish": "var(--up)", "Bearish": "var(--down)"}.get(pulse["label"], "var(--neut)")
    st.markdown(
        f"""
        <div class="aurora-card aurora-glow">
          <div style="color:var(--t2);font-size:0.85rem;">MARKET PULSE · NIFTY 50 breadth</div>
          <div class="pulse-label {cls}">
            <span class="pulse-dot" style="background:{dot}"></span>{pulse['label']}
          </div>
          <div style="color:var(--t2);margin-top:6px;font-size:0.86rem;">
            {pulse['pct_above_sma50']}% above SMA50 &nbsp;·&nbsp;
            {pulse['pct_advancers']}% advancing today &nbsp;·&nbsp;
            {pulse['n']} stocks scanned
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sector_heatmap(df: pd.DataFrame) -> None:
    """Sector tiles colored by day change."""
    if df.empty:
        st.caption("Sector data unavailable right now.")
        return
    tiles = []
    for _, row in df.sort_values("change_pct", ascending=False).iterrows():
        v = row["change_pct"]
        alpha = min(abs(v) / 2.5, 1) * 0.26 + 0.06
        bg = f"rgba(22,163,74,{alpha:.2f})" if v >= 0 else f"rgba(225,29,72,{alpha:.2f})"
        fg = "var(--up)" if v >= 0 else "var(--down)"
        tiles.append(
            f'<div class="sector-tile" style="background:{bg}">'
            f'<div class="sector-name">{row["sector"]}</div>'
            f'<div class="sector-chg" style="color:{fg}">{v:+.2f}%</div></div>'
        )
    st.markdown(f'<div class="sector-grid">{"".join(tiles)}</div>', unsafe_allow_html=True)


def standout_cards(df: pd.DataFrame, n: int = 5) -> None:
    """Top technical-score cards with score rings."""
    if df.empty:
        st.caption("Scores unavailable right now.")
        return
    top = df.head(n)
    cols = st.columns(len(top))
    tag_cls = {"Uptrend": "bull", "Downtrend": "bear", "Sideways": "neut"}
    for col, (_, r) in zip(cols, top.iterrows()):
        with col:
            st.markdown(
                f"""
                <div class="aurora-card standout">
                  <div class="ss-sym">{r['symbol']}</div>
                  <div class="ss-ring" style="--p:{r['score']}"><div>{r['score']}</div></div>
                  <div class="ss-tag {tag_cls.get(r['trend'], 'neut')}">{r['trend']}</div>
                  <div class="ss-sub">RSI {r['rsi']} · 21d {r['ret_21d']:+.1f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def data_disclaimer() -> None:
    st.caption(
        "Market data via Yahoo Finance (yfinance) — may be delayed. "
        "ITMC InvestAI shows real data only and is not investment advice."
    )
