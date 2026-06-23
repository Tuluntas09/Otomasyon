"""Integration tests for PricesRepo against an in-memory SQLite database."""

import pytest

from app.core.models import PriceRecord
from app.data.persistence.db import get_connection, init_schema
from app.data.persistence.prices_repo import PricesRepo


@pytest.fixture()
def repo():
    conn = get_connection(":memory:")
    init_schema(conn)
    yield PricesRepo(conn)
    conn.close()


def test_upsert_and_get_all(repo):
    r = PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0)
    repo.upsert(r)
    result = repo.get_all()
    assert len(result) == 1
    assert result[0] == r


def test_get_all_empty(repo):
    assert repo.get_all() == []


def test_upsert_is_idempotent_same_price(repo):
    r = PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0)
    repo.upsert(r)
    repo.upsert(r)
    assert len(repo.get_all()) == 1


def test_upsert_updates_price_on_duplicate_date(repo):
    r1 = PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0)
    r2 = PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=190.0)
    repo.upsert(r1)
    repo.upsert(r2)
    records = repo.get_for_ticker("AAPL")
    assert len(records) == 1
    assert records[0].close_price == 190.0


def test_different_dates_are_separate_records(repo):
    repo.upsert(PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0))
    repo.upsert(PriceRecord(ticker="AAPL", price_date="2024-01-16", close_price=188.0))
    records = repo.get_for_ticker("AAPL")
    assert len(records) == 2


def test_different_tickers_same_date_are_separate(repo):
    repo.upsert(PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0))
    repo.upsert(PriceRecord(ticker="MSFT", price_date="2024-01-15", close_price=400.0))
    assert len(repo.get_all()) == 2


def test_get_for_ticker_filters_correctly(repo):
    repo.upsert(PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0))
    repo.upsert(PriceRecord(ticker="MSFT", price_date="2024-01-15", close_price=400.0))
    aapl_records = repo.get_for_ticker("AAPL")
    assert len(aapl_records) == 1
    assert aapl_records[0].ticker == "AAPL"


def test_get_for_ticker_returns_empty_for_unknown(repo):
    assert repo.get_for_ticker("UNKNOWN") == []


def test_get_for_ticker_ordered_by_date(repo):
    repo.upsert(PriceRecord(ticker="AAPL", price_date="2024-01-17", close_price=190.0))
    repo.upsert(PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0))
    repo.upsert(PriceRecord(ticker="AAPL", price_date="2024-01-16", close_price=188.0))
    records = repo.get_for_ticker("AAPL")
    dates = [r.price_date for r in records]
    assert dates == sorted(dates)


def test_returns_domain_objects(repo):
    repo.upsert(PriceRecord(ticker="AAPL", price_date="2024-01-15", close_price=185.0))
    result = repo.get_all()
    assert isinstance(result[0], PriceRecord)
