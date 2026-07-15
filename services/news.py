"""Market news — real headlines from Indian market RSS feeds + Yahoo stock news.

No fabrication: items are shown exactly as published, with source and time.
AI summaries (optional) are generated only from the fetched headlines.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests
import streamlit as st
import yfinance as yf

from utils.logger import get_logger

log = get_logger("news")

FEEDS = [
    ("Economic Times", "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/marketreports.xml"),
    ("Livemint", "https://www.livemint.com/rss/markets"),
]

_HEADERS = {"User-Agent": "Mozilla/5.0 (ITMC InvestAI news reader)"}


def _parse_feed(source: str, url: str, limit: int = 15) -> list[dict]:
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=8)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if not title or not link:
                continue
            pub = item.findtext("pubDate")
            try:
                dt = parsedate_to_datetime(pub) if pub else None
            except Exception:
                dt = None
            items.append({"title": title, "link": link, "source": source, "published": dt})
            if len(items) >= limit:
                break
        return items
    except Exception as e:
        log.warning("feed %s failed: %s", source, e)
        return []


@st.cache_data(ttl=300, show_spinner=False)
def market_news(limit: int = 30) -> list[dict]:
    """Merged, newest-first headlines from all feeds."""
    items = []
    for source, url in FEEDS:
        items.extend(_parse_feed(source, url))
    far_past = datetime(1970, 1, 1, tzinfo=timezone.utc)
    items.sort(key=lambda x: x["published"] or far_past, reverse=True)
    return items[:limit]


@st.cache_data(ttl=300, show_spinner=False)
def stock_news(symbol: str, limit: int = 8) -> list[dict]:
    """Yahoo Finance news for one symbol (handles old and new yfinance formats)."""
    try:
        raw = yf.Ticker(symbol).news or []
        items = []
        for n in raw[:limit]:
            content = n.get("content", n)  # new format nests under 'content'
            title = content.get("title")
            link = (content.get("canonicalUrl") or {}).get("url") or n.get("link")
            provider = (content.get("provider") or {}).get("displayName") or n.get("publisher", "Yahoo")
            pub = content.get("pubDate")
            dt = None
            if pub:
                try:
                    dt = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
                except Exception:
                    dt = None
            elif n.get("providerPublishTime"):
                dt = datetime.fromtimestamp(n["providerPublishTime"], tz=timezone.utc)
            if title and link:
                items.append({"title": title, "link": link, "source": provider, "published": dt})
        return items
    except Exception as e:
        log.warning("stock_news(%s) failed: %s", symbol, e)
        return []


def time_ago(dt: datetime | None) -> str:
    if dt is None:
        return ""
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    mins = int((now - dt).total_seconds() // 60)
    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins}m ago"
    if mins < 1440:
        return f"{mins // 60}h ago"
    return f"{mins // 1440}d ago"


_BRIEF_PROMPT = """These are real, current Indian market headlines (just fetched).
Summarize in 4-6 bullet points what is moving the market today. Group related
headlines. Only use information present in the headlines — do not add facts,
prices or predictions. End with: "_AI summary of real headlines — not advice._" """


def ai_news_brief(items: list[dict]) -> str:
    from services import ai
    headlines = "\n".join(f"- [{i['source']}] {i['title']}" for i in items[:25])
    return ai.ask([{"role": "user", "content": _BRIEF_PROMPT}], headlines)
