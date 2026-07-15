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

_PROMPT = """From the MARKET DATA (real NIFTY 50 prices + real news headlines,
fetched just now), pick the 5 most noteworthy stocks FOR THIS SESSION.

Prioritise what is happening TODAY: big day moves (gainers/losers), 52-week-high
breakouts, sector rotation and stocks named in the headlines — do not simply
repeat the highest technical scores every time (mention a score leader only if
something changed about it). For each pick, 1–2 sentences grounded ONLY in the
given numbers/headlines, and say WHY TODAY (e.g. "top gainer +3.1% today",
"named in headline about X"). Format: markdown list, **SYMBOL** — reason.
Start with one sentence blending market pulse and the news mood. Do NOT invent
numbers not present in the data. No buy/sell instructions. End with:
"_Real data + AI interpretation — not investment advice._" Reply in English."""


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
        "session": _slot(),
        "market_pulse": analytics.market_pulse(closes),
        "top10_by_technical_score": scores.head(10).to_dict("records"),
        "bottom5_by_technical_score": scores.tail(5).to_dict("records"),
    }
    sectors = analytics.sector_performance()
    if not sectors.empty:
        payload["sector_day_change_pct"] = sectors.round(2).to_dict("records")

    # Today's actual action — movers and 52-week-high breakouts
    try:
        from config import NIFTY50 as _N
        from services import market_data as md
        movers = md.get_movers(tuple(_N))
        if not movers.empty:
            payload["today_top_gainers"] = movers.head(5).round(2).to_dict("records")
            payload["today_top_losers"] = movers.tail(5).round(2).to_dict("records")
        highs = analytics.near_52w_high(closes)
        if not highs.empty:
            payload["near_52w_high"] = highs.head(5).to_dict("records")
    except Exception as e:
        log.warning("brief movers failed: %s", e)

    # Latest real headlines
    try:
        from services import news
        headlines = news.market_news(limit=12)
        if headlines:
            payload["latest_headlines"] = [
                {"source": h["source"], "title": h["title"]} for h in headlines]
    except Exception as e:
        log.warning("brief news failed: %s", e)

    text = ai.ask([{"role": "user", "content": _PROMPT}],
                  json.dumps(payload, default=str))
    if text.startswith(("AI request failed", "No ")):
        return False, text
    try:
        db.set_setting(_key(), text)
    except Exception as e:
        log.warning("could not cache daily brief: %s", e)
    return True, text
