"""Settings — API keys and cache control."""
import streamlit as st

from database import db

st.title("⚙️ Settings")

st.subheader("Appearance")
from utils.theme import current_theme  # noqa: E402

theme_choice = st.radio("Theme", ["light", "dark"],
                        index=0 if current_theme() == "light" else 1,
                        format_func=str.capitalize, horizontal=True)
if theme_choice != current_theme():
    db.set_setting("theme", theme_choice)
    st.rerun()

st.divider()

st.subheader("Profile")
current_name = db.get_setting("display_name", "") or ""
new_name = st.text_input("Display name (used in the Home greeting)", value=current_name)
if st.button("Save name") :
    db.set_setting("display_name", new_name.strip())
    st.success("Saved.")

st.divider()

st.subheader("AI provider")
st.caption("Keys are stored locally in SQLite (data/investai.db) and never leave your machine "
           "except to call the provider you choose.")

from services.ai import PROVIDERS, active_provider  # noqa: E402

provider = st.radio(
    "Provider", list(PROVIDERS),
    index=list(PROVIDERS).index(active_provider()),
    format_func=lambda p: PROVIDERS[p]["label"], horizontal=True,
)
prov = PROVIDERS[provider]
key_val = db.get_setting(prov["key_setting"], "") or ""
new_key = st.text_input(f"{prov['label']} API key", value=key_val, type="password",
                        placeholder=prov["key_prefix"] + "…")
model = st.text_input(
    "Model",
    value=db.get_setting(prov["model_setting"], prov["default_model"]) or prov["default_model"],
    help="OpenAI: gpt-4o-mini / gpt-4o · Grok: grok-3-mini / grok-3 · "
         "Groq: llama-3.3-70b-versatile / llama-3.1-8b-instant",
)
c_save, c_test = st.columns(2)
if c_save.button("Save AI settings", use_container_width=True):
    try:
        clean_key = "".join(new_key.split())  # strip ALL whitespace/newlines from paste
        db.set_setting("ai_provider", provider)
        db.set_setting(prov["key_setting"], clean_key)
        db.set_setting(prov["model_setting"], model.strip() or prov["default_model"])
        st.success(f"Saved — AI Copilot will use {prov['label']}.")
    except Exception as e:
        st.error(f"Could not save: {e}")

if c_test.button("🔌 Test connection", use_container_width=True):
    stored = db.get_setting(prov["key_setting"], "") or ""
    stored_model = db.get_setting(prov["model_setting"], prov["default_model"])
    if not stored:
        st.error(f"No {prov['label']} key saved yet. Paste it above and click Save first.")
    else:
        st.caption(f"Stored key: `{stored[:7]}…{stored[-4:]}` · length {len(stored)} · "
                   f"model `{stored_model}` · provider **{prov['label']}**")
        if not stored.startswith(prov["key_prefix"]):
            st.warning(f"This doesn't look like a {prov['label']} key — they start with "
                       f"`{prov['key_prefix']}`. OpenAI = `sk-`, Grok (xAI) = `xai-`, "
                       f"Groq = `gsk_`. Check you picked the right provider.")
        db.set_setting("ai_provider", provider)
        with st.spinner("Calling the API…"):
            from services import ai as ai_svc
            reply = ai_svc.ask([{"role": "user", "content": "Reply with exactly: OK"}],
                               "No market data needed for this test.")
        if reply.startswith(("AI request failed", "No ")):
            st.error(reply)
        else:
            st.success(f"✅ Connection works! Response: {reply[:100]}")

st.divider()

st.subheader("Data cache")
st.caption("Market data is cached for a few minutes to keep the app fast.")
if st.button("Clear cache & refresh data"):
    st.cache_data.clear()
    st.success("Cache cleared. Data will be re-fetched on next page load.")
