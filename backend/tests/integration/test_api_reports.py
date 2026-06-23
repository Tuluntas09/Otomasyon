"""API integration tests for Phase 7B report routes.

Uses FastAPI TestClient with dependency_overrides to inject an isolated
in-memory SQLite connection. Data is seeded through existing repos only —
no route internals, no raw SQL.

Covers:
  - Health route smoke test
  - Daily report: structure, metrics, alerts, journal filtering, compliance
  - Weekly report: structure, metrics, drawdown/volatility sections, journal
  - Error handling: invalid dates, missing params, week_start > report_date
  - Adapter/repo extension: get_journal_entries, get_by_date_range
  - Boundary: no forbidden imports in route modules, no write decorators
"""

import re
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app.api.app import app
from app.api.deps import get_conn
from app.core.models import Holding, PriceRecord
from app.data.adapters.base import DataAdapter
from app.data.adapters.sqlite_adapter import SQLiteDataAdapter
from app.data.persistence.db import get_connection, init_schema
from app.data.persistence.holdings_repo import HoldingsRepo
from app.data.persistence.journal_repo import JournalRepo
from app.data.persistence.prices_repo import PricesRepo
from app.core.exceptions import InvalidDateError
from app.journal.models import JournalEntry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn():
    """Isolated in-memory SQLite connection with schema initialised."""
    c = get_connection(":memory:")
    init_schema(c)
    yield c
    c.close()


@pytest.fixture()
def client(conn):
    """TestClient with the DB dependency overridden to use the test connection."""

    def override_get_conn():
        try:
            yield conn
        finally:
            pass  # test fixture owns the connection lifecycle

    app.dependency_overrides[get_conn] = override_get_conn
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_simple_portfolio(conn, report_date: str = "2024-01-15") -> None:
    """One holding (AAPL) with a price on report_date. MV = 2000.00 USD."""
    HoldingsRepo(conn).insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    PricesRepo(conn).upsert(
        PriceRecord(ticker="AAPL", price_date=report_date, close_price=200.0)
    )


def _seed_concentrated_portfolio(conn, report_date: str = "2024-01-15") -> None:
    """AAPL dominates at >25% weight — CONC-001 must fire."""
    HoldingsRepo(conn).insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    HoldingsRepo(conn).insert(Holding(ticker="MSFT", quantity=1.0, cost_basis=300.0))
    PricesRepo(conn).upsert(
        PriceRecord(ticker="AAPL", price_date=report_date, close_price=200.0)
    )
    PricesRepo(conn).upsert(
        PriceRecord(ticker="MSFT", price_date=report_date, close_price=200.0)
    )
    # AAPL weight = 2000/2200 ≈ 90.9% >> 25% ceiling


def _seed_diversified_portfolio(conn, report_date: str = "2024-01-15") -> None:
    """Four equal-weight positions at exactly 25% — CONC-001 must NOT fire."""
    tickers = ["AAPL", "MSFT", "GOOG", "AMZN"]
    repo = HoldingsRepo(conn)
    prepo = PricesRepo(conn)
    for t in tickers:
        repo.insert(Holding(ticker=t, quantity=10.0, cost_basis=100.0))
        prepo.upsert(PriceRecord(ticker=t, price_date=report_date, close_price=100.0))
    # Each weight = 1000/4000 = 25.0% exactly — strict GT does not fire


def _seed_weekly_prices(conn) -> None:
    """Multi-day prices for AAPL to enable drawdown + volatility computation."""
    repo = PricesRepo(conn)
    prices = [
        ("2024-01-08", 180.0),
        ("2024-01-09", 185.0),
        ("2024-01-10", 190.0),
        ("2024-01-11", 188.0),
        ("2024-01-12", 195.0),
        ("2024-01-15", 200.0),
    ]
    for d, p in prices:
        repo.upsert(PriceRecord(ticker="AAPL", price_date=d, close_price=p))


# ---------------------------------------------------------------------------
# 1. Health route
# ---------------------------------------------------------------------------


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# 2. Daily report — structure
# ---------------------------------------------------------------------------


def test_daily_report_returns_200(conn, client):
    _seed_simple_portfolio(conn)
    resp = client.get("/reports/daily?report_date=2024-01-15")
    assert resp.status_code == 200


def test_daily_report_type(conn, client):
    _seed_simple_portfolio(conn)
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    assert data["report_type"] == "daily"


