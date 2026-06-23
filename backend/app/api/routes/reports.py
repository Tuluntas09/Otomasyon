"""Read-only report routes.

GET /reports/daily?report_date=YYYY-MM-DD
GET /reports/weekly?week_start=YYYY-MM-DD&report_date=YYYY-MM-DD

Orchestration sequence (D-062):
  connection → init_schema (done in dep) → SQLiteDataAdapter
  → holdings/prices/journal entries → metrics → alerts → report builder
  → dataclasses.asdict() → JSON response.

Route boundary rules (approved Phase 7B plan):
  - No persistence repo imports (HoldingsRepo, JournalRepo, etc.).
  - No sqlite3 import.
  - No raw SQL.
  - No external HTTP clients.
  - No POST/PUT/PATCH/DELETE decorators.
  - All data access through SQLiteDataAdapter.
"""

import dataclasses
from datetime import date as _date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.alerts.results import AlertConfig
from app.alerts.rules import evaluate_alerts
from app.api.deps import get_conn
from app.data.adapters.sqlite_adapter import SQLiteDataAdapter
from app.metrics.engine import (
    compute_drawdown,
    compute_portfolio_snapshot,
    compute_volatility_proxy,
)
from app.metrics.quality import compute_data_quality
from app.reports.builder import build_daily_report, build_weekly_report

router = APIRouter()

_DATE_DESC = "ISO-8601 date string (YYYY-MM-DD)"


def _parse_date(value: str, field: str) -> _date:
    """Parse an ISO-8601 date string; raise HTTP 422 with structured detail on failure."""
    try:
        return _date.fromisoformat(value)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_date",
                "field": field,
                "value": value,
                "message": f"{field} must be a valid ISO-8601 date (YYYY-MM-DD).",
            },
        )


@router.get("/daily")
def get_daily_report(
    report_date: str = Query(..., description=_DATE_DESC),
    conn=Depends(get_conn),
) -> dict:
    """Return a serialized DailyReport for the given report_date.

    Computes drawdown and volatility even though build_daily_report does not
    consume them directly — evaluate_alerts requires them for DD-001 and VOL-001.
    """
    _parse_date(report_date, "report_date")

    adapter = SQLiteDataAdapter(conn)
    holdings = adapter.get_holdings()
    prices = adapter.get_prices()
    journal_entries = adapter.get_journal_entries(
        date_from=report_date, date_to=report_date
    )

    snapshot = compute_portfolio_snapshot(holdings, prices)
    drawdown = compute_drawdown(holdings, prices)
    volatility = compute_volatility_proxy(holdings, prices)
    alert_results = evaluate_alerts(snapshot, drawdown, volatility, AlertConfig())
    data_quality = compute_data_quality(holdings, prices, report_date)
    report = build_daily_report(
        report_date, snapshot, alert_results, journal_entries, data_quality
    )
    return dataclasses.asdict(report)


@router.get("/weekly")
def get_weekly_report(
    week_start: str = Query(..., description=_DATE_DESC),
    report_date: str = Query(..., description=_DATE_DESC),
    conn=Depends(get_conn),
) -> dict:
    """Return a serialized WeeklyReport for the given week_start / report_date range."""
    ws = _parse_date(week_start, "week_start")
    rd = _parse_date(report_date, "report_date")
    if ws > rd:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_date_range",
                "field": "week_start",
                "message": "week_start must be on or before report_date.",
            },
        )

    adapter = SQLiteDataAdapter(conn)
    holdings = adapter.get_holdings()
    prices = adapter.get_prices()
    journal_entries = adapter.get_journal_entries(
        date_from=week_start, date_to=report_date
    )

    snapshot = compute_portfolio_snapshot(holdings, prices)
    drawdown = compute_drawdown(holdings, prices)
    volatility = compute_volatility_proxy(holdings, prices)
    alert_results = evaluate_alerts(snapshot, drawdown, volatility, AlertConfig())
    data_quality = compute_data_quality(holdings, prices, report_date)
    report = build_weekly_report(
        report_date, week_start, snapshot, drawdown, volatility,
        alert_results, journal_entries, data_quality,
    )
    return dataclasses.asdict(report)
