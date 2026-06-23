"""Integration tests for SQLiteDataAdapter — verifies DataAdapter contract."""

import pytest

from app.core.models import Holding, PriceRecord, WatchlistEntry
from app.data.adapters.base import DataAdapter
from app.data.adapters.sqlite_adapter import SQLiteDataAdapter
from app.data.persistence.db import get_connection, init_schema
from app.data.persistence.holdings_repo import HoldingsRepo
from app.data.persistence.prices_repo import PricesRepo
from app.data.persistence.watchlist_repo import WatchlistRepo


@pytest.fixture()
def conn():
    c = get_connection(":memory:")
    init_schema(c)
    yield c
    c.close()


@pytest.fixture()
def adapter(conn):
    return SQLiteDataAdapter(conn)


def test_data_adapter_is_abstract():
    with pytest.raises(TypeError):
        DataAdapter()  # type: ignore[abstract]


def test_sqlite_adapter_satisfies_contract(adapter):
    assert isinstance(adapter, DataAdapter)


def test_get_holdings_empty(adapter):
    assert adapter.get_holdings() == []


def test_get_holdings_returns_domain_objects(conn, adapter):
    HoldingsRepo(conn).insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    result = adapter.get_holdings()
    assert len(result) == 1
    assert isinstance(result[0], Holding)
    assert result[0].ticker == "AAPL"


def test_get_holdings_multiple(conn, adapter):
    repo = HoldingsRepo(conn)
    repo.insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    repo.insert(Holding(ticker="MSFT", quantity=5.0, cost_basis=300.0))
    result = adapter.get_holdings()
    assert {h.ticker for h in result} == {"AAPL", "MSFT"}


def test_get_watchlist_empty(adapter):
    assert adapter.get_watchlist() == []


def test_get_watchlist_returns_domain_objects(conn, adapter):
    WatchlistRepo(conn).add(WatchlistEntry(ticker="TSLA"))
    result = adapter.get_watchlist()
    assert len(result) == 1
    assert isinstance(result[0], WatchlistEntry)
    assert result[0].ticker == "TSLA"


def test_get_prices_empty(adapter):
    assert adapter.get_prices() == []


def test_get_prices_returns_domain_objects(conn, adapter):
    PricesRepo(conn).upsert(PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0))
    result = adapter.get_prices()
    assert len(result) == 1
    assert isinstance(result[0], PriceRecord)


def test_get_prices_all(conn, adapter):
    repo = PricesRepo(conn)
    repo.upsert(PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0))
    repo.upsert(PriceRecord(ticker="MSFT", price_date="2024-01-15", close_price=400.0))
    assert len(adapter.get_prices()) == 2


def test_get_prices_filtered_by_ticker(conn, adapter):
    repo = PricesRepo(conn)
    repo.upsert(PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0))
    repo.upsert(PriceRecord(ticker="MSFT", price_date="2024-01-15", close_price=400.0))
    result = adapter.get_prices(ticker="AAPL")
    assert len(result) == 1
    assert result[0].ticker == "AAPL"


def test_get_prices_unknown_ticker_returns_empty(adapter):
    assert adapter.get_prices(ticker="UNKNOWN") == []


def test_adapter_reflects_writes(conn, adapter):
    assert adapter.get_holdings() == []
    HoldingsRepo(conn).insert(Holding(ticker="NVDA", quantity=2.0, cost_basis=500.0))
    assert len(adapter.get_holdings()) == 1
