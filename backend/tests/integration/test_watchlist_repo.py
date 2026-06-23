"""Integration tests for WatchlistRepo against an in-memory SQLite database."""

import pytest

from app.core.exceptions import DuplicateTickerError
from app.core.models import WatchlistEntry
from app.data.persistence.db import get_connection, init_schema
from app.data.persistence.watchlist_repo import WatchlistRepo


@pytest.fixture()
def repo():
    conn = get_connection(":memory:")
    init_schema(conn)
    yield WatchlistRepo(conn)
    conn.close()


def test_add_and_get_all(repo):
    entry = WatchlistEntry(ticker="AAPL")
    repo.add(entry)
    result = repo.get_all()
    assert len(result) == 1
    assert result[0] == entry


def test_get_all_empty(repo):
    assert repo.get_all() == []


def test_add_multiple(repo):
    tickers = ["AAPL", "MSFT", "GOOG"]
    for t in tickers:
        repo.add(WatchlistEntry(ticker=t))
    result = repo.get_all()
    assert {e.ticker for e in result} == set(tickers)


def test_duplicate_ticker_raises(repo):
    repo.add(WatchlistEntry(ticker="TSLA"))
    with pytest.raises(DuplicateTickerError):
        repo.add(WatchlistEntry(ticker="TSLA"))


def test_duplicate_does_not_corrupt_db(repo):
    repo.add(WatchlistEntry(ticker="TSLA"))
    try:
        repo.add(WatchlistEntry(ticker="TSLA"))
    except DuplicateTickerError:
        pass
    assert len(repo.get_all()) == 1


def test_remove_entry(repo):
    repo.add(WatchlistEntry(ticker="NVDA"))
    repo.remove("NVDA")
    assert repo.get_all() == []


def test_remove_nonexistent_is_noop(repo):
    repo.remove("NONE")
    assert repo.get_all() == []


def test_returns_domain_objects(repo):
    repo.add(WatchlistEntry(ticker="AMZN"))
    result = repo.get_all()
    assert isinstance(result[0], WatchlistEntry)
