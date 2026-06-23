"""SQLite connection factory and schema initialisation.

DB file location is read from the OTOMASYON_DB_PATH environment variable,
defaulting to ./data/otomasyon.db (relative to the process working directory).

Pass ":memory:" as db_path in tests to use an isolated in-memory database.
init_schema() is idempotent: safe to call on every startup.
"""

import os
import sqlite3
from pathlib import Path

_DEFAULT_DB_PATH = Path("data") / "otomasyon.db"

_DDL = """
CREATE TABLE IF NOT EXISTS holdings (
    ticker      TEXT PRIMARY KEY,
    quantity    REAL NOT NULL CHECK(quantity > 0),
    cost_basis  REAL NOT NULL CHECK(cost_basis >= 0),
    currency    TEXT NOT NULL DEFAULT 'USD' CHECK(currency = 'USD')
);

CREATE TABLE IF NOT EXISTS watchlist (
    ticker TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS prices (
    ticker       TEXT NOT NULL,
    price_date   TEXT NOT NULL,
    close_price  REAL NOT NULL CHECK(close_price > 0),
    currency     TEXT NOT NULL DEFAULT 'USD' CHECK(currency = 'USD'),
    PRIMARY KEY (ticker, price_date)
);

CREATE TABLE IF NOT EXISTS journal_entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date   TEXT NOT NULL,
    ticker       TEXT,
    action_taken TEXT NOT NULL,
    reasoning    TEXT NOT NULL,
    hypothesis   TEXT,
    review_date  TEXT,
    tags         TEXT,
    created_at   TEXT NOT NULL
);
"""


def get_db_path() -> str:
    return os.environ.get("OTOMASYON_DB_PATH", str(_DEFAULT_DB_PATH))


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return an open sqlite3 connection with row_factory and foreign-key support."""
    path = db_path if db_path is not None else get_db_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create all tables if they do not already exist (idempotent)."""
    conn.executescript(_DDL)
    conn.commit()
