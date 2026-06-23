"""Integration tests: prices CSV import → in-memory SQLite → read back."""

import io

import pytest

from app.core.exceptions import MissingColumnError
from app.data.adapters.csv_importer import import_prices_csv
from app.data.persistence.db import get_connection, init_schema
from app.data.persistence.prices_repo import PricesRepo


@pytest.fixture()
def conn():
    c = get_connection(":memory:")
    init_schema(c)
    yield c
    c.close()


def test_prices_csv_round_trip(conn):
    csv_text = (
        "ticker,date,close,currency\n"
        "AAPL,2024-01-15,185.0,USD\n"
        "AAPL,2024-01-16,188.0,USD\n"
        "MSFT,2024-01-15,400.0,USD\n"
    )
    result = import_prices_csv(io.StringIO(csv_text), conn)
    assert result.imported_count == 3
    assert result.errors == []
    records = PricesRepo(conn).get_all()
    assert len(records) == 3


def test_prices_round_trip_values_preserved(conn):
    csv_text = "ticker,date,close,currency\nAAPL,2024-01-15,185.75,USD\n"
    import_prices_csv(io.StringIO(csv_text), conn)
    records = PricesRepo(conn).get_for_ticker("AAPL")
    assert records[0].ticker == "AAPL"
    assert records[0].price_date == "2024-01-15"
    assert records[0].close_price == 185.75
    assert records[0].currency == "USD"


def test_prices_csv_reimport_is_idempotent(conn):
    csv_text = (
        "ticker,date,close,currency\n"
        "AAPL,2024-01-15,185.0,USD\n"
        "MSFT,2024-01-15,400.0,USD\n"
    )
    result1 = import_prices_csv(io.StringIO(csv_text), conn)
    result2 = import_prices_csv(io.StringIO(csv_text), conn)
    assert result1.imported_count == 2
    assert result2.imported_count == 2
    assert len(PricesRepo(conn).get_all()) == 2


def test_prices_csv_upsert_updates_close_price(conn):
    csv_text_v1 = "ticker,date,close,currency\nAAPL,2024-01-15,185.0,USD\n"
    csv_text_v2 = "ticker,date,close,currency\nAAPL,2024-01-15,190.0,USD\n"
    import_prices_csv(io.StringIO(csv_text_v1), conn)
    import_prices_csv(io.StringIO(csv_text_v2), conn)
    records = PricesRepo(conn).get_for_ticker("AAPL")
    assert len(records) == 1
    assert records[0].close_price == 190.0


def test_prices_csv_partial_import_valid_rows_written(conn):
    csv_text = (
        "ticker,date,close,currency\n"
        "AAPL,2024-01-15,185.0,USD\n"
        "MSFT,not-a-date,400.0,USD\n"
        "GOOG,2024-01-15,150.0,USD\n"
    )
    result = import_prices_csv(io.StringIO(csv_text), conn)
    assert result.imported_count == 2
    assert len(result.errors) == 1
    records = PricesRepo(conn).get_all()
    assert {r.ticker for r in records} == {"AAPL", "GOOG"}


def test_prices_csv_partial_import_invalid_rows_in_errors(conn):
    csv_text = (
        "ticker,date,close,currency\n"
        "AAPL,2024-01-15,185.0,USD\n"
        "MSFT,2024-01-15,0.0,USD\n"
    )
    result = import_prices_csv(io.StringIO(csv_text), conn)
    assert result.imported_count == 1
    assert len(result.errors) == 1
    assert result.errors[0].row_number == 3


def test_prices_csv_with_date_gaps(conn):
    csv_text = (
        "ticker,date,close,currency\n"
        "AAPL,2024-01-02,182.0,USD\n"
        "AAPL,2024-01-05,185.0,USD\n"
        "AAPL,2024-01-10,188.0,USD\n"
    )
    result = import_prices_csv(io.StringIO(csv_text), conn)
    assert result.imported_count == 3
    records = PricesRepo(conn).get_for_ticker("AAPL")
    assert [r.price_date for r in records] == ["2024-01-02", "2024-01-05", "2024-01-10"]


def test_prices_csv_multiple_tickers(conn):
    csv_text = (
        "ticker,date,close,currency\n"
        "AAPL,2024-01-15,185.0,USD\n"
        "MSFT,2024-01-15,400.0,USD\n"
        "GOOG,2024-01-15,150.0,USD\n"
    )
    import_prices_csv(io.StringIO(csv_text), conn)
    aapl = PricesRepo(conn).get_for_ticker("AAPL")
    msft = PricesRepo(conn).get_for_ticker("MSFT")
    assert len(aapl) == 1 and aapl[0].close_price == 185.0
    assert len(msft) == 1 and msft[0].close_price == 400.0


def test_prices_csv_missing_column_raises(conn):
    csv_text = "ticker,date,currency\nAAPL,2024-01-15,USD\n"
    with pytest.raises(MissingColumnError):
        import_prices_csv(io.StringIO(csv_text), conn)


def test_prices_csv_all_rows_bad_no_writes(conn):
    csv_text = (
        "ticker,date,close,currency\n"
        "AAPL,bad-date,185.0,USD\n"
        "MSFT,2024-01-15,0.0,USD\n"
    )
    result = import_prices_csv(io.StringIO(csv_text), conn)
    assert result.imported_count == 0
    assert len(result.errors) == 2
    assert PricesRepo(conn).get_all() == []
