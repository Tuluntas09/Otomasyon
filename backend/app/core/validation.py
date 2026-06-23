"""Domain validation helpers.

Each function validates one invariant and returns the cleaned value on success,
or raises a typed exception on failure. No I/O; no side effects.
"""

import re
from datetime import date as _date

from app.core.exceptions import (
    CurrencyError,
    InvalidCostBasisError,
    InvalidDateError,
    InvalidTickerError,
    NegativePriceError,
    NegativeQuantityError,
)

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")


def validate_ticker(ticker: str) -> str:
    """Return *ticker* unchanged if it matches the allowed format.

    Allowed: 1–10 chars, starts with an uppercase letter, remaining chars are
    uppercase letters, digits, dots, or hyphens.
    """
    if not isinstance(ticker, str) or not _TICKER_RE.match(ticker):
        raise InvalidTickerError(
            f"Invalid ticker {ticker!r}. Expected 1-10 uppercase alphanumeric chars "
            "(letters, digits, '.', '-') starting with a letter."
        )
    return ticker


def validate_currency_usd(currency: str) -> str:
    """Return *currency* unchanged if it is 'USD'; raise CurrencyError otherwise."""
    if currency != "USD":
        raise CurrencyError(
            f"Currency must be 'USD' in v0.1; got {currency!r}."
        )
    return currency


def validate_positive_quantity(quantity: float) -> float:
    """Return *quantity* unchanged if it is strictly positive; raise NegativeQuantityError otherwise."""
    if quantity <= 0:
        raise NegativeQuantityError(
            f"Quantity must be > 0 (no zero or short positions); got {quantity}."
        )
    return quantity


def validate_non_negative_cost_basis(cost_basis: float) -> float:
    """Return *cost_basis* unchanged if it is >= 0; raise InvalidCostBasisError otherwise."""
    if cost_basis < 0:
        raise InvalidCostBasisError(
            f"Cost basis must be >= 0; got {cost_basis}."
        )
    return cost_basis


def validate_positive_close_price(close_price: float) -> float:
    """Return *close_price* unchanged if it is strictly positive; raise NegativePriceError otherwise."""
    if close_price <= 0:
        raise NegativePriceError(
            f"Close price must be > 0; got {close_price}."
        )
    return close_price


def validate_iso_date(date_str: str) -> str:
    """Return *date_str* unchanged if it is a valid ISO 8601 date (YYYY-MM-DD)."""
    try:
        _date.fromisoformat(date_str)
    except (ValueError, TypeError, AttributeError):
        raise InvalidDateError(
            f"Date must be in YYYY-MM-DD format; got {date_str!r}."
        )
    return date_str
