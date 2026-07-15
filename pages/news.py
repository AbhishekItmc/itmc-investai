"""News — live Indian market headlines + stock-specific news."""
import streamlit as st

from database import db
from services import ai, news
from utils.user import current_user

st.title("📰 Market News")
st.caption("Live headlines from Economic Times, Moneycontrol and Livemint — "
           "refreshed every 5 minutes. Times are as published by the source.")

top = st.columns([1, 1, 2])
if top[0].button("🔄 Refresh now"):
    news.market_news.clear()
    news.stock_news.clear()
    st.rerun()

tab_market, tab_stocks = st.tabs(["🌐 Market", "⭐ My stocks"])


def _render(items: list[dict]) -> None:
    if not items:
        st.warning("No headlines available right now — source feeds may be unreachable.")
        return
    for it in items:
        when = news.time_ago(it["published"])
        st.markdown(
            f"""
            <div class="aurora-card" style="padding:14px 18px;margin-bottom:8px;">
              <a href="{it['link']}" target="_blank"
                 style="color:var(--t1);font-weight:600;text-decoration:none;">{it['title']}</a>
              <div style="color:var(--t2);font-size:0.78rem;margin-top:4px;">
                {it['source']}{(' · ' + when) if when else ''}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


with tab_market:
    items = news.market_news()
    if items and ai.has_key():
        with st.expander("🤖 AI summary of today's headlines"):
            if st.button("Summarize headlines"):
                with st.spinner("Reading the news…"):
                    st.session_state["news_brief"] = news.ai_news_brief(items)
            if st.session_state.get("news_brief"):
                st.markdown(st.session_state["news_brief"])
    _render(items)

with tab_stocks:
    watchlist = db.get_watchlist(current_user())
    if not watchlist:
        st.info("Add stocks to your ⭐ Watchlist to see their news here.")
    else:
        pick = st.selectbox("Stock", [s.replace(".NS", "") for s in watchlist])
        _render(news.stock_news(f"{pick}.NS" if "." not in pick else pick))