def test_daily_report_date_field(conn, client):
    _seed_simple_portfolio(conn)
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    assert data["report_date"] == "2024-01-15"


def test_daily_report_has_non_empty_sections(conn, client):
    _seed_simple_portfolio(conn)
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    assert isinstance(data["sections"], list)
    assert len(data["sections"]) > 0
    for s in data["sections"]:
        assert "label" in s
        assert "body" in s


def test_daily_report_has_journal_entries_field(conn, client):
    _seed_simple_portfolio(conn)
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    assert "journal_entries" in data
    assert isinstance(data["journal_entries"], list)


# ---------------------------------------------------------------------------
# 3. Daily report — metrics content
# ---------------------------------------------------------------------------


def test_daily_report_known_portfolio_value_in_sections(conn, client):
    """Known portfolio: AAPL 10 shares @ $200 = $2000 total market value."""
    _seed_simple_portfolio(conn)
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    all_bodies = " ".join(s["body"] for s in data["sections"])
    assert "2000.00 USD" in all_bodies


def test_daily_report_known_position_weight_in_sections(conn, client):
    """Single position must show 100.00% weight."""
    _seed_simple_portfolio(conn)
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    all_bodies = " ".join(s["body"] for s in data["sections"])
    assert "100.00%" in all_bodies


# ---------------------------------------------------------------------------
# 4. Daily report — alert behavior
# ---------------------------------------------------------------------------


def test_daily_report_concentration_alert_fires(conn, client):
    """Concentrated portfolio: CONC-001 fires (AAPL weight ~90.9% > 25%)."""
    _seed_concentrated_portfolio(conn)
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    alert_section = next(
        s for s in data["sections"] if s["label"] == "Alert Summary"
    )
    assert "Fired" in alert_section["body"]
    assert "CONC-001" in alert_section["body"]


def test_daily_report_concentration_alert_informational_when_diversified(conn, client):
    """Diversified portfolio: CONC-001 within threshold — shows Within threshold."""
    _seed_diversified_portfolio(conn)
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    alert_section = next(
        s for s in data["sections"] if s["label"] == "Alert Summary"
    )
    assert "Within threshold" in alert_section["body"]
    assert "CONC-001" in alert_section["body"]


def test_daily_report_concentration_at_exact_threshold_not_fired(conn, client):
    """Exact 25% weight (strict GT) — CONC-001 must not fire."""
    _seed_diversified_portfolio(conn)  # 4 × 25% = exactly threshold
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    alert_section = next(
        s for s in data["sections"] if s["label"] == "Alert Summary"
    )
    # No CONC-001 entry should say "Fired" for the diversified case
    conc_lines = [
        line for line in alert_section["body"].splitlines() if "CONC-001" in line
    ]
    for line in conc_lines:
        assert "Fired" not in line


# ---------------------------------------------------------------------------
# 5. Daily report — journal filtering
# ---------------------------------------------------------------------------


def test_daily_report_journal_filtering_by_date(conn, client):
    """Only journal entries with entry_date == report_date are returned."""
    jr = JournalRepo(conn)
    jr.add_entry(
        entry_date="2024-01-15",
        action_taken="Reviewed portfolio on the 15th",
        reasoning="Quarterly check",
    )
    jr.add_entry(
        entry_date="2024-01-10",
        action_taken="Reviewed portfolio on the 10th",
        reasoning="Mid-week check",
    )
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    entries = data["journal_entries"]
    assert len(entries) == 1
    assert entries[0]["entry_date"] == "2024-01-15"
    assert entries[0]["action_taken"] == "Reviewed portfolio on the 15th"


def test_daily_report_journal_empty_when_no_match(conn, client):
    """No entries for the report date → journal_entries == []."""
    JournalRepo(conn).add_entry(
        entry_date="2024-01-10",
        action_taken="Some past action",
        reasoning="Past reasoning",
    )
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    assert data["journal_entries"] == []


def test_daily_report_journal_forbidden_words_returned_verbatim(conn, client):
    """User-authored text containing forbidden terms is returned verbatim, not rewritten."""
    JournalRepo(conn).add_entry(
        entry_date="2024-01-15",
        action_taken="I decided to buy and then sell some shares",
        reasoning="Testing verbatim return of user text with profit and loss words",
    )
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    entries = data["journal_entries"]
    assert len(entries) == 1
    assert entries[0]["action_taken"] == "I decided to buy and then sell some shares"
    assert "profit and loss" in entries[0]["reasoning"]


