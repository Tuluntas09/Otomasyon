"""Concrete DataAdapter implementation backed by SQLite repositories.

SQLiteDataAdapter is the read boundary consumed by metrics, alerts, and reports.
It satisfies the DataAdapter ABC from base.py and delegates to the Phase 2 repos.
"""

import sqlite3

from app.core.models import Holding, PriceRecord, WatchlistEntry
from app.data.adapters.base import DataAdapter
from app.data.persistence.holdings_repo import HoldingsRepo
from app.data.persistence.journal_repo import JournalRepo
from app.data.persistence.prices_repo import PricesRepo
from app.data.persistence.watchlist_repo import WatchlistRepo
from app.journal.models import JournalEntry


class SQLiteDataAdapter(DataAdapter):
    """DataAdapter backed by the Phase 2–6 SQLite repositories."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._holdings = HoldingsRepo(conn)
        self._watchlist = WatchlistRepo(conn)
        self._prices = PricesRepo(conn)
        self._journal = JournalRepo(conn)

    def get_holdings(self) -> list[Holding]:
        return self._holdings.get_all()

    def get_watchlist(self) -> list[WatchlistEntry]:
        return self._watchlist.get_all()

    def get_prices(self, ticker: str | None = None) -> list[PriceRecord]:
        if ticker is not None:
            return self._prices.get_for_ticker(ticker)
        return self._prices.get_all()

    def get_journal_entries(self, date_from: str, date_to: str) -> list[JournalEntry]:
        return self._journal.get_by_date_range(date_from, date_to)
