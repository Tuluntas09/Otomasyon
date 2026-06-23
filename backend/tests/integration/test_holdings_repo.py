"""Integration tests for HoldingsRepo against an in-memory SQLite database."""

import pytest

from app.core.exceptions import DuplicateTickerError
from app.core.models import Holding
from app.data.persistence.db import get_connection, init_schema
from app.data.persistence.holdings_repo import HoldingsRepo


@pytest.fixture()
def repo():
    conn = get_connection(":memory:")
    init_schema(conn)
    yield HoldingsRepo(conn)
    conn.close()


def test_insert_and_get_all(repo):
    h = Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0)
    repo.insert(h)
    result = repo.get_all()
    assert len(result) == 1
    assert result[0] == h


def test_get_all_empty(repo):
    assert repo.get_all() == []


def test_get_all_multiple(repo):
    tickers = ["AAPL", "MSFT", "GOOG"]
    for t in tickers:
        repo.insert(Holding(ticker=t, quantity=1.0, cost_basis=100.0))
    result = repo.get_all()
    assert len(result) == 3
    assert {h.ticker for h in result} == set(tickers)


def test_duplicate_ticker_raises(repo):
    repo.insert(Holding(ticker="TSLA", quantity=2.0, cost_basis=200.0))
    with pytest.raises(DuplicateTickerError):
        repo.insert(Holding(ticker="TSLA", quantity=3.0, cost_basis=250.0))


def test_duplicate_does_not_corrupt_db(repo):
    repo.insert(Holding(ticker="TSLA", quantity=2.0, cost_basis=200.0))
    try:
        repo.insert(Holding(ticker="TSLA", quantity=3.0, cost_basis=250.0))
    except DuplicateTickerError:
        pass
    result = repo.get_all()
    assert len(result) == 1
    assert result[0].quantity == 2.0


def test_delete_removes_holding(repo):
    repo.insert(Holding(ticker="AAPL", quantity=5.0, cost_basis=100.0))
    repo.delete("AAPL")
    assert repo.get_all() == []


def test_delete_nonexistent_is_noop(repo):
    repo.delete("NONEXIST")
    assert repo.get_all() == []


def test_returns_domain_objects_not_raw_rows(repo):
    repo.insert(Holding(ticker="MSFT", quantity=1.0, cost_basis=300.0))
    result = repo.get_all()
    assert isinstance(result[0], Holding)


def test_cost_basis_zero_allowed(repo):
    h = Holding(ticker="FREE", quantity=1.0, cost_basis=0.0)
    repo.insert(h)
    result = repo.get_all()
    assert result[0].cost_basis == 0.0


def test_large_portfolio(repo):
    for i in range(100):
        ticker = f"T{i:03d}"
        repo.insert(Holding(ticker=ticker, quantity=float(i + 1), cost_basis=float(i) * 10))
    assert len(repo.get_all()) == 100
