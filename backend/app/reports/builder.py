"""Pure report builder functions for daily and weekly reports.

No I/O, no DB access, no DataAdapter calls, no system clock.
All data arrives as function arguments.
Every system-generated ReportSection label and body passes through
check_compliance() before being stored. ComplianceViolationError propagates
to the caller — it is never caught or rewritten here.

User-authored JournalEntry fields are NOT passed through check_compliance().
They are carried verbatim in the report's journal_entries field.
"""

from datetime import date as _date

from app.alerts.results import AlertResult
from app.compliance.guard import check_compliance
from app.core.exceptions import InvalidDateError
from app.core.validation import validate_iso_date
from app.journal.models import JournalEntry
from app.metrics.quality import DataQualitySummary
from app.metrics.results import DrawdownResult, PortfolioSnapshot, VolatilityResult
from app.reports.models import DailyReport, ReportSection, WeeklyReport


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _make_section(label: str, body: str) -> ReportSection:
    """Compliance-check label and body, then return a frozen ReportSection.

    Raises ComplianceViolationError if either string contains a forbidden term.
    Never catches or rewrites compliance errors.
    """
    check_compliance(label)
    check_compliance(body)
    return ReportSection(label=label, body=body)


# ---------------------------------------------------------------------------
# Section builders — each returns one ReportSection
# ---------------------------------------------------------------------------


def _header_section(report_date: str, report_type: str) -> ReportSection:
    label = "Report"
    body = (
        f"Type: {report_type} | Date: {report_date} | "
        "This report describes computed facts only. "
        "Not investment advice. "
        "The user is solely responsible for their own financial decisions."
    )
    return _make_section(label, body)


def _coverage_section(snapshot: PortfolioSnapshot) -> ReportSection:
    label = "Data Coverage"
    total = len(snapshot.positions)
    priced = snapshot.priced_count
    unpriced = snapshot.unpriced_tickers

    if total == 0:
        body = "No positions recorded."
    elif not unpriced:
        body = f"{priced} of {total} position(s) priced. Data coverage: complete."
    elif priced == 0:
        tickers_str = ", ".join(unpriced)
        body = (
            f"0 of {total} position(s) priced. "
            f"Price data not available for all positions: {tickers_str}."
        )
    else:
        tickers_str = ", ".join(unpriced)
        body = (
            f"{priced} of {total} position(s) priced. "
            f"Price data not available for: {tickers_str}."
        )
    return _make_section(label, body)


def _snapshot_section(snapshot: PortfolioSnapshot) -> ReportSection:
    label = "Portfolio Snapshot"
    total = len(snapshot.positions)
    body = (
        f"Total market value: {snapshot.total_market_value:.2f} USD. "
        f"Priced positions: {snapshot.priced_count}. "
        f"Total positions: {total}."
    )
    return _make_section(label, body)


def _weights_section(snapshot: PortfolioSnapshot) -> ReportSection:
    label = "Position Weights"
    lines: list[str] = []
    for pos in snapshot.positions:
        if pos.weight is not None and pos.market_value is not None:
            if (
                pos.unrealised_change_usd is not None
                and pos.unrealised_change_pct is not None
            ):
                change_str = (
                    f", unrealised change in value:"
                    f" {pos.unrealised_change_usd:+.2f} USD"
                    f" ({pos.unrealised_change_pct:+.2%})"
                )
            else:
                change_str = ""
            lines.append(
                f"{pos.ticker}: weight {pos.weight:.2%},"
                f" market value {pos.market_value:.2f} USD{change_str}"
            )
        else:
            lines.append(f"{pos.ticker}: price data not available")
    if not lines:
        lines.append("No positions recorded.")
    return _make_section(label, "\n".join(lines))


def _alert_section(alert_results: list[AlertResult]) -> ReportSection:
    label = "Alert Summary"
    lines: list[str] = []
    for ar in alert_results:
        status = "Fired" if ar.fired else "Within threshold"
        lines.append(
            f"[{ar.rule_id}] {status}"
            f" | Severity: {ar.severity}"
            f" | Measured: {ar.metric_value:.6f}"
            f" | Threshold: {ar.threshold:.6f}"
            f" | {ar.explanation}"
        )
    if not lines:
        lines.append("No alert rules evaluated.")
    return _make_section(label, "\n".join(lines))


def _journal_note_section(journal_entries: list[JournalEntry]) -> ReportSection:
    label = "Journal Entries"
    if not journal_entries:
        body = "No entries recorded for this period."
    else:
        n = len(journal_entries)
        noun = "entry" if n == 1 else "entries"
        body = f"{n} user-authored {noun} recorded for this period."
    return _make_section(label, body)


def _method_section() -> ReportSection:
    label = "Method Note"
    body = (
        "Metrics are computed from supplied price and position data. "
        "Unavailable data is reported as not available. "
        "This report describes measured values only. "
        "No prescriptive statements are made by this report."
    )
    return _make_section(label, body)


def _disclaimer_section() -> ReportSection:
    label = "Disclaimer"
    body = (
        "Not investment advice. "
        "Past performance is not indicative of future results. "
        "The user is solely responsible for their own financial decisions."
    )
    return _make_section(label, body)


