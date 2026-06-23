"""Integration tests: watchlist CSV import → in-memory SQLite → read back."""

import io

import pytest

from app.core.exceptions import CsvImportError, DuplicateTickerError
from app.data.adapters.csv_importer import import_watchlist_csv
from app.data.persistence.db import get_connection, init_schema
from app.data.persistence.watchlist_repo import WatchlistRepo


@pytest.fixture()
def conn():
    c = get_connection(":memory:")
    init_schema(c)
    yield c
    c.close()


def test_watchlist_csv_round_trip(conn):
    csv_text = "ticker\nAAPL\nMSFT\nGOOG\n"
    result = import_watchlist_csv(io.StringIO(csv_text), conn)
    assert result.imported_count == 3
    entries = WatchlistRepo(conn).get_all()
    assert {e.ticker for e in entries} == {"AAPL", "MSFT", "GOOG"}


def test_watchlist_csv_duplicate_already_in_db_causes_csv_import_error(conn):
    import_watchlist_csv(io.StringIO("ticker\nAAPL\n"), conn)
    with pytest.raises(CsvImportError) as exc_info:
        import_watchlist_csv(io.StringIO("ticker\nAAPL\n"), conn)
    assert any(isinstance(e.error, DuplicateTickerError) for e in exc_info.value.errors)


def test_watchlist_csv_duplicate_in_db_leaves_db_unchanged(conn):
    import_watchlist_csv(io.StringIO("ticker\nAAPL\n"), conn)
    with pytest.raises(CsvImportError):
        import_watchlist_csv(io.StringIO("ticker\nMSFT\nAAPL\n"), conn)
    entries = WatchlistRepo(conn).get_all()
    assert len(entries) == 1
    assert entries[0].ticker == "AAPL"


def test_watchlist_invalid_row_leaves_db_empty(conn):
    csv_text = "ticker\nAAPL\naapl_bad\n"
    with pytest.raises(CsvImportError):
        import_watchlist_csv(io.StringIO(csv_text), conn)
    assert WatchlistRepo(conn).get_all() == []


def test_watchlist_no_partial_writes_on_error(conn):
    csv_text = "ticker\nAAPL\nMSFT\naapl_invalid\n"
    with pytest.raises(CsvImportError):
        import_watchlist_csv(io.StringIO(csv_text), conn)
    assert WatchlistRepo(conn).get_all() == []


def test_watchlist_csv_single_entry(conn):
    result = import_watchlist_csv(io.StringIO("ticker\nNVDA\n"), conn)
    assert result.imported_count == 1
