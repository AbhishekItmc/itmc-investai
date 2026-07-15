"""AI Copilot — ChatGPT-style chat grounded on real market data."""
import streamlit as st

from database import db
from services import ai
from services import market_data as md

st.title("🤖 AI Copilot")
st.caption("Ask about any NSE/BSE stock. Answers are grounded on live yfinance data — "
           "facts and AI analysis are labeled separately. Not investment advice.")

if not ai.has_key():
    st.info("Add your OpenAI or Grok API key in **⚙️ Settings** to enable the copilot.")
    st.stop()
st.caption(f"Powered by {ai.PROVIDERS[ai.active_provider()]['label']}")

if "chat" not in st.session_state:
    st.session_state.chat = []

# ---- Suggestion chips ---------------------------------------------------------
SUGGESTIONS = [
    "Should I look at Infosys right now?",
    "How risky is Tata Motors?",
    "Compare Wipro vs Tech Mahindra",
    "What does the data say about HDFC Bank?",
]
if not st.session_state.chat:
    cols = st.columns(2)
    for i, s in enumerate(SUGGESTIONS):
        if cols[i % 2].button(s, key=f"sug_{i}", use_container_width=True):
            st.session_state.prefill = s
            st.rerun()

# ---- History ---------------------------------------------------------------------
for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---- Input -----------------------------------------------------------------------
prompt = st.chat_input("Ask anything about Indian stocks…")
if not prompt and "prefill" in st.session_state:
    prompt = st.session_state.pop("prefill")

if prompt:
    st.session_state.chat.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    from utils.user import current_user
    _u = current_user()
    known = tuple(db.get_watchlist(_u)) + tuple(h["symbol"] for h in db.get_portfolio(_u))
    with st.chat_message("assistant"):
        with st.spinner("Fetching live data & thinking…"):
            symbols = ai.detect_symbols(prompt, known)
            context = ai.build_context(symbols) if symbols else \
                "No specific stock detected in the question. Ask the user to name a stock if needed."
            answer = ai.ask(st.session_state.chat, context)
        st.markdown(answer)
        if symbols:
            st.caption("Data fetched live for: " +
                       ", ".join(s.replace('.NS', '') for s in symbols))
    st.session_state.chat.append({"role": "assistant", "content": answer})

if st.session_state.chat and st.button("🗑️ Clear conversation"):
    st.session_state.chat = []
    st.rerun()
