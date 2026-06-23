"""Repository for portfolio holdings (write-side of the data layer)."""

import sqlite3

from app.core.exceptions import DuplicateTickerError
from app.core.models import Holding


class HoldingsRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def insert(self, holding: Holding) -> None:
        """Persist *holding*. Raises DuplicateTickerError if the ticker already exists."""
        try:
            self._conn.execute(
                "INSERT INTO holdings (ticker, quantity, cost_basis, currency) VALUES (?, ?, ?, ?)",
                (holding.ticker, holding.quantity, holding.cost_basis, holding.currency),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            msg = str(exc).upper()
            if "UNIQUE" in msg or "PRIMARY" in msg:
                raise DuplicateTickerError(
                    f"Ticker {holding.ticker!r} already exists in holdings."
                ) from exc
            raise

    def get_all(self) -> list[Holding]:
        """Return all holdings as domain objects."""
        rows = self._conn.execute(
            "SELECT ticker, quantity, cost_basis, currency FROM holdings ORDER BY ticker"
        ).fetchall()
        return [
            Holding(
                ticker=r["ticker"],
                quantity=r["quantity"],
                cost_basis=r["cost_basis"],
                currency=r["currency"],
            )
            for r in rows
        ]

    def delete(self, ticker: str) -> None:
        """Remove the holding with *ticker* (no-op if not present)."""
        self._conn.execute("DELETE FROM holdings WHERE ticker = ?", (ticker,))
        self._conn.commit()
