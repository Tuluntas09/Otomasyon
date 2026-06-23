"""Unit tests for app.data.adapters.csv_importer — parsing and validation in isolation.

Tests use io.StringIO for CSV content and an in-memory SQLite connection so that
the DB duplicate pre-check in import_holdings_csv / import_watchlist_csv works without
touching any real file. No file I/O occurs.
"""

import io

import pytest

from app.core.exceptions import (
    CsvImportError,
    CurrencyError,
    DuplicateTickerError,
    InvalidCostBasisError,
    InvalidDateError,
    InvalidTickerError,
    MissingColumnError,
    NegativePriceError,
    NegativeQuantityError,
    ValidationError,
)
from app.data.adapters.csv_importer import (
    ImportResult,
    RowImportError,
    import_holdings_csv,
    import_prices_csv,
    import_watchlist_csv,
)
from app.data.persistence.db import get_connection, init_schema


@pytest.fixture()
def conn():
    c = get_connection(":memory:")
    init_schema(c)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Holdings CSV — unit-level tests
# ---------------------------------------------------------------------------


class TestImportHoldingsCsv:
    def test_valid_csv(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\nAAPL,10,150.0,USD\nMSFT,5,300.0,USD\n"
        result = import_holdings_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 2
        assert result.errors == []

    def test_empty_body_with_header(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\n"
        result = import_holdings_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 0
        assert result.errors == []

    def test_empty_file_no_header_raises(self, conn):
        with pytest.raises(MissingColumnError):
            import_holdings_csv(io.StringIO(""), conn)

    def test_missing_column_raises(self, conn):
        csv_text = "ticker,quantity,currency\nAAPL,10,USD\n"
        with pytest.raises(MissingColumnError) as exc_info:
            import_holdings_csv(io.StringIO(csv_text), conn)
        assert "cost_basis" in str(exc_info.value)

    def test_non_usd_currency_raises(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\nAAPL,10,150.0,EUR\n"
        with pytest.raises(CsvImportError) as exc_info:
            import_holdings_csv(io.StringIO(csv_text), conn)
        assert any(isinstance(e.error, CurrencyError) for e in exc_info.value.errors)

    def test_invalid_ticker_raises(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\naapl,10,150.0,USD\n"
        with pytest.raises(CsvImportError) as exc_info:
            import_holdings_csv(io.StringIO(csv_text), conn)
        assert any(isinstance(e.error, InvalidTickerError) for e in exc_info.value.errors)

    def test_negative_quantity_raises(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\nAAPL,-5,150.0,USD\n"
        with pytest.raises(CsvImportError) as exc_info:
            import_holdings_csv(io.StringIO(csv_text), conn)
        assert any(isinstance(e.error, NegativeQuantityError) for e in exc_info.value.errors)

    def test_zero_quantity_raises(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\nAAPL,0,150.0,USD\n"
        with pytest.raises(CsvImportError) as exc_info:
            import_holdings_csv(io.StringIO(csv_text), conn)
        assert any(isinstance(e.error, NegativeQuantityError) for e in exc_info.value.errors)

    def test_negative_cost_basis_raises(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\nAAPL,10,-1.0,USD\n"
        with pytest.raises(CsvImportError) as exc_info:
            import_holdings_csv(io.StringIO(csv_text), conn)
        assert any(isinstance(e.error, InvalidCostBasisError) for e in exc_info.value.errors)

    def test_non_numeric_quantity_raises(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\nAAPL,abc,150.0,USD\n"
        with pytest.raises(CsvImportError) as exc_info:
            import_holdings_csv(io.StringIO(csv_text), conn)
        assert any(isinstance(e.error, ValidationError) for e in exc_info.value.errors)

    def test_duplicate_ticker_within_csv_raises(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\nAAPL,10,150.0,USD\nAAPL,5,200.0,USD\n"
        with pytest.raises(CsvImportError) as exc_info:
            import_holdings_csv(io.StringIO(csv_text), conn)
        assert any(isinstance(e.error, DuplicateTickerError) for e in exc_info.value.errors)

    def test_extra_columns_ignored(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency,notes,row_id\nAAPL,10,150.0,USD,my note,1\n"
        result = import_holdings_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 1

    def test_whitespace_stripped_from_values(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\n  AAPL , 10 , 150.0 , USD \n"
        result = import_holdings_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 1

    def test_zero_cost_basis_allowed(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\nFREE,1,0.0,USD\n"
        result = import_holdings_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 1

    def test_multiple_errors_collected(self, conn):
        csv_text = (
            "ticker,quantity,cost_basis,currency\n"
            "aapl,10,150.0,USD\n"
            "MSFT,10,150.0,EUR\n"
        )
        with pytest.raises(CsvImportError) as exc_info:
            import_holdings_csv(io.StringIO(csv_text), conn)
        assert len(exc_info.value.errors) == 2

    def test_row_import_error_contains_row_number(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\nAAPL,10,150.0,EUR\n"
        with pytest.raises(CsvImportError) as exc_info:
            import_holdings_csv(io.StringIO(csv_text), conn)
        assert exc_info.value.errors[0].row_number == 2

    def test_row_import_error_contains_raw_row(self, conn):
        csv_text = "ticker,quantity,cost_basis,currency\nAAPL,10,150.0,EUR\n"
        with pytest.raises(CsvImportError) as exc_info:
            import_holdings_csv(io.StringIO(csv_text), conn)
        raw = exc_info.value.errors[0].raw_row
        assert raw["ticker"] == "AAPL"
        assert raw["currency"] == "EUR"


# ---------------------------------------------------------------------------
# Watchlist CSV — unit-level tests
# ---------------------------------------------------------------------------


class TestImportWatchlistCsv:
    def test_valid_csv(self, conn):
        csv_text = "ticker\nAAPL\nMSFT\nGOOG\n"
        result = import_watchlist_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 3
        assert result.errors == []

    def test_empty_body_with_header(self, conn):
        csv_text = "ticker\n"
        result = import_watchlist_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 0

    def test_empty_file_no_header_raises(self, conn):
        with pytest.raises(MissingColumnError):
            import_watchlist_csv(io.StringIO(""), conn)

    def test_missing_column_raises(self, conn):
        csv_text = "symbol\nAAPL\n"
        with pytest.raises(MissingColumnError):
            import_watchlist_csv(io.StringIO(csv_text), conn)

    def test_invalid_ticker_raises(self, conn):
        csv_text = "ticker\naapl\n"
        with pytest.raises(CsvImportError) as exc_info:
            import_watchlist_csv(io.StringIO(csv_text), conn)
        assert any(isinstance(e.error, InvalidTickerError) for e in exc_info.value.errors)

    def test_duplicate_ticker_within_csv_raises(self, conn):
        csv_text = "ticker\nAAPL\nAAPL\n"
        with pytest.raises(CsvImportError) as exc_info:
            import_watchlist_csv(io.StringIO(csv_text), conn)
        assert any(isinstance(e.error, DuplicateTickerError) for e in exc_info.value.errors)

    def test_extra_columns_ignored(self, conn):
        csv_text = "ticker,notes\nAAPL,watching closely\n"
        result = import_watchlist_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 1

    def test_whitespace_stripped(self, conn):
        csv_text = "ticker\n  TSLA \n"
        result = import_watchlist_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 1


# ---------------------------------------------------------------------------
# Prices CSV — unit-level tests
# ---------------------------------------------------------------------------


class TestImportPricesCsv:
    def test_valid_csv(self, conn):
        csv_text = (
            "ticker,date,close,currency\n"
            "AAPL,2024-01-15,185.0,USD\n"
            "MSFT,2024-01-15,400.0,USD\n"
        )
        result = import_prices_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 2
        assert result.errors == []

    def test_empty_body_with_header(self, conn):
        csv_text = "ticker,date,close,currency\n"
        result = import_prices_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 0
        assert result.errors == []

    def test_empty_file_no_header_raises(self, conn):
        with pytest.raises(MissingColumnError):
            import_prices_csv(io.StringIO(""), conn)

    def test_missing_column_raises(self, conn):
        csv_text = "ticker,date,currency\nAAPL,2024-01-15,USD\n"
        with pytest.raises(MissingColumnError) as exc_info:
            import_prices_csv(io.StringIO(csv_text), conn)
        assert "close" in str(exc_info.value)

    def test_invalid_row_collected_not_raised(self, conn):
        csv_text = (
            "ticker,date,close,currency\n"
            "AAPL,2024-01-15,185.0,USD\n"
            "MSFT,2024-01-15,not_a_number,USD\n"
        )
        result = import_prices_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 1
        assert len(result.errors) == 1

    def test_non_usd_row_collected(self, conn):
        csv_text = (
            "ticker,date,close,currency\n"
            "AAPL,2024-01-15,185.0,EUR\n"
            "MSFT,2024-01-15,400.0,USD\n"
        )
        result = import_prices_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 1
        assert len(result.errors) == 1
        assert isinstance(result.errors[0].error, CurrencyError)

    def test_zero_price_collected(self, conn):
        csv_text = "ticker,date,close,currency\nAAPL,2024-01-15,0.0,USD\n"
        result = import_prices_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 0
        assert isinstance(result.errors[0].error, NegativePriceError)

    def test_negative_price_collected(self, conn):
        csv_text = "ticker,date,close,currency\nAAPL,2024-01-15,-1.0,USD\n"
        result = import_prices_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 0
        assert isinstance(result.errors[0].error, NegativePriceError)

    def test_invalid_date_collected(self, conn):
        csv_text = "ticker,date,close,currency\nAAPL,not-a-date,185.0,USD\n"
        result = import_prices_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 0
        assert isinstance(result.errors[0].error, InvalidDateError)

    def test_all_rows_bad_returns_zero_imported(self, conn):
        csv_text = (
            "ticker,date,close,currency\n"
            "AAPL,bad-date,185.0,USD\n"
            "MSFT,2024-01-15,0.0,USD\n"
            "GOOG,2024-01-15,200.0,EUR\n"
        )
        result = import_prices_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 0
        assert len(result.errors) == 3

    def test_error_contains_row_number(self, conn):
        csv_text = (
            "ticker,date,close,currency\n"
            "AAPL,2024-01-15,185.0,USD\n"
            "MSFT,bad-date,400.0,USD\n"
        )
        result = import_prices_csv(io.StringIO(csv_text), conn)
        assert result.errors[0].row_number == 3

    def test_whitespace_stripped(self, conn):
        csv_text = "ticker,date,close,currency\n AAPL , 2024-01-15 , 185.0 , USD \n"
        result = import_prices_csv(io.StringIO(csv_text), conn)
        assert result.imported_count == 1
        assert result.errors == []
