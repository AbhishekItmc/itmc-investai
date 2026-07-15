"""Persistence layer — Postgres (permanent, for cloud) or SQLite (local fallback).

Backend selection: if .streamlit/secrets.toml contains
    [database]
    url = "postgresql://user:pass@host/db?sslmode=require"
the app uses Postgres (data survives redeploys). Otherwise SQLite at data/investai.db.

Public API is identical for both backends. SQL is written with '?' placeholders
and converted to '%s' for Postgres automatically.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import streamlit as st

from config import DATA_DIR, DB_PATH
from utils.logger import get_logger

log = get_logger("database")

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS watchlist (
    user_email TEXT NOT NULL DEFAULT 'local',
    symbol     TEXT NOT NULL,
    added_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_email, symbol)
);
CREATE TABLE IF NOT EXISTS portfolio (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_email TEXT NOT NULL DEFAULT 'local',
    symbol     TEXT NOT NULL,
    quantity   REAL NOT NULL,
    buy_price  REAL NOT NULL,
    buy_date   TEXT,
    notes      TEXT
);
"""

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS watchlist (
    user_email TEXT NOT NULL DEFAULT 'local',
    symbol     TEXT NOT NULL,
    added_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_email, symbol)
);
CREATE TABLE IF NOT EXISTS portfolio (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_email TEXT NOT NULL DEFAULT 'local',
    symbol     TEXT NOT NULL,
    quantity   DOUBLE PRECISION NOT NULL,
    buy_price  DOUBLE PRECISION NOT NULL,
    buy_date   TEXT,
    notes      TEXT
);
"""


def _pg_url() -> str | None:
    try:
        return st.secrets.get("database", {}).get("url") or None
    except Exception:
        return None


def is_postgres() -> bool:
    return bool(_pg_url())


@st.cache_resource(show_spinner=False)
def _pg_pool():
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool
    return ConnectionPool(
        _pg_url(), min_size=0, max_size=4, open=True,
        kwargs={"row_factory": dict_row},
    )


@contextmanager
def get_conn():
    """Yields a connection; commits on success, rolls back on error."""
    if is_postgres():
        with _pg_pool().connection() as conn:   # pool commits/rolls back on exit
            yield conn
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def _q(sql: str) -> str:
    """Convert '?' placeholders to '%s' for Postgres."""
    return sql.replace("?", "%s") if is_postgres() else sql


def _migrate_sqlite(conn) -> None:
    """Upgrade pre-multi-user SQLite databases."""
    wcols = [r["name"] for r in conn.execute("PRAGMA table_info(watchlist)")]
    if wcols and "user_email" not in wcols:
        log.info("migrating watchlist to per-user schema")
        conn.executescript("""
            ALTER TABLE watchlist RENAME TO watchlist_old;
            CREATE TABLE watchlist (
                user_email TEXT NOT NULL DEFAULT 'local',
                symbol     TEXT NOT NULL,
                added_at   TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_email, symbol)
            );
            INSERT INTO watchlist(user_email, symbol, added_at)
                SELECT 'local', symbol, added_at FROM watchlist_old;
            DROP TABLE watchlist_old;
        """)
    pcols = [r["name"] for r in conn.execute("PRAGMA table_info(portfolio)")]
    if pcols and "user_email" not in pcols:
        log.info("migrating portfolio to per-user schema")
        conn.execute("ALTER TABLE portfolio ADD COLUMN user_email TEXT NOT NULL DEFAULT 'local'")


def init_db() -> None:
    try:
        with get_conn() as conn:
            if is_postgres():
                conn.execute(_PG_SCHEMA)
                log.info("using Postgres backend")
            else:
                _migrate_sqlite(conn)
                conn.executescript(_SQLITE_SCHEMA)
    except Exception as e:
        log.error("init_db failed: %s", e)
        raise


# ---- settings (global) -------------------------------------------------------

def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(_q(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value"), (key, value))


def get_setting(key: str, default: str | None = None) -> str | None:
    try:
        with get_conn() as conn:
            row = conn.execute(_q("SELECT value FROM settings WHERE key = ?"), (key,)).fetchone()
        return row["value"] if row else default
    except Exception as e:
        log.warning("get_setting(%s) failed: %s", key, e)
        return default


# ---- watchlist (per user) ----------------------------------------------------

def get_watchlist(user: str = "local") -> list[str]:
    try:
        with get_conn() as conn:
            rows = conn.execute(_q(
                "SELECT symbol FROM watchlist WHERE user_email = ? ORDER BY added_at"),
                (user,)).fetchall()
        return [r["symbol"] for r in rows]
    except Exception as e:
        log.warning("get_watchlist failed: %s", e)
        return []


def add_to_watchlist(symbol: str, user: str = "local") -> None:
    with get_conn() as conn:
        conn.execute(_q(
            "INSERT INTO watchlist(user_email, symbol) VALUES(?, ?) "
            "ON CONFLICT(user_email, symbol) DO NOTHING"), (user, symbol))


def remove_from_watchlist(symbol: str, user: str = "local") -> None:
    with get_conn() as conn:
        conn.execute(_q("DELETE FROM watchlist WHERE user_email = ? AND symbol = ?"),
                     (user, symbol))


# ---- portfolio (per user) ------------------------------------------------------

def get_portfolio(user: str = "local") -> list[dict]:
    try:
        with get_conn() as conn:
            rows = conn.execute(_q(
                "SELECT id, symbol, quantity, buy_price, buy_date, notes "
                "FROM portfolio WHERE user_email = ? ORDER BY symbol"), (user,)).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.warning("get_portfolio failed: %s", e)
        return []


def add_holding(symbol: str, quantity: float, buy_price: float,
                buy_date: str | None = None, notes: str = "",
                user: str = "local") -> None:
    with get_conn() as conn:
        conn.execute(_q(
            "INSERT INTO portfolio(user_email, symbol, quantity, buy_price, buy_date, notes) "
            "VALUES(?, ?, ?, ?, ?, ?)"), (user, symbol, quantity, buy_price, buy_date, notes))


def remove_holding(holding_id: int, user: str = "local") -> None:
    with get_conn() as conn:
        conn.execute(_q("DELETE FROM portfolio WHERE id = ? AND user_email = ?"),
                     (holding_id, user))
