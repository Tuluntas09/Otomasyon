"""DataAdapter abstract boundary.

All modules outside the data layer (metrics, alerts, reports, api) read data
exclusively through this interface. Nothing outside data/ touches the database
directly.
"""

from abc import ABC, abstractmethod

from app.core.models import Holding, PriceRecord, WatchlistEntry
from app.journal.models import JournalEntry


class DataAdapter(ABC):
    """Read contract consumed by metrics, alerts, reports, and API routes."""

    @abstractmethod
    def get_holdings(self) -> list[Holding]:
        """Return all current holdings in the portfolio."""

    @abstractmethod
    def get_watchlist(self) -> list[WatchlistEntry]:
        """Return all tickers on the watchlist."""

    @abstractmethod
    def get_prices(self, ticker: str | None = None) -> list[PriceRecord]:
        """Return price records, optionally filtered to a single ticker."""

    @abstractmethod
    def get_journal_entries(self, date_from: str, date_to: str) -> list[JournalEntry]:
        """Return journal entries whose entry_date falls within [date_from, date_to].

        Both dates are ISO-8601 strings (YYYY-MM-DD). date_from must be <= date_to.
        Returns entries ordered by entry_date DESC, created_at DESC.
        Returns [] if none match.
        User-authored text fields are never compliance-scanned here.
        """
