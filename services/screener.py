"""Screener — fundamentals + technicals per symbol, filterable by chips."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services import indicators as ta
from services import market_data as md
from services.ideas import batch_ohlc
from utils.logger import get_logger

log = get_logger("screener")


@st.cache_data(ttl=3600, show_spinner=False)
def screener_table(symbols: tuple[str, ...]) -> pd.DataFrame:
    """Build the screener universe. Fundamentals come from yfinance .info
    (one call per symbol — cached for an hour), technicals from one batch download."""
    ohlc = batch_ohlc(symbols)
    rows = []
    for sym in symbols:
        df = ohlc.get(sym)
        if df is None:
            continue
        c = df["Close"]
        info = md.get_info(sym)
        rsi = float(ta.rsi(c).iloc[-1])
        s50 = ta.sma(c, 50).iloc[-1]
        hi52 = float(c.max())
        roe = info.get("returnOnEquity")
        dy = info.get("dividendYield")
        rows.append({
            "Symbol": sym.replace(".NS", ""),
            "Price": round(float(c.iloc[-1]), 2),
            "MCap (Cr)": round(info["marketCap"] / 1e7) if info.get("marketCap") else None,
            "P/E": round(info["trailingPE"], 1) if info.get("trailingPE") else None,
            "ROE %": round(roe * 100, 1) if roe is not None else None,
            "D/E": round(info["debtToEquity"] / 100, 2) if info.get("debtToEquity") else None,
            "Div %": round(dy, 2) if dy is not None else None,
            "RSI": round(rsi, 1),
            "Above SMA50": bool(pd.notna(s50) and c.iloc[-1] > s50),
            "1M %": round((c.iloc[-1] / c.iloc[-22] - 1) * 100, 1) if len(c) > 22 else None,
            "52W pos %": round(c.iloc[-1] / hi52 * 100, 1),
        })
    return pd.DataFrame(rows)


# Chip name -> filter function on the table
FILTERS = {
    "Large cap (>₹1L Cr)": lambda d: d["MCap (Cr)"] > 100_000,
    "Mid cap (₹25k–1L Cr)": lambda d: d["MCap (Cr)"].between(25_000, 100_000),
    "P/E < 25": lambda d: d["P/E"] < 25,
    "ROE > 15%": lambda d: d["ROE %"] > 15,
    "Low debt (D/E < 0.5)": lambda d: d["D/E"] < 0.5,
    "Dividend > 1%": lambda d: d["Div %"] > 1,
    "RSI oversold (<35)": lambda d: d["RSI"] < 35,
    "RSI healthy (45–70)": lambda d: d["RSI"].between(45, 70),
    "Above SMA50": lambda d: d["Above SMA50"],
    "Momentum (1M > +5%)": lambda d: d["1M %"] > 5,
    "Near 52W high (≥95%)": lambda d: d["52W pos %"] >= 95,
}


def apply_filters(df: pd.DataFrame, selected: list[str]) -> pd.DataFrame:
    out = df.copy()
    for name in selected:
        fn = FILTERS.get(name)
        if fn is None:
            continue
        try:
            mask = fn(out)
            out = out[mask.fillna(False)]
        except Exception as e:
            log.warning("filter %s failed: %s", name, e)
    return out
