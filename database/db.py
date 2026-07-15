"""SQLite persistence layer — per-user watchlist & portfolio.

Data is scoped by user_email ('local' when running without login).
init_db() migrates older single-user databases automatically.
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


def _migrate(conn: sqlite3.Connection) -> None:
    """Upgrade pre-multi-user databases (adds user_email, defaults to 'local')."""
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
            _migrate(conn)
            conn.executescript(_SCHEMA)
    except Exception as e:
        log.error("init_db failed: %s", e)
        raise


# ---- settings (global) -------------------------------------------------------

def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def get_setting(key: str, default: str | None = None) -> str | None:
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    except Exception as e:
        log.warning("get_setting(%s) failed: %s", key, e)
        return default


# ---- watchlist (per user) ----------------------------------------------------

def get_watchlist(user: str = "local") -> list[str]:
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT symbol FROM watchlist WHERE user_email = ? ORDER BY added_at",
                (user,),
            ).fetchall()
        return [r["symbol"] for r in rows]
    except Exception as e:
        log.warning("get_watchlist failed: %s", e)
        return []


def add_to_watchlist(symbol: str, user: str = "local") -> None:
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO watchlist(user_email, symbol) VALUES(?, ?)",
                     (user, symbol))


def remove_from_watchlist(symbol: str, user: str = "local") -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM watchlist WHERE user_email = ? AND symbol = ?",
                     (user, symbol))


# ---- portfolio (per user) ------------------------------------------------------

def get_portfolio(user: str = "local") -> list[dict]:
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id, symbol, quantity, buy_price, buy_date, notes "
                "FROM portfolio WHERE user_email = ? ORDER BY symbol",
                (user,),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.warning("get_portfolio failed: %s", e)
        return []


def add_holding(symbol: str, quantity: float, buy_price: float,
                buy_date: str | None = None, notes: str = "",
                user: str = "local") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO portfolio(user_email, symbol, quantity, buy_price, buy_date, notes) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (user, symbol, quantity, buy_price, buy_date, notes),
        )


def remove_holding(holding_id: int, user: str = "local") -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM portfolio WHERE id = ? AND user_email = ?",
                     (holding_id, user))
