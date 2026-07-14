"""SQLite persistence layer.

Phase 1 uses the settings table; watchlist/portfolio tables are created
now so later phases don't need migrations.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from config import DATA_DIR, DB_PATH
from utils.logger import get_logger

log = get_logger("database")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS watchlist (
    symbol   TEXT PRIMARY KEY,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS portfolio (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol    TEXT NOT NULL,
    quantity  REAL NOT NULL,
    buy_price REAL NOT NULL,
    buy_date  TEXT,
    notes     TEXT
);
"""


@contextmanager
def get_conn():
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


def init_db() -> None:
    try:
        with get_conn() as conn:
            conn.executescript(_SCHEMA)
    except Exception as e:
        log.error("init_db failed: %s", e)
        raise


def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def get_watchlist() -> list[str]:
    try:
        with get_conn() as conn:
            rows = conn.execute("SELECT symbol FROM watchlist ORDER BY added_at").fetchall()
        return [r["symbol"] for r in rows]
    except Exception as e:
        log.warning("get_watchlist failed: %s", e)
        return []


def add_to_watchlist(symbol: str) -> None:
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO watchlist(symbol) VALUES(?)", (symbol,))


def remove_from_watchlist(symbol: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))


def get_setting(key: str, default: str | None = None) -> str | None:
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    except Exception as e:
        log.warning("get_setting(%s) failed: %s", key, e)
        return default


def get_portfolio() -> list[dict]:
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id, symbol, quantity, buy_price, buy_date, notes "
                "FROM portfolio ORDER BY symbol"
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.warning("get_portfolio failed: %s", e)
        return []


def add_holding(symbol: str, quantity: float, buy_price: float,
                buy_date: str | None = None, notes: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO portfolio(symbol, quantity, buy_price, buy_date, notes) "
            "VALUES(?, ?, ?, ?, ?)",
            (symbol, quantity, buy_price, buy_date, notes),
        )


def remove_holding(holding_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM portfolio WHERE id = ?", (holding_id,))
