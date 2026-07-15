"""Daily AI suggestions — 5 stocks picked by the AI from real scored data.

Generated at most once per day (cached in SQLite). The AI only sees data we
computed from real prices, and its instructions forbid inventing numbers.
"""
from __future__ import annotations

import json
from datetime import date, datetime

from config import NIFTY50
from database import db
from services import ai, analytics
from utils.logger import get_logger

log = get_logger("brief")

_PROMPT = """From the MARKET DATA (real NIFTY 50 prices, computed today), pick the
5 most noteworthy stocks. For each, write 1–2 sentences grounded ONLY in the
given numbers (score, RSI, 21-day return, trend, sector moves). Format as a
markdown list: **SYMBOL** — reason. Start with one sentence on overall market
pulse. Do NOT invent prices/targets/percentages not present in the data. Do not
give buy/sell instructions. End with: "_Rule-based data + AI interpretation —
not investment advice._" Reply in English."""


def _slot() -> str:
    """Three refresh windows per trading day (IST-ish local time):
    morning (before 12), midday (12–16), evening (after close)."""
    h = datetime.now().hour
    return "morning" if h < 12 else "midday" if h < 16 else "evening"


def _key() -> str:
    return f"daily_brief_{date.today().isoformat()}_{_slot()}"


def cached_today() -> str | None:
    return db.get_setting(_key())


def generate(force: bool = False) -> tuple[bool, str]:
    """Returns (ok, markdown_or_error). Caches successful results for the day."""
    if not force:
        cached = cached_today()
        if cached:
            return True, cached

    closes = analytics.batch_closes(tuple(NIFTY50))
    scores = analytics.technical_scores(closes)
    if scores.empty:
        return False, "Market data unavailable — cannot generate suggestions right now."
    payload = {
        "date": date.today().isoformat(),
        "market_pulse": analytics.market_pulse(closes),
        "top10_by_technical_score": scores.head(10).to_dict("records"),
        "bottom5_by_technical_score": scores.tail(5).to_dict("records"),
    }
    sectors = analytics.sector_performance()
    if not sectors.empty:
        payload["sector_day_change_pct"] = sectors.round(2).to_dict("records")

    text = ai.ask([{"role": "user", "content": _PROMPT}],
                  json.dumps(payload, default=str))
    if text.startswith(("AI request failed", "No ")):
        return False, text
    try:
        db.set_setting(_key(), text)
    except Exception as e:
        log.warning("could not cache daily brief: %s", e)
    return True, text
