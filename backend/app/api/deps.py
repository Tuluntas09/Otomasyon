"""FastAPI dependency for the SQLite database connection.

Opens one connection per request using the D-023 DB path policy:
  OTOMASYON_DB_PATH environment variable, default ./data/otomasyon.db.

Calls init_schema(conn) so tables always exist before the route runs.
Guarantees conn.close() via try/finally.

This module may import sqlite3 and os. Route modules must not.
"""

import sqlite3
from collections.abc import Generator

from app.data.persistence.db import get_connection, init_schema


def get_conn() -> Generator[sqlite3.Connection, None, None]:
    """Yield an initialised SQLite connection; close it after the request."""
    conn = get_connection()
    init_schema(conn)
    try:
        yield conn
    finally:
        conn.close()