# ---------------------------------------------------------------------------
# 6. Daily report — compliance of system sections
# ---------------------------------------------------------------------------


_FORBIDDEN_IN_SYSTEM = re.compile(
    r"\b(buy|sell|hold|recommend|suggest|profit|guaranteed|opportunity"
    r"|target price|price prediction)\b",
    re.IGNORECASE,
)


def test_daily_report_system_sections_no_forbidden_language(conn, client):
    """All system-generated sections pass compliance — no forbidden terms."""
    _seed_simple_portfolio(conn)
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    for section in data["sections"]:
        assert not _FORBIDDEN_IN_SYSTEM.search(section["label"]), (
            f"Forbidden term in label: {section['label']!r}"
        )
        assert not _FORBIDDEN_IN_SYSTEM.search(section["body"]), (
            f"Forbidden term in body: {section['body']!r}"
        )


# ---------------------------------------------------------------------------
# 7. Weekly report — structure
# ---------------------------------------------------------------------------


def test_weekly_report_returns_200(conn, client):
    HoldingsRepo(conn).insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    _seed_weekly_prices(conn)
    resp = client.get(
        "/reports/weekly?week_start=2024-01-08&report_date=2024-01-15"
    )
    assert resp.status_code == 200


def test_weekly_report_type(conn, client):
    HoldingsRepo(conn).insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    _seed_weekly_prices(conn)
    data = client.get(
        "/reports/weekly?week_start=2024-01-08&report_date=2024-01-15"
    ).json()
    assert data["report_type"] == "weekly"


def test_weekly_report_week_start_field(conn, client):
    HoldingsRepo(conn).insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    _seed_weekly_prices(conn)
    data = client.get(
        "/reports/weekly?week_start=2024-01-08&report_date=2024-01-15"
    ).json()
    assert data["week_start"] == "2024-01-08"


def test_weekly_report_date_field(conn, client):
    HoldingsRepo(conn).insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    _seed_weekly_prices(conn)
    data = client.get(
        "/reports/weekly?week_start=2024-01-08&report_date=2024-01-15"
    ).json()
    assert data["report_date"] == "2024-01-15"


def test_weekly_report_has_drawdown_section(conn, client):
    HoldingsRepo(conn).insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    _seed_weekly_prices(conn)
    data = client.get(
        "/reports/weekly?week_start=2024-01-08&report_date=2024-01-15"
    ).json()
    labels = [s["label"] for s in data["sections"]]
    assert "Drawdown Summary" in labels


def test_weekly_report_has_volatility_section(conn, client):
    HoldingsRepo(conn).insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    _seed_weekly_prices(conn)
    data = client.get(
        "/reports/weekly?week_start=2024-01-08&report_date=2024-01-15"
    ).json()
    labels = [s["label"] for s in data["sections"]]
    assert "Volatility Proxy Summary" in labels


# ---------------------------------------------------------------------------
# 8. Weekly report — metrics content and journal filtering
# ---------------------------------------------------------------------------


def test_weekly_report_portfolio_value_in_sections(conn, client):
    HoldingsRepo(conn).insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    _seed_weekly_prices(conn)
    data = client.get(
        "/reports/weekly?week_start=2024-01-08&report_date=2024-01-15"
    ).json()
    all_bodies = " ".join(s["body"] for s in data["sections"])
    assert "2000.00 USD" in all_bodies  # 10 × 200.0 at latest price


def test_weekly_report_journal_filtering_by_date_range(conn, client):
    """Only entries within week_start <= entry_date <= report_date are returned."""
    HoldingsRepo(conn).insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    _seed_weekly_prices(conn)
    jr = JournalRepo(conn)
    jr.add_entry(
        entry_date="2024-01-08",
        action_taken="Action on week start",
        reasoning="Week start reasoning",
    )
    jr.add_entry(
        entry_date="2024-01-12",
        action_taken="Mid-week action",
        reasoning="Mid-week reasoning",
    )
    jr.add_entry(
        entry_date="2024-01-05",
        action_taken="Action before week",
        reasoning="Before week reasoning",
    )
    jr.add_entry(
        entry_date="2024-01-20",
        action_taken="Action after week",
        reasoning="After week reasoning",
    )
    data = client.get(
        "/reports/weekly?week_start=2024-01-08&report_date=2024-01-15"
    ).json()
    entries = data["journal_entries"]
    entry_dates = {e["entry_date"] for e in entries}
    assert entry_dates == {"2024-01-08", "2024-01-12"}
    assert "2024-01-05" not in entry_dates
    assert "2024-01-20" not in entry_dates