def _data_quality_section(data_quality: DataQualitySummary) -> ReportSection:
    label = "Data Quality Summary"
    total = data_quality.total_holding_count
    priced = data_quality.priced_holding_count
    ratio = data_quality.coverage_ratio
    report_date = data_quality.report_date

    if total == 0:
        body = "No positions recorded. Price history coverage: no data to compute."
    else:
        lines: list[str] = [
            f"Price history coverage as of {report_date}: "
            f"{priced} of {total} position(s) have at least one price record "
            f"on or before the report date. Coverage ratio: {ratio:.2%}."
        ]
        if data_quality.unpriced_tickers:
            tickers_str = ", ".join(data_quality.unpriced_tickers)
            lines.append(
                f"Positions without price data on or before {report_date}: {tickers_str}."
            )
        for tq in data_quality.ticker_quality:
            if tq.price_record_count == 0:
                lines.append(f"{tq.ticker}: no price records.")
            elif tq.days_since_last_price is None:
                lines.append(
                    f"{tq.ticker}: {tq.price_record_count} price record(s), "
                    f"none on or before {report_date} "
                    f"(earliest available: {tq.earliest_price_date})."
                )
            else:
                lines.append(
                    f"{tq.ticker}: {tq.price_record_count} price record(s), "
                    f"earliest {tq.earliest_price_date}, "
                    f"{tq.days_since_last_price} day(s) since last price as of report date."
                )
        body = "\n".join(lines)

    return _make_section(label, body)


def _week_range_section(week_start: str, report_date: str) -> ReportSection:
    label = "Week Range"
    body = f"Period: {week_start} to {report_date}."
    return _make_section(label, body)


def _drawdown_section(drawdown: DrawdownResult | None) -> ReportSection:
    label = "Drawdown Summary"
    if drawdown is None:
        body = "Drawdown from peak (M-005): not available — insufficient data."
    else:
        body = (
            f"Drawdown from peak (M-005): {drawdown.drawdown:.2%}"
            f" | Peak value: {drawdown.peak_value:.2f} USD"
            f" | Current value: {drawdown.current_value:.2f} USD"
            f" | Window: {drawdown.window_days} days"
            f" | Dates in window: {drawdown.dates_in_window}"
            f" | Min coverage ratio: {drawdown.min_coverage_ratio:.2%}"
            f" | Latest coverage ratio: {drawdown.latest_coverage_ratio:.2%}."
        )
    return _make_section(label, body)


def _volatility_section(volatility: VolatilityResult | None) -> ReportSection:
    label = "Volatility Proxy Summary"
    if volatility is None:
        body = "Volatility proxy (M-006): not available — insufficient data."
    else:
        body = (
            f"Volatility proxy (M-006): {volatility.volatility_proxy:.6f}"
            " (population std dev of daily percentage returns)"
            f" | Window: {volatility.window_days} days"
            f" | Returns computed: {volatility.returns_count}"
            f" | Min coverage ratio: {volatility.min_coverage_ratio:.2%}"
            f" | Latest coverage ratio: {volatility.latest_coverage_ratio:.2%}."
        )
    return _make_section(label, body)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_daily_report(
    report_date: str,
    snapshot: PortfolioSnapshot,
    alert_results: list[AlertResult],
    journal_entries: list[JournalEntry],
    data_quality: DataQualitySummary | None = None,
) -> DailyReport:
    """Compose a DailyReport from already-computed result objects.

    Validates report_date. Does not access DB, filesystem, network, or system clock.
    Raises InvalidDateError for an invalid report_date.
    Raises ComplianceViolationError if any system-generated section text is non-compliant.

    When data_quality is provided a 'Data Quality Summary' section is included
    after the Data Coverage section, and data_quality is stored on the returned
    DailyReport for structured API serialisation.
    """
    validate_iso_date(report_date)
    sections: list[ReportSection] = [
        _header_section(report_date, "daily"),
        _coverage_section(snapshot),
    ]
    if data_quality is not None:
        sections.append(_data_quality_section(data_quality))
    sections += [
        _snapshot_section(snapshot),
        _weights_section(snapshot),
        _alert_section(alert_results),
        _journal_note_section(journal_entries),
        _method_section(),
        _disclaimer_section(),
    ]
    return DailyReport(
        report_date=report_date,
        report_type="daily",
        sections=sections,
        journal_entries=list(journal_entries),
        data_quality=data_quality,
    )


def build_weekly_report(
    report_date: str,
    week_start: str,
    snapshot: PortfolioSnapshot,
    drawdown: DrawdownResult | None,
    volatility: VolatilityResult | None,
    alert_results: list[AlertResult],
    journal_entries: list[JournalEntry],
    data_quality: DataQualitySummary | None = None,
) -> WeeklyReport:
    """Compose a WeeklyReport from already-computed result objects.

    Validates report_date and week_start. week_start must be on or before report_date.
    Does not access DB, filesystem, network, or system clock.
    Raises InvalidDateError for invalid dates or if week_start is after report_date.
    Raises ComplianceViolationError if any system-generated section text is non-compliant.

    When data_quality is provided a 'Data Quality Summary' section is included
    after the Data Coverage section, and data_quality is stored on the returned
    WeeklyReport for structured API serialisation.
    """
    validate_iso_date(report_date)
    validate_iso_date(week_start)
    if _date.fromisoformat(week_start) > _date.fromisoformat(report_date):
        raise InvalidDateError(
            f"week_start {week_start!r} must be on or before report_date {report_date!r}."
        )
    sections: list[ReportSection] = [
        _header_section(report_date, "weekly"),
        _week_range_section(week_start, report_date),
        _coverage_section(snapshot),
    ]
    if data_quality is not None:
        sections.append(_data_quality_section(data_quality))
    sections += [
        _snapshot_section(snapshot),
        _drawdown_section(drawdown),
        _volatility_section(volatility),
        _weights_section(snapshot),
        _alert_section(alert_results),
        _journal_note_section(journal_entries),
        _method_section(),
        _disclaimer_section(),
    ]
    return WeeklyReport(
        report_date=report_date,
        week_start=week_start,
        report_type="weekly",
        sections=sections,
        journal_entries=list(journal_entries),
        data_quality=data_quality,
    )
