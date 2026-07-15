"""Trade-idea engine — mechanical long setups from real OHLC data.

A symbol qualifies as a LONG SETUP when at least 4 of 5 documented rules hold:
  1. Close above SMA50            2. SMA50 rising (vs 10 sessions ago)
  3. MACD above signal line       4. RSI between 45 and 70
  5. Positive 21-day return

Levels are pure arithmetic:
  Entry  = last close
  Stop   = entry − 2×ATR(14)      Target = entry + 3×ATR(14)   (R:R 1.5)

These are rule-based calculations for study — NOT SEBI-registered advice.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

from services import indicators as ta
from utils.logger import get_logger

log = get_logger("ideas")

RULE_NAMES = ["Above SMA50", "SMA50 rising", "MACD bullish", "RSI 45–70", "1M return +ve"]


@st.cache_data(ttl=600, show_spinner=False)
def last_scan_time() -> str:
    """Approximates when the current cached scan was made (same TTL as data)."""
    from datetime import datetime
    return datetime.now().strftime("%d %b, %H:%M")


@st.cache_data(ttl=600, show_spinner=False)
def batch_ohlc(symbols: tuple[str, ...], period: str = "1y") -> dict[str, pd.DataFrame]:
    """One batched download -> {symbol: OHLCV DataFrame}."""
    try:
        data = yf.download(list(symbols), period=period, interval="1d",
                           group_by="ticker", auto_adjust=True, progress=False, threads=True)
        out = {}
        for s in symbols:
            try:
                df = data[s].dropna(subset=["Close"])
                if len(df) >= 120:
                    out[s] = df
            except Exception:
                continue
        return out
    except Exception as e:
        log.warning("batch_ohlc failed: %s", e)
        return {}


def generate_ideas(ohlc: dict[str, pd.DataFrame], min_rules: int = 4) -> pd.DataFrame:
    """Evaluate the 5 rules per symbol; return qualifying long setups."""
    rows = []
    for sym, df in ohlc.items():
        try:
            c = df["Close"]
            s50 = ta.sma(c, 50)
            r = ta.rsi(c).iloc[-1]
            m = ta.macd(c)
            atr = ta.atr(df).iloc[-1]
            if pd.isna(s50.iloc[-1]) or pd.isna(atr) or atr <= 0:
                continue
            ret21 = (c.iloc[-1] / c.iloc[-22] - 1) * 100 if len(c) > 22 else 0.0

            rules = [
                bool(c.iloc[-1] > s50.iloc[-1]),
                bool(len(s50.dropna()) > 10 and s50.iloc[-1] > s50.iloc[-11]),
                bool(m["macd"].iloc[-1] > m["signal"].iloc[-1]),
                bool(45 <= r <= 70),
                bool(ret21 > 0),
            ]
            matched = sum(rules)
            if matched < min_rules:
                continue

            entry = float(c.iloc[-1])
            stop = entry - 2 * float(atr)
            target = entry + 3 * float(atr)
            rows.append({
                "symbol": sym.replace(".NS", ""),
                "entry": round(entry, 2),
                "target": round(target, 2),
                "stop": round(stop, 2),
                "target_pct": round((target / entry - 1) * 100, 1),
                "stop_pct": round((stop / entry - 1) * 100, 1),
                "atr": round(float(atr), 2),
                "rsi": round(float(r), 1),
                "rules_matched": matched,
                "rules": [n for n, ok in zip(RULE_NAMES, rules) if ok],
            })
        except Exception as e:
            log.warning("idea eval failed for %s: %s", sym, e)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(["rules_matched", "rsi"], ascending=[False, True]).reset_index(drop=True)
