"""Email allowlist — restricts sign-in to approved team members.

Two sources, combined:
  1. secrets.toml  [access] allowed_emails  — permanent, survives redeploys (admins)
  2. SQLite setting "allowed_emails"        — editable in Settings by admins
                                              (note: resets if the cloud app redeploys)
If BOTH are empty, access is open to any signed-in Google account (backwards
compatible). Admins are the emails listed in secrets.
"""
from __future__ import annotations

import streamlit as st

from database import db


def _secrets_list() -> set[str]:
    try:
        raw = st.secrets.get("access", {}).get("allowed_emails", [])
    except Exception:
        return set()
    if isinstance(raw, str):
        raw = raw.replace("\n", ",").split(",")
    return {str(e).strip().lower() for e in raw if str(e).strip()}


def db_list() -> set[str]:
    raw = db.get_setting("allowed_emails", "") or ""
    return {e.strip().lower() for e in raw.replace("\n", ",").split(",") if e.strip()}


def allowlist() -> set[str]:
    return _secrets_list() | db_list()


def is_allowed(email: str) -> bool:
    al = allowlist()
    return True if not al else email.strip().lower() in al


def is_admin(email: str) -> bool:
    """Admins = emails in the secrets allowlist (they manage the Settings list)."""
    return email.strip().lower() in _secrets_list()


def save_db_list(emails: str) -> None:
    cleaned = ",".join(sorted({e.strip().lower() for e in emails.replace("\n", ",").split(",")
                               if e.strip() and "@" in e}))
    db.set_setting("allowed_emails", cleaned)
