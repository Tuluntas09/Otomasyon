"""Repository for the user's watchlist (write-side of the data layer)."""

import sqlite3

from app.core.exceptions import DuplicateTickerError
from app.core.models import WatchlistEntry


class WatchlistRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add(self, entry: WatchlistEntry) -> None:
        """Add *entry* to the watchlist. Raises DuplicateTickerError if already present."""
        try:
            self._conn.execute(
                "INSERT INTO watchlist (ticker) VALUES (?)", (entry.ticker,)
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            msg = str(exc).upper()
            if "UNIQUE" in msg or "PRIMARY" in msg:
                raise DuplicateTickerError(
                    f"Ticker {entry.ticker!r} already exists in watchlist."
                ) from exc
            raise

    def remove(self, ticker: str) -> None:
        """Remove *ticker* from the watchlist (no-op if not present)."""
        self._conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))
        self._conn.commit()

    def get_all(self) -> list[WatchlistEntry]:
        """Return all watchlist entries as domain objects."""
        rows = self._conn.execute(
            "SELECT ticker FROM watchlist ORDER BY ticker"
        ).fetchall()
        return [WatchlistEntry(ticker=r["ticker"]) for r in rows]
