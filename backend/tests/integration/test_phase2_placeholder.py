"""Phase 2 integration tests — replaced from placeholder stubs."""

import pytest

from app.core.exceptions import DuplicateTickerError
from app.core.models import Holding, PriceRecord
from app.data.persistence.db import get_connection, init_schema
from app.data.persistence.holdings_repo import HoldingsRepo
from app.data.persistence.prices_repo import PricesRepo


@pytest.fixture()
def conn():
    c = get_connection(":memory:")
    init_schema(c)
    yield c
    c.close()


def test_holding_round_trips_through_repository(conn) -> None:
    """A Holding inserted via HoldingsRepo is returned correctly by get_all()."""
    repo = HoldingsRepo(conn)
    h = Holding(ticker="MSFT", quantity=5.0, cost_basis=300.0)
    repo.insert(h)
    result = repo.get_all()
    assert len(result) == 1
    assert result[0] == h


def test_duplicate_ticker_rejected_by_repository(conn) -> None:
    """Inserting a duplicate ticker via HoldingsRepo raises DuplicateTickerError."""
    repo = HoldingsRepo(conn)
    h = Holding(ticker="TSLA", quantity=2.0, cost_basis=200.0)
    repo.insert(h)
    with pytest.raises(DuplicateTickerError):
        repo.insert(Holding(ticker="TSLA", quantity=3.0, cost_basis=250.0))


def test_price_record_upsert_is_idempotent(conn) -> None:
    """Re-inserting a price record for the same (ticker, date) updates without error."""
    repo = PricesRepo(conn)
    r1 = PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0)
    r2 = PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=190.0)
    repo.upsert(r1)
    repo.upsert(r2)
    records = repo.get_for_ticker("AAPL")
    assert len(records) == 1
    assert records[0].close_price == 190.0
