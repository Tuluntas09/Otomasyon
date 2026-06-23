"""Phase 2 unit tests — replaced from placeholder stubs."""

from app.core.exceptions import CurrencyError, NegativeQuantityError
from app.core.models import Holding
import pytest


def test_holding_model_valid_construction() -> None:
    """A valid Holding with positive quantity and USD currency constructs without error."""
    h = Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0, currency="USD")
    assert h.ticker == "AAPL"
    assert h.quantity == 10.0
    assert h.cost_basis == 150.0
    assert h.currency == "USD"


def test_negative_quantity_raises_error() -> None:
    """Negative quantity input raises NegativeQuantityError."""
    with pytest.raises(NegativeQuantityError):
        Holding(ticker="AAPL", quantity=-1.0, cost_basis=100.0)


def test_non_usd_currency_raises_error() -> None:
    """Non-USD currency input raises CurrencyError."""
    with pytest.raises(CurrencyError):
        Holding(ticker="AAPL", quantity=1.0, cost_basis=100.0, currency="EUR")
