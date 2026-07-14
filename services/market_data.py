"""Market data service — thin, cached wrapper around yfinance.

All functions return real market data or None/empty on failure.
Nothing here is ever fabricated; errors are logged and surfaced to the UI.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
import yfinance as yf

from config import TTL_HISTORY, TTL_INFO, TTL_MOVERS, TTL_QUOTE
from utils.logger import get_logger

log = get_logger("market_data")


def normalize_symbol(raw: str) -> str:
    """'reliance' -> 'RELIANCE.NS'. Leaves indices (^NSEI) and suffixed symbols alone."""
    s = raw.strip().upper()
    if not s:
        return s
    if s.startswith("^") or "." in s or "=" in s:
        return s
    return f"{s}.NS"


@st.cache_data(ttl=86400, show_spinner=False)
def _yahoo_search(query: str) -> str | None:
    """Last-resort name lookup on Yahoo Finance. Returns an NSE/BSE symbol or None."""
    try:
        results = yf.Search(query, max_results=8).quotes
        for q in results:  # prefer NSE, then BSE
            if q.get("exchange") == "NSI":
                return q.get("symbol")
        for q in results:
            if q.get("exchange") == "BSE":
                return q.get("symbol")
    except Exception as e:
        log.warning("_yahoo_search(%s) failed: %s", query, e)
    return None


def resolve_symbol(raw: str) -> str:
    """Resolve free text (code OR company name) to a tradable symbol.

    Order: explicit suffix/index -> name alias -> NSE code guess -> Yahoo search.
    """
    from config import ALIASES  # local import to avoid cycles

    s = raw.strip()
    if not s:
        return ""
    if s.startswith("^") or "." in s or "=" in s:
        return s.upper()

    alias = ALIASES.get(s.lower())
    if alias:
        return f"{alias}.NS"

    guess = f"{s.upper().replace(' ', '')}.NS"
    if get_quote(guess) is not None:
        return guess

    found = _yahoo_search(s)
    return found or guess


def _fi(fast_info, key):
    """Safe access into yfinance FastInfo (raises on missing/failed keys)."""
    try:
        return fast_info[key]
    except Exception:
        return None


@st.cache_data(ttl=TTL_QUOTE, show_spinner=False)
def get_quote(symbol: str) -> dict | None:
    """Last price, previous close and derived change for one symbol."""
    try:
        fi = yf.Ticker(symbol).fast_info
        price = _fi(fi, "lastPrice")
        prev = _fi(fi, "previousClose")
        if price is None:
            return None
        change = price - prev if prev else None
        change_pct = (change / prev * 100) if change is not None and prev else None
        return {
            "symbol": symbol,
            "price": price,
            "prev_close": prev,
            "change": change,
            "change_pct": change_pct,
            "currency": _fi(fi, "currency"),
            "day_high": _fi(fi, "dayHigh"),
            "day_low": _fi(fi, "dayLow"),
            "year_high": _fi(fi, "yearHigh"),
            "year_low": _fi(fi, "yearLow"),
            "market_cap": _fi(fi, "marketCap"),
            "volume": _fi(fi, "lastVolume"),
        }
    except Exception as e:  # network, delisted, bad symbol …
        log.warning("get_quote(%s) failed: %s", symbol, e)
        return None


@st.cache_data(ttl=TTL_HISTORY, show_spinner=False)
def get_history(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """OHLCV history. Empty DataFrame on failure."""
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty:
            log.warning("get_history(%s, %s, %s): empty", symbol, period, interval)
            return pd.DataFrame()
        return df.dropna(subset=["Close"])
    except Exception as e:
        log.warning("get_history(%s) failed: %s", symbol, e)
        return pd.DataFrame()


@st.cache_data(ttl=TTL_INFO, show_spinner=False)
def get_info(symbol: str) -> dict:
    """Slow-changing metadata (name, sector, PE …). Empty dict on failure."""
    try:
        info = yf.Ticker(symbol).info or {}
        keep = (
            "longName", "shortName", "sector", "industry", "website",
            "trailingPE", "forwardPE", "priceToBook", "dividendYield",
            "beta", "trailingEps", "bookValue", "longBusinessSummary",
            "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "marketCap", "currency",
            "returnOnEquity", "debtToEquity", "profitMargins", "revenueGrowth",
        )
        return {k: info.get(k) for k in keep}
    except Exception as e:
        log.warning("get_info(%s) failed: %s", symbol, e)
        return {}


@st.cache_data(ttl=TTL_MOVERS, show_spinner=False)
def get_movers(symbols: tuple[str, ...]) -> pd.DataFrame:
    """Day change for a basket of symbols (one batched download).

    Returns DataFrame [symbol, price, change_pct] sorted by change_pct desc.
    """
    try:
        data = yf.download(
            list(symbols), period="5d", interval="1d",
            group_by="ticker", auto_adjust=True, progress=False, threads=True,
        )
        rows = []
        for sym in symbols:
            try:
                closes = data[sym]["Close"].dropna()
                if len(closes) < 2:
                    continue
                last, prev = closes.iloc[-1], closes.iloc[-2]
                rows.append({
                    "symbol": sym.replace(".NS", ""),
                    "price": last,
                    "change_pct": (last - prev) / prev * 100,
                })
            except Exception:
                continue
        df = pd.DataFrame(rows)
        if df.empty:
            log.warning("get_movers: no data for %d symbols", len(symbols))
            return df
        return df.sort_values("change_pct", ascending=False).reset_index(drop=True)
    except Exception as e:
        log.warning("get_movers failed: %s", e)
        return pd.DataFrame()
