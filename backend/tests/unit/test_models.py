"""Unit tests for app.core.models — construction, invariants, and immutability."""

import pytest

from app.core.exceptions import (
    CurrencyError,
    InvalidCostBasisError,
    InvalidDateError,
    InvalidTickerError,
    NegativePriceError,
    NegativeQuantityError,
)
from app.core.models import Holding, PriceRecord, WatchlistEntry


class TestHolding:
    def test_valid_construction(self):
        h = Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0, currency="USD")
        assert h.ticker == "AAPL"
        assert h.quantity == 10.0
        assert h.cost_basis == 150.0
        assert h.currency == "USD"

    def test_default_currency_is_usd(self):
        h = Holding(ticker="MSFT", quantity=1.0, cost_basis=300.0)
        assert h.currency == "USD"

    def test_zero_cost_basis_allowed(self):
        h = Holding(ticker="GOOG", quantity=1.0, cost_basis=0.0)
        assert h.cost_basis == 0.0

    def test_invalid_ticker_raises(self):
        with pytest.raises(InvalidTickerError):
            Holding(ticker="aapl", quantity=1.0, cost_basis=100.0)

    def test_negative_quantity_raises(self):
        with pytest.raises(NegativeQuantityError):
            Holding(ticker="AAPL", quantity=-1.0, cost_basis=100.0)

    def test_zero_quantity_raises(self):
        with pytest.raises(NegativeQuantityError):
            Holding(ticker="AAPL", quantity=0.0, cost_basis=100.0)

    def test_negative_cost_basis_raises(self):
        with pytest.raises(InvalidCostBasisError):
            Holding(ticker="AAPL", quantity=1.0, cost_basis=-0.01)

    def test_non_usd_raises(self):
        with pytest.raises(CurrencyError):
            Holding(ticker="AAPL", quantity=1.0, cost_basis=100.0, currency="EUR")

    def test_frozen(self):
        h = Holding(ticker="AAPL", quantity=1.0, cost_basis=100.0)
        with pytest.raises(Exception):
            h.quantity = 999.0  # type: ignore[misc]

    def test_equality(self):
        h1 = Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0)
        h2 = Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0)
        assert h1 == h2

    def test_ticker_with_dot(self):
        h = Holding(ticker="BRK.B", quantity=1.0, cost_basis=350.0)
        assert h.ticker == "BRK.B"


class TestWatchlistEntry:
    def test_valid_construction(self):
        w = WatchlistEntry(ticker="TSLA")
        assert w.ticker == "TSLA"

    def test_invalid_ticker_raises(self):
        with pytest.raises(InvalidTickerError):
            WatchlistEntry(ticker="")

    def test_lowercase_ticker_raises(self):
        with pytest.raises(InvalidTickerError):
            WatchlistEntry(ticker="tsla")

    def test_frozen(self):
        w = WatchlistEntry(ticker="TSLA")
        with pytest.raises(Exception):
            w.ticker = "AAPL"  # type: ignore[misc]


class TestPriceRecord:
    def test_valid_construction(self):
        p = PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0)
        assert p.ticker == "AAPL"
        assert p.price_date == "2024-01-15"
        assert p.close_price == 185.0
        assert p.currency == "USD"

    def test_default_currency_is_usd(self):
        p = PriceRecord(ticker="MSFT", price_date="2024-06-01", close_price=400.0)
        assert p.currency == "USD"

    def test_invalid_ticker_raises(self):
        with pytest.raises(InvalidTickerError):
            PriceRecord(ticker="", price_date="2024-01-01", close_price=100.0)

    def test_invalid_date_raises(self):
        with pytest.raises(InvalidDateError):
            PriceRecord(ticker="AAPL", price_date="not-a-date", close_price=185.0)

    def test_zero_price_raises(self):
        with pytest.raises(NegativePriceError):
            PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=0.0)

    def test_negative_price_raises(self):
        with pytest.raises(NegativePriceError):
            PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=-1.0)

    def test_non_usd_raises(self):
        with pytest.raises(CurrencyError):
            PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0, currency="GBP")

    def test_frozen(self):
        p = PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0)
        with pytest.raises(Exception):
            p.close_price = 999.0  # type: ignore[misc]
