"""Technical indicators — pure pandas implementations.

Implemented directly with pandas/numpy (no pandas-ta dependency: it is
incompatible with numpy >= 2). All functions take an OHLCV DataFrame from
services.market_data.get_history and compute from real data only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---- Core indicators --------------------------------------------------------

def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window).mean()


def ema(close: pd.Series, window: int) -> pd.Series:
    return close.ewm(span=window, adjust=False).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / window, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def bollinger(close: pd.Series, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    mid = sma(close, window)
    std = close.rolling(window).std()
    return pd.DataFrame({"bb_mid": mid, "bb_upper": mid + num_std * std, "bb_lower": mid - num_std * std})


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    hl = df["High"] - df["Low"]
    hc = (df["High"] - df["Close"].shift()).abs()
    lc = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / window, adjust=False).mean()


def stochastic(df: pd.DataFrame, k: int = 14, d: int = 3, smooth: int = 3) -> pd.DataFrame:
    low_k = df["Low"].rolling(k).min()
    high_k = df["High"].rolling(k).max()
    fast_k = 100 * (df["Close"] - low_k) / (high_k - low_k).replace(0, np.nan)
    slow_k = fast_k.rolling(smooth).mean()
    return pd.DataFrame({"stoch_k": slow_k, "stoch_d": slow_k.rolling(d).mean()})


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with all standard indicator columns added."""
    out = df.copy()
    close = out["Close"]
    out["SMA20"] = sma(close, 20)
    out["SMA50"] = sma(close, 50)
    out["SMA200"] = sma(close, 200)
    out["EMA20"] = ema(close, 20)
    out["RSI"] = rsi(close)
    out = out.join(macd(close))
    out = out.join(bollinger(close))
    out["ATR"] = atr(out)
    out = out.join(stochastic(out))
    return out


# ---- Rule-based signal summary ---------------------------------------------

BULLISH, BEARISH, NEUTRAL = "🟢 Bullish", "🔴 Bearish", "⚪ Neutral"


def signal_summary(df: pd.DataFrame) -> list[dict]:
    """Textbook rule-of-thumb readings of the latest bar.

    These are mechanical calculations, NOT investment advice or predictions.
    """
    if df.empty or "RSI" not in df.columns:
        return []
    last = df.iloc[-1]
    rows = []

    r = last["RSI"]
    rows.append({
        "Indicator": "RSI (14)", "Value": f"{r:.1f}",
        "Reading": BEARISH if r > 70 else BULLISH if r < 30 else NEUTRAL,
        "Rule": ">70 overbought, <30 oversold",
    })

    m, s = last["macd"], last["signal"]
    if pd.notna(m) and pd.notna(s):
        rows.append({
            "Indicator": "MACD (12,26,9)", "Value": f"{m:.2f} / {s:.2f}",
            "Reading": BULLISH if m > s else BEARISH,
            "Rule": "MACD above signal line = bullish momentum",
        })

    c = last["Close"]
    for ma_col, label in (("SMA50", "Price vs SMA50"), ("SMA200", "Price vs SMA200")):
        v = last.get(ma_col)
        if pd.notna(v):
            rows.append({
                "Indicator": label, "Value": f"{c:.2f} / {v:.2f}",
                "Reading": BULLISH if c > v else BEARISH,
                "Rule": "Close above moving average = uptrend",
            })

    up, lo = last.get("bb_upper"), last.get("bb_lower")
    if pd.notna(up) and pd.notna(lo):
        pos = (c - lo) / (up - lo) if up != lo else 0.5
        rows.append({
            "Indicator": "Bollinger (20,2)", "Value": f"{pos * 100:.0f}% of band",
            "Reading": BEARISH if pos > 1 else BULLISH if pos < 0 else NEUTRAL,
            "Rule": "Close outside bands = stretched move",
        })

    k = last.get("stoch_k")
    if pd.notna(k):
        rows.append({
            "Indicator": "Stochastic %K", "Value": f"{k:.1f}",
            "Reading": BEARISH if k > 80 else BULLISH if k < 20 else NEUTRAL,
            "Rule": ">80 overbought, <20 oversold",
        })
    return rows
