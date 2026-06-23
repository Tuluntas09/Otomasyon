"""Phase 3 unit tests — replaced from placeholder stubs."""

import io

import pytest

from app.core.exceptions import CsvImportError, CurrencyError, DuplicateTickerError
from app.data.adapters.csv_importer import import_holdings_csv
from app.data.persistence.db import get_connection, init_schema


@pytest.fixture()
def mem_conn():
    conn = get_connection(":memory:")
    init_schema(conn)
    yield conn
    conn.close()


def test_valid_holdings_csv_parses_correctly(mem_conn) -> None:
    """A well-formed holdings CSV is parsed into Holding objects without error."""
    csv_text = "ticker,quantity,cost_basis,currency\nAAPL,10,150.0,USD\nMSFT,5,300.0,USD\n"
    result = import_holdings_csv(io.StringIO(csv_text), mem_conn)
    assert result.imported_count == 2
    assert result.errors == []


def test_csv_with_duplicate_ticker_raises_error(mem_conn) -> None:
    """A holdings CSV containing a duplicate ticker raises CsvImportError wrapping DuplicateTickerError."""
    csv_text = "ticker,quantity,cost_basis,currency\nAAPL,10,150.0,USD\nAAPL,5,200.0,USD\n"
    with pytest.raises(CsvImportError) as exc_info:
        import_holdings_csv(io.StringIO(csv_text), mem_conn)
    assert any(isinstance(e.error, DuplicateTickerError) for e in exc_info.value.errors)


def test_csv_with_non_usd_currency_raises_error(mem_conn) -> None:
    """A holdings CSV row with non-USD currency raises CsvImportError wrapping CurrencyError."""
    csv_text = "ticker,quantity,cost_basis,currency\nAAPL,10,150.0,EUR\n"
    with pytest.raises(CsvImportError) as exc_info:
        import_holdings_csv(io.StringIO(csv_text), mem_conn)
    assert any(isinstance(e.error, CurrencyError) for e in exc_info.value.errors)
