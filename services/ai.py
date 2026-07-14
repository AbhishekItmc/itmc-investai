"""AI service — OpenAI reasoning grounded strictly on real market data.

The model only sees structured data we fetched from yfinance; the system
prompt forbids inventing numbers and requires separating facts from analysis.
"""
from __future__ import annotations

import json
import re

from database import db
from services import indicators as ta
from services import market_data as md
from utils.logger import get_logger

log = get_logger("ai")

# Providers: OpenAI and Grok (xAI) — Grok uses an OpenAI-compatible API
PROVIDERS = {
    "openai": {"label": "OpenAI", "base_url": None, "default_model": "gpt-4o-mini",
               "key_setting": "openai_api_key", "model_setting": "openai_model",
               "key_prefix": "sk-"},
    "grok": {"label": "Grok (xAI)", "base_url": "https://api.x.ai/v1", "default_model": "grok-3-mini",
             "key_setting": "grok_api_key", "model_setting": "grok_model",
             "key_prefix": "xai-"},
    "groq": {"label": "Groq (fast Llama)", "base_url": "https://api.groq.com/openai/v1",
             "default_model": "llama-3.3-70b-versatile",
             "key_setting": "groq_api_key", "model_setting": "groq_model",
             "key_prefix": "gsk_"},
}


def active_provider() -> str:
    p = db.get_setting("ai_provider", "openai") or "openai"
    return p if p in PROVIDERS else "openai"

SYSTEM_PROMPT = """You are ITMC InvestAI's copilot for Indian (NSE/BSE) markets.

STRICT RULES:
1. Use ONLY the numbers in the MARKET DATA block below. NEVER invent prices,
   ratios, targets or percentages. If a number is not in the data, say
   "not available in my data".
2. Clearly separate **Facts** (straight from the data) and **Analysis**
   (your interpretation). Label them.
3. Do not give a buy/sell instruction. You may describe what the data shows
   (trend, valuation context, risks) and end with "This is analysis, not
   investment advice."
4. Do not state fake confidence percentages. Express uncertainty in words.
5. Be concise. Use short sections: Summary / Facts / Analysis / Risks.
6. Reply in the user's language (English or Hindi/Hinglish)."""

from config import ALIASES  # shared company-name aliases -> NSE base symbol


def has_key() -> bool:
    return bool(db.get_setting(PROVIDERS[active_provider()]["key_setting"]))


def detect_symbols(text: str, known: tuple[str, ...] = ()) -> list[str]:
    """Find NSE symbols mentioned in free text (aliases, known symbols, X.NS)."""
    t = text.lower()
    found: list[str] = []
    for name, sym in ALIASES.items():
        if re.search(rf"\b{re.escape(name)}\b", t):
            found.append(f"{sym}.NS")
    for sym in known:  # watchlist/portfolio symbols
        base = sym.replace(".NS", "").replace(".BO", "").lower()
        if re.search(rf"\b{re.escape(base)}\b", t):
            found.append(sym)
    for m in re.findall(r"\b([A-Za-z&-]{2,15})\.(?:NS|BO)\b", text):
        found.append(f"{m.upper()}.NS")
    # Bare uppercase tokens like "INFY"
    for m in re.findall(r"\b[A-Z][A-Z&-]{2,14}\b", text):
        found.append(f"{m}.NS")
    seen, out = set(), []
    for s in found:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out[:3]


def build_context(symbols: list[str]) -> str:
    """Fetch real data for each symbol and pack it as JSON for the model."""
    blocks = []
    for sym in symbols:
        quote = md.get_quote(sym)
        if quote is None:
            continue
        info = md.get_info(sym)
        block = {"symbol": sym, "quote": quote, "fundamentals": info}
        hist = md.get_history(sym, period="1y", interval="1d")
        if not hist.empty:
            enriched = ta.enrich(hist)
            block["technical_readings"] = [
                {k: r[k] for k in ("Indicator", "Value", "Reading")}
                for r in ta.signal_summary(enriched)
            ]
            block["returns_pct"] = {
                "1m": round((hist["Close"].iloc[-1] / hist["Close"].iloc[-22] - 1) * 100, 1)
                if len(hist) > 22 else None,
                "1y": round((hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100, 1),
            }
        blocks.append(block)
    if not blocks:
        return "No market data could be fetched for the mentioned stocks."
    return json.dumps(blocks, default=str, ensure_ascii=False)


def ask(chat_history: list[dict], context: str) -> str:
    """One completion. chat_history = [{'role','content'}, ...]. Returns text or error note."""
    try:
        from openai import OpenAI
    except ImportError:
        return ("The `openai` package is not installed. Run "
                "`pip install openai` and restart the app. "
                "(It is required for both OpenAI and Grok.)")
    prov = PROVIDERS[active_provider()]
    key = db.get_setting(prov["key_setting"])
    if not key:
        return f"No {prov['label']} API key set. Add one in **Settings** first."
    model = db.get_setting(prov["model_setting"], prov["default_model"]) or prov["default_model"]
    try:
        client = OpenAI(api_key=key, base_url=prov["base_url"])
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"MARKET DATA (fetched just now from Yahoo Finance):\n{context}"},
        ] + chat_history[-8:]
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0.3)
        return resp.choices[0].message.content or "(empty response)"
    except Exception as e:
        log.warning("OpenAI call failed: %s", e)
        return f"AI request failed: {e}"
