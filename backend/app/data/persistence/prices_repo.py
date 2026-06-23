"""Repository for end-of-day price records (write-side of the data layer).

Duplicate (ticker, price_date) rows are handled by upsert so that re-ingesting
the same CSV is idempotent (D-022).
"""

import sqlite3

from app.core.models import PriceRecord


class PricesRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def upsert(self, record: PriceRecord) -> None:
        """Insert or update a price record. Idempotent on (ticker, price_date)."""
        self._conn.execute(
            """
            INSERT INTO prices (ticker, price_date, close_price, currency)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ticker, price_date) DO UPDATE SET
                close_price = excluded.close_price,
                currency    = excluded.currency
            """,
            (record.ticker, record.price_date, record.close_price, record.currency),
        )
        self._conn.commit()

    def get_all(self) -> list[PriceRecord]:
        """Return all price records as domain objects, ordered by ticker then date."""
        rows = self._conn.execute(
            "SELECT ticker, price_date, close_price, currency FROM prices ORDER BY ticker, price_date"
        ).fetchall()
        return [
            PriceRecord(
                ticker=r["ticker"],
                price_date=r["price_date"],
                close_price=r["close_price"],
                currency=r["currency"],
            )
            for r in rows
        ]

    def get_for_ticker(self, ticker: str) -> list[PriceRecord]:
        """Return all price records for *ticker*, ordered by date ascending."""
        rows = self._conn.execute(
            "SELECT ticker, price_date, close_price, currency FROM prices "
            "WHERE ticker = ? ORDER BY price_date",
            (ticker,),
        ).fetchall()
        return [
            PriceRecord(
                ticker=r["ticker"],
                price_date=r["price_date"],
                close_price=r["close_price"],
                currency=r["currency"],
            )
            for r in rows
        ]
