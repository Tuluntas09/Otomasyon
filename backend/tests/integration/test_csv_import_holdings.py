"""Integration tests: holdings CSV import → in-memory SQLite → read back."""

import io

import pytest

from app.core.exceptions import CsvImportError, DuplicateTickerError
from app.data.adapters.csv_importer import import_holdings_csv
from app.data.persistence.db import get_connection, init_schema
from app.data.persistence.holdings_repo import HoldingsRepo


@pytest.fixture()
def conn():
    c = get_connection(":memory:")
    init_schema(c)
    yield c
    c.close()


def test_holdings_csv_round_trip(conn):
    csv_text = (
        "ticker,quantity,cost_basis,currency\n"
        "AAPL,10,150.0,USD\n"
        "MSFT,5,300.0,USD\n"
    )
    result = import_holdings_csv(io.StringIO(csv_text), conn)
    assert result.imported_count == 2
    holdings = HoldingsRepo(conn).get_all()
    assert len(holdings) == 2
    assert {h.ticker for h in holdings} == {"AAPL", "MSFT"}


def test_holdings_round_trip_values_preserved(conn):
    csv_text = "ticker,quantity,cost_basis,currency\nBRK.B,2,350.50,USD\n"
    import_holdings_csv(io.StringIO(csv_text), conn)
    holdings = HoldingsRepo(conn).get_all()
    h = holdings[0]
    assert h.ticker == "BRK.B"
    assert h.quantity == 2.0
    assert h.cost_basis == 350.50
    assert h.currency == "USD"


def test_holdings_csv_duplicate_already_in_db_causes_csv_import_error(conn):
    csv_text = "ticker,quantity,cost_basis,currency\nAAPL,10,150.0,USD\n"
    import_holdings_csv(io.StringIO(csv_text), conn)
    with pytest.raises(CsvImportError) as exc_info:
        import_holdings_csv(io.StringIO(csv_text), conn)
    assert any(isinstance(e.error, DuplicateTickerError) for e in exc_info.value.errors)


def test_holdings_csv_duplicate_in_db_leaves_db_unchanged(conn):
    first_csv = "ticker,quantity,cost_basis,currency\nAAPL,10,150.0,USD\n"
    import_holdings_csv(io.StringIO(first_csv), conn)
    second_csv = (
        "ticker,quantity,cost_basis,currency\n"
        "MSFT,5,300.0,USD\n"
        "AAPL,99,999.0,USD\n"
    )
    with pytest.raises(CsvImportError):
        import_holdings_csv(io.StringIO(second_csv), conn)
    holdings = HoldingsRepo(conn).get_all()
    assert len(holdings) == 1
    assert holdings[0].ticker == "AAPL"
    assert holdings[0].quantity == 10.0


def test_holdings_invalid_row_leaves_db_empty(conn):
    csv_text = (
        "ticker,quantity,cost_basis,currency\n"
        "AAPL,10,150.0,USD\n"
        "MSFT,-5,300.0,USD\n"
    )
    with pytest.raises(CsvImportError):
        import_holdings_csv(io.StringIO(csv_text), conn)
    assert HoldingsRepo(conn).get_all() == []


def test_holdings_csv_no_partial_writes_on_error(conn):
    csv_text = (
        "ticker,quantity,cost_basis,currency\n"
        "AAPL,10,150.0,USD\n"
        "MSFT,5,300.0,USD\n"
        "aapl_invalid,1,100.0,USD\n"
    )
    with pytest.raises(CsvImportError):
        import_holdings_csv(io.StringIO(csv_text), conn)
    assert HoldingsRepo(conn).get_all() == []


def test_holdings_csv_single_holding(conn):
    csv_text = "ticker,quantity,cost_basis,currency\nTSLA,1,200.0,USD\n"
    result = import_holdings_csv(io.StringIO(csv_text), conn)
    assert result.imported_count == 1


def test_holdings_csv_zero_cost_basis_allowed(conn):
    csv_text = "ticker,quantity,cost_basis,currency\nFREE,1,0.0,USD\n"
    result = import_holdings_csv(io.StringIO(csv_text), conn)
    assert result.imported_count == 1
    assert HoldingsRepo(conn).get_all()[0].cost_basis == 0.0
