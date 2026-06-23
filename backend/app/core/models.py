"""Domain model dataclasses for the Otomasyon portfolio instrument.

All models are immutable (frozen=True) and self-validating: construction raises
a typed exception rather than storing an invalid value.
"""

from dataclasses import dataclass

from app.core.validation import (
    validate_currency_usd,
    validate_iso_date,
    validate_non_negative_cost_basis,
    validate_positive_close_price,
    validate_positive_quantity,
    validate_ticker,
)


@dataclass(frozen=True)
class Holding:
    """A single portfolio position.

    Invariants enforced on construction:
    - ticker: valid format
    - quantity: > 0
    - cost_basis: >= 0
    - currency: must be 'USD'
    """

    ticker: str
    quantity: float
    cost_basis: float
    currency: str = "USD"

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", validate_ticker(self.ticker))
        object.__setattr__(self, "currency", validate_currency_usd(self.currency))
        object.__setattr__(self, "quantity", validate_positive_quantity(self.quantity))
        object.__setattr__(self, "cost_basis", validate_non_negative_cost_basis(self.cost_basis))


@dataclass(frozen=True)
class WatchlistEntry:
    """A ticker on the user's watchlist."""

    ticker: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", validate_ticker(self.ticker))


@dataclass(frozen=True)
class PriceRecord:
    """An end-of-day closing price for one ticker on one date.

    Invariants enforced on construction:
    - ticker: valid format
    - price_date: ISO 8601 (YYYY-MM-DD)
    - close_price: > 0
    - currency: must be 'USD'
    """

    ticker: str
    price_date: str
    close_price: float
    currency: str = "USD"

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", validate_ticker(self.ticker))
        object.__setattr__(self, "price_date", validate_iso_date(self.price_date))
        object.__setattr__(self, "currency", validate_currency_usd(self.currency))
        object.__setattr__(self, "close_price", validate_positive_close_price(self.close_price))
