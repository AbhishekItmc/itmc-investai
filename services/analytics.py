"""Computed market analytics — breadth pulse, sector performance, technical scores.

Every number here is calculated mechanically from real yfinance price data
with the documented rules below. Nothing is predicted or fabricated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from services.indicators import macd, rsi, sma
from utils.logger import get_logger

log = get_logger("analytics")

SECTOR_INDICES = {
    "IT": "^CNXIT",
    "Bank": "^NSEBANK",
    "Pharma": "^CNXPHARMA",
    "Auto": "^CNXAUTO",
    "Energy": "^CNXENERGY",
    "FMCG": "^CNXFMCG",
    "Metal": "^CNXMETAL",
    "Realty": "^CNXREALTY",
}


@st.cache_data(ttl=600, show_spinner=False)
def batch_closes(symbols: tuple[str, ...], period: str = "1y") -> pd.DataFrame:
    """One batched download -> DataFrame of Close series per symbol."""
    try:
        data = yf.download(list(symbols), period=period, interval="1d",
                           group_by="ticker", auto_adjust=True, progress=False, threads=True)
        out = {}
        for s in symbols:
            try:
                c = data[s]["Close"].dropna()
                if len(c) >= 60:
                    out[s] = c
            except Exception:
                continue
        return pd.DataFrame(out)
    except Exception as e:
        log.warning("batch_closes failed: %s", e)
        return pd.DataFrame()


def technical_scores(closes: pd.DataFrame) -> pd.DataFrame:
    """Rule-based technical score per symbol (0–100).

    Rules (each satisfied rule adds points to a base of 50):
      +15 close above SMA50        +10 SMA50 rising vs 10 sessions ago
      +10 close above SMA200       +10 MACD above signal line
      +10 RSI in 50–70 (healthy)   -15 RSI > 75 (overheated) or < 30
      +5  positive 21-day return   -5  negative 21-day return
    """
    rows = []
    for sym in closes.columns:
        c = closes[sym].dropna()
        if len(c) < 60:
            continue
        s50, s200 = sma(c, 50), sma(c, 200)
        r = rsi(c).iloc[-1]
        m = macd(c)
        ret21 = (c.iloc[-1] / c.iloc[-22] - 1) * 100 if len(c) > 22 else 0.0

        score = 50
        if c.iloc[-1] > s50.iloc[-1]:
            score += 15
        if len(s50.dropna()) > 10 and s50.iloc[-1] > s50.iloc[-11]:
            score += 10
        if pd.notna(s200.iloc[-1]) and c.iloc[-1] > s200.iloc[-1]:
            score += 10
        if m["macd"].iloc[-1] > m["signal"].iloc[-1]:
            score += 10
        if 50 <= r <= 70:
            score += 10
        elif r > 75 or r < 30:
            score -= 15
        score += 5 if ret21 > 0 else -5
        score = int(np.clip(score, 0, 100))

        rows.append({
            "symbol": sym.replace(".NS", ""),
            "score": score,
            "rsi": round(float(r), 1),
            "above_sma50": bool(c.iloc[-1] > s50.iloc[-1]),
            "ret_21d": round(float(ret21), 1),
            "trend": "Uptrend" if score >= 65 else "Downtrend" if score <= 40 else "Sideways",
        })
    df = pd.DataFrame(rows)
    return df.sort_values("score", ascending=False).reset_index(drop=True) if not df.empty else df


def market_pulse(closes: pd.DataFrame) -> dict | None:
    """Breadth-based pulse: 60% weight = share of stocks above SMA50,
    40% = share of today's advancers. Score 0–100.
    >=60 Bullish, <=40 Bearish, else Neutral. NOT the CNN Fear & Greed index."""
    if closes.empty or len(closes) < 51:
        return None
    last, prev = closes.iloc[-1], closes.iloc[-2]
    s50 = closes.rolling(50).mean().iloc[-1]
    valid = last.notna() & s50.notna()
    if valid.sum() < 5:
        return None
    above = (last[valid] > s50[valid]).mean() * 100
    adv = (last[valid] > prev[valid]).mean() * 100
    score = round(0.6 * above + 0.4 * adv)
    label = "Bullish" if score >= 60 else "Bearish" if score <= 40 else "Neutral"
    return {
        "score": int(score), "label": label,
        "pct_above_sma50": round(above), "pct_advancers": round(adv),
        "n": int(valid.sum()),
    }


@st.cache_data(ttl=300, show_spinner=False)
def index_sparks(index_map_items: tuple[tuple[str, str], ...]) -> dict:
    """1-month close series per index for sparkline cards.

    Returns {name: {"series": pd.Series, "last": float, "change_pct": float}}."""
    symbols = [s for _, s in index_map_items]
    try:
        data = yf.download(symbols, period="1mo", interval="1d",
                           group_by="ticker", auto_adjust=True, progress=False, threads=True)
        out = {}
        for name, sym in index_map_items:
            try:
                c = (data[sym]["Close"] if len(symbols) > 1 else data["Close"]).dropna()
                if len(c) < 2:
                    continue
                out[name] = {
                    "series": c,
                    "last": float(c.iloc[-1]),
                    "change_pct": float((c.iloc[-1] / c.iloc[-2] - 1) * 100),
                }
            except Exception:
                continue
        return out
    except Exception as e:
        log.warning("index_sparks failed: %s", e)
        return {}


def near_52w_high(closes: pd.DataFrame, threshold: float = 0.98) -> pd.DataFrame:
    """Stocks whose last close is within `threshold` of their 52-week high."""
    if closes.empty:
        return pd.DataFrame()
    rows = []
    for sym in closes.columns:
        c = closes[sym].dropna()
        if len(c) < 60:
            continue
        hi = float(c.max())
        last = float(c.iloc[-1])
        if hi > 0 and last >= threshold * hi:
            rows.append({"symbol": sym.replace(".NS", ""), "price": round(last, 2),
                         "pct_of_high": round(last / hi * 100, 1)})
    df = pd.DataFrame(rows)
    return df.sort_values("pct_of_high", ascending=False).reset_index(drop=True) if not df.empty else df


@st.cache_data(ttl=600, show_spinner=False)
def sector_performance() -> pd.DataFrame:
    """Day % change of NSE sector indices. Empty DataFrame on failure."""
    try:
        data = yf.download(list(SECTOR_INDICES.values()), period="5d", interval="1d",
                           group_by="ticker", auto_adjust=True, progress=False, threads=True)
        rows = []
        for name, sym in SECTOR_INDICES.items():
            try:
                c = data[sym]["Close"].dropna()
                if len(c) >= 2:
                    rows.append({"sector": name, "change_pct": (c.iloc[-1] / c.iloc[-2] - 1) * 100})
            except Exception:
                continue
        return pd.DataFrame(rows)
    except Exception as e:
        log.warning("sector_performance failed: %s", e)
        return pd.DataFrame()