def test_weekly_report_same_date_week_start_and_report_date(conn, client):
    """week_start == report_date is valid (same-day weekly report)."""
    _seed_simple_portfolio(conn, report_date="2024-01-15")
    resp = client.get(
        "/reports/weekly?week_start=2024-01-15&report_date=2024-01-15"
    )
    assert resp.status_code == 200
    assert resp.json()["report_type"] == "weekly"


# ---------------------------------------------------------------------------
# 9. Edge cases — empty and unpriced portfolios
# ---------------------------------------------------------------------------


def test_daily_report_empty_portfolio(client):
    """Zero holdings produces a valid report with no crash."""
    resp = client.get("/reports/daily?report_date=2024-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_type"] == "daily"
    all_bodies = " ".join(s["body"] for s in data["sections"])
    assert "No positions recorded" in all_bodies


def test_daily_report_all_unpriced_portfolio(conn, client):
    """Holdings with no prices produce a valid report."""
    HoldingsRepo(conn).insert(Holding(ticker="AAPL", quantity=10.0, cost_basis=150.0))
    resp = client.get("/reports/daily?report_date=2024-01-15")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_type"] == "daily"
    all_bodies = " ".join(s["body"] for s in data["sections"])
    assert "Price data not available" in all_bodies


def test_daily_report_no_journal_entries_returns_empty_list(conn, client):
    _seed_simple_portfolio(conn)
    data = client.get("/reports/daily?report_date=2024-01-15").json()
    assert data["journal_entries"] == []


# ---------------------------------------------------------------------------
# 10. Error handling
# ---------------------------------------------------------------------------


def test_daily_missing_report_date_returns_422(client):
    resp = client.get("/reports/daily")
    assert resp.status_code == 422


def test_daily_invalid_report_date_returns_422(client):
    resp = client.get("/reports/daily?report_date=not-a-date")
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error"] == "invalid_date"
    assert detail["field"] == "report_date"
    assert detail["value"] == "not-a-date"


def test_weekly_missing_week_start_returns_422(client):
    resp = client.get("/reports/weekly?report_date=2024-01-15")
    assert resp.status_code == 422


def test_weekly_missing_report_date_returns_422(client):
    resp = client.get("/reports/weekly?week_start=2024-01-08")
    assert resp.status_code == 422


