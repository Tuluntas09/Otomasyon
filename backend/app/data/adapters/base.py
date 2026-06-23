"""DataAdapter abstract boundary.

All modules outside the data layer (metrics, alerts, reports, api) read data
exclusively through this interface. Nothing outside data/ touches the database
directly.
"""

from abc import ABC, abstractmethod

from app.core.models import Holding, PriceRecord, WatchlistEntry


class DataAdapter(ABC):
    """Read contract consumed by metrics, alerts, and reports."""

    @abstractmethod
    def get_holdings(self) -> list[Holding]:
        """Return all current holdings in the portfolio."""

    @abstractmethod
    def get_watchlist(self) -> list[WatchlistEntry]:
        """Return all tickers on the watchlist."""

    @abstractmethod
    def get_prices(self, ticker: str | None = None) -> list[PriceRecord]:
        """Return price records, optionally filtered to a single ticker."""
