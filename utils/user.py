"""Current-user helpers. Without login everything belongs to the 'local' user."""
from __future__ import annotations

import streamlit as st

from database import db


def current_user() -> str:
    """Google email when logged in, else 'local'."""
    try:
        if getattr(st, "user", None) and st.user.is_logged_in:
            return (st.user.email or "local").lower()
    except Exception:
        pass
    return "local"


def _name_key(user: str) -> str:
    return "display_name" if user == "local" else f"display_name:{user}"


def display_name() -> str:
    """Preferred greeting name: saved name -> Google name -> 'Investor'."""
    user = current_user()
    saved = db.get_setting(_name_key(user), "") or ""
    if saved:
        return saved
    try:
        if user != "local" and st.user.name:
            return str(st.user.name).split(" ")[0]
    except Exception:
        pass
    return "Investor"


def save_display_name(name: str) -> None:
    db.set_setting(_name_key(current_user()), name.strip())