def test_weekly_invalid_week_start_returns_422(client):
    resp = client.get(
        "/reports/weekly?week_start=bad-date&report_date=2024-01-15"
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error"] == "invalid_date"
    assert detail["field"] == "week_start"


def test_weekly_invalid_report_date_returns_422(client):
    resp = client.get(
        "/reports/weekly?week_start=2024-01-08&report_date=bad-date"
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error"] == "invalid_date"
    assert detail["field"] == "report_date"


def test_weekly_week_start_after_report_date_returns_422(client):
    resp = client.get(
        "/reports/weekly?week_start=2024-01-20&report_date=2024-01-15"
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error"] == "invalid_date_range"
    assert detail["field"] == "week_start"


# ---------------------------------------------------------------------------
# 11. DataAdapter and JournalRepo extension
# ---------------------------------------------------------------------------


def test_data_adapter_has_get_journal_entries():
    """DataAdapter ABC declares get_journal_entries as an abstract method."""
    import inspect
    assert "get_journal_entries" in {
        name for name, _ in inspect.getmembers(DataAdapter)
    }


def test_sqlite_adapter_get_journal_entries_returns_entries_in_range(conn):
    """SQLiteDataAdapter.get_journal_entries filters by date range correctly."""
    jr = JournalRepo(conn)
    jr.add_entry(
        entry_date="2024-01-10",
        action_taken="In range",
        reasoning="Should appear",
    )
    jr.add_entry(
        entry_date="2024-01-20",
        action_taken="Out of range",
        reasoning="Should not appear",
    )
    adapter = SQLiteDataAdapter(conn)
    results = adapter.get_journal_entries("2024-01-08", "2024-01-15")
    assert len(results) == 1
    assert results[0].action_taken == "In range"


def test_sqlite_adapter_get_journal_entries_returns_empty_when_none_match(conn):
    adapter = SQLiteDataAdapter(conn)
    results = adapter.get_journal_entries("2024-01-01", "2024-01-07")
    assert results == []


def test_journal_repo_get_by_date_range_invalid_date_from(conn):
    repo = JournalRepo(conn)
    with pytest.raises(InvalidDateError):
        repo.get_by_date_range("not-a-date", "2024-01-15")


def test_journal_repo_get_by_date_range_invalid_date_to(conn):
    repo = JournalRepo(conn)
    with pytest.raises(InvalidDateError):
        repo.get_by_date_range("2024-01-08", "not-a-date")


def test_journal_repo_get_by_date_range_date_from_after_date_to(conn):
    repo = JournalRepo(conn)
    with pytest.raises(InvalidDateError):
        repo.get_by_date_range("2024-01-15", "2024-01-08")


def test_journal_repo_get_by_date_range_ordering(conn):
    """Results ordered by entry_date DESC, created_at DESC."""
    repo = JournalRepo(conn)
    repo.add_entry(
        entry_date="2024-01-10",
        action_taken="Earlier date",
        reasoning="First inserted",
    )
    repo.add_entry(
        entry_date="2024-01-12",
        action_taken="Later date",
        reasoning="Second inserted",
    )
    results = repo.get_by_date_range("2024-01-08", "2024-01-15")
    assert len(results) == 2
    assert results[0].entry_date == "2024-01-12"
    assert results[1].entry_date == "2024-01-10"


def test_journal_repo_get_by_date_range_same_date(conn):
    """date_from == date_to returns only that exact date."""
    repo = JournalRepo(conn)
    repo.add_entry(
        entry_date="2024-01-15",
        action_taken="On target date",
        reasoning="Should appear",
    )
    repo.add_entry(
        entry_date="2024-01-14",
        action_taken="Day before",
        reasoning="Should not appear",
    )
    results = repo.get_by_date_range("2024-01-15", "2024-01-15")
    assert len(results) == 1
    assert results[0].action_taken == "On target date"


# ---------------------------------------------------------------------------
# 12. Boundary checks — routes do not import forbidden modules
# ---------------------------------------------------------------------------

_ROUTES_DIR = Path(__file__).parent.parent.parent / "app" / "api" / "routes"
_API_DIR = Path(__file__).parent.parent.parent / "app" / "api"


def _read_routes_source() -> str:
    sources = []
    for f in _ROUTES_DIR.glob("*.py"):
        sources.append(f.read_text(encoding="utf-8"))
    return "\n".join(sources)


def test_routes_do_not_import_persistence_repos_directly():
    source = _read_routes_source()
    forbidden = [
        "from app.data.persistence",
        "import HoldingsRepo",
        "import PricesRepo",
        "import WatchlistRepo",
        "import JournalRepo",
    ]
    for pattern in forbidden:
        assert pattern not in source, (
            f"Route files must not import persistence repos directly. "
            f"Found: {pattern!r}"
        )


def test_routes_do_not_import_sqlite3():
    source = _read_routes_source()
    assert "import sqlite3" not in source


def test_routes_do_not_import_external_http_clients():
    source = _read_routes_source()
    for lib in ("import requests", "import httpx", "import aiohttp"):
        assert lib not in source, f"Routes must not import {lib!r}"


def test_routes_have_no_write_decorators():
    source = _read_routes_source()
    for method in (".post(", ".put(", ".patch(", ".delete("):
        assert method not in source, f"Routes must not define write endpoint {method!r}"


def test_main_does_not_call_uvicorn_run():
    main_path = Path(__file__).parent.parent.parent / "main.py"
    source = main_path.read_text(encoding="utf-8")
    assert "uvicorn.run" not in source


def test_pyproject_has_fastapi_runtime_dependency():
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    source = pyproject_path.read_text(encoding="utf-8")
    assert "fastapi" in source


def test_pyproject_has_dev_optional_dependency():
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    source = pyproject_path.read_text(encoding="utf-8")
    assert "[project.optional-dependencies]" in source
    assert "dev" in source
