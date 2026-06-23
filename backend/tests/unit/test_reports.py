"""Unit tests for the Phase 7A pure report builder.

All tests are pure: no DB fixtures, no SQLite, no CSV, no file I/O,
no DataAdapter, no repositories, no API routes, no network.
Inputs are constructed in-memory from result dataclasses.
"""

import ast
import dataclasses
from pathlib import Path

import pytest

from app.alerts.results import AlertResult
from app.compliance.guard import check_compliance
from app.core.exceptions import ComplianceViolationError, InvalidDateError
from app.journal.models import JournalEntry
from app.metrics.results import (
    DrawdownResult,
    PortfolioSnapshot,
    PositionMetrics,
    VolatilityResult,
)
from app.reports.builder import _make_section, build_daily_report, build_weekly_report
from app.reports.models import DailyReport, ReportSection, WeeklyReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _priced_pos(
    ticker: str,
    weight: float = 0.5,
    market_value: float = 1000.0,
    qty: float = 10.0,
    cost_per_unit: float = 90.0,
) -> PositionMetrics:
    total_cost = qty * cost_per_unit
    unrealised_usd = market_value - total_cost
    unrealised_pct = unrealised_usd / total_cost if total_cost else None
    return PositionMetrics(
        ticker=ticker,
        quantity=qty,
        cost_basis_per_unit=cost_per_unit,
        total_cost_basis=total_cost,
        market_value=market_value,
        weight=weight,
        unrealised_change_usd=unrealised_usd,
        unrealised_change_pct=unrealised_pct,
    )


def _unpriced_pos(ticker: str, qty: float = 10.0, cost_per_unit: float = 90.0) -> PositionMetrics:
    return PositionMetrics(
        ticker=ticker,
        quantity=qty,
        cost_basis_per_unit=cost_per_unit,
        total_cost_basis=qty * cost_per_unit,
        market_value=None,
        weight=None,
        unrealised_change_usd=None,
        unrealised_change_pct=None,
    )


def _snapshot(
    positions: list[PositionMetrics],
    unpriced_tickers: list[str] | None = None,
    total_mv: float | None = None,
) -> PortfolioSnapshot:
    priced_count = sum(1 for p in positions if p.market_value is not None)
    computed_mv = sum(p.market_value for p in positions if p.market_value is not None)
    return PortfolioSnapshot(
        total_market_value=total_mv if total_mv is not None else computed_mv,
        positions=positions,
        priced_count=priced_count,
        unpriced_tickers=unpriced_tickers or [],
    )


def _empty_snapshot() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        total_market_value=0.0,
        positions=[],
        priced_count=0,
        unpriced_tickers=[],
    )


def _drawdown(dd: float = 0.10, window: int = 90) -> DrawdownResult:
    peak = 10000.0
    current = peak * (1.0 - dd)
    return DrawdownResult(
        drawdown=dd,
        peak_value=peak,
        current_value=current,
        window_days=window,
        dates_in_window=window,
        min_coverage_ratio=1.0,
        latest_coverage_ratio=1.0,
    )


def _volatility(vp: float = 0.015, window: int = 30) -> VolatilityResult:
    return VolatilityResult(
        volatility_proxy=vp,
        window_days=window,
        returns_count=window - 1,
        min_coverage_ratio=1.0,
        latest_coverage_ratio=1.0,
    )


def _alert(
    rule_id: str = "CONC-001",
    fired: bool = False,
    severity: str = "informational",
    metric_value: float = 0.10,
    threshold: float = 0.25,
    explanation: str = "CONC-001: within threshold.",
    ticker: str | None = None,
) -> AlertResult:
    return AlertResult(
        rule_id=rule_id,
        fired=fired,
        severity=severity,
        metric_value=metric_value,
        threshold=threshold,
        explanation=explanation,
        ticker=ticker,
    )


def _fired_alert(ticker: str = "AAPL") -> AlertResult:
    return AlertResult(
        rule_id="CONC-001",
        fired=True,
        severity="watch",
        metric_value=0.30,
        threshold=0.25,
        explanation=f"CONC-001: {ticker} weight is 30.00%, above the single-position ceiling of 25.00%.",
        ticker=ticker,
    )


def _journal_entry(
    id: int = 1,
    entry_date: str = "2026-01-10",
    action_taken: str = "reviewed portfolio",
    reasoning: str = "quarterly check",
    ticker: str | None = None,
) -> JournalEntry:
    return JournalEntry(
        id=id,
        entry_date=entry_date,
        action_taken=action_taken,
        reasoning=reasoning,
        created_at="2026-01-10T00:00:00+00:00",
        ticker=ticker,
    )


_DATE = "2026-06-23"
_WEEK_START = "2026-06-17"


# ---------------------------------------------------------------------------
# ReportSection dataclass
# ---------------------------------------------------------------------------


class TestReportSectionDataclass:
    def test_is_frozen(self):
        section = ReportSection(label="X", body="Y")
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
            section.label = "Z"  # type: ignore[misc]

    def test_fields_accessible(self):
        section = ReportSection(label="Header", body="content")
        assert section.label == "Header"
        assert section.body == "content"


# ---------------------------------------------------------------------------
# DailyReport dataclass
# ---------------------------------------------------------------------------


class TestDailyReportDataclass:
    def test_is_frozen(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
            report.report_date = "2026-01-01"  # type: ignore[misc]

    def test_report_type_is_daily(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        assert report.report_type == "daily"

    def test_report_date_preserved(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        assert report.report_date == _DATE


# ---------------------------------------------------------------------------
# WeeklyReport dataclass
# ---------------------------------------------------------------------------


class TestWeeklyReportDataclass:
    def test_is_frozen(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
            report.report_date = "2026-01-01"  # type: ignore[misc]

    def test_report_type_is_weekly(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        assert report.report_type == "weekly"

    def test_report_date_preserved(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        assert report.report_date == _DATE

    def test_week_start_preserved(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        assert report.week_start == _WEEK_START


# ---------------------------------------------------------------------------
# _make_section helper
# ---------------------------------------------------------------------------


class TestMakeSection:
    def test_returns_report_section(self):
        s = _make_section("Label", "Body text.")
        assert isinstance(s, ReportSection)
        assert s.label == "Label"
        assert s.body == "Body text."

    def test_compliance_violation_on_label_propagates(self):
        with pytest.raises(ComplianceViolationError):
            _make_section("buy", "Safe body.")

    def test_compliance_violation_on_body_propagates(self):
        with pytest.raises(ComplianceViolationError):
            _make_section("Safe label", "You should sell immediately.")

    def test_clean_text_does_not_raise(self):
        s = _make_section("Data Coverage", "2 of 3 position(s) priced.")
        assert s.label == "Data Coverage"


# ---------------------------------------------------------------------------
# build_daily_report — structure and content
# ---------------------------------------------------------------------------


class TestBuildDailyReport:
    def test_returns_daily_report_instance(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        assert isinstance(report, DailyReport)

    def test_sections_are_non_empty(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        assert len(report.sections) > 0

    def test_all_sections_are_report_section_instances(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        for section in report.sections:
            assert isinstance(section, ReportSection)

    def test_every_section_label_passes_compliance(self):
        report = build_daily_report(
            _DATE,
            _snapshot([_priced_pos("AAPL"), _unpriced_pos("MSFT")], unpriced_tickers=["MSFT"]),
            [_alert(), _fired_alert()],
            [_journal_entry()],
        )
        for section in report.sections:
            check_compliance(section.label)  # must not raise

    def test_every_section_body_passes_compliance(self):
        report = build_daily_report(
            _DATE,
            _snapshot([_priced_pos("AAPL"), _unpriced_pos("MSFT")], unpriced_tickers=["MSFT"]),
            [_alert(), _fired_alert()],
            [_journal_entry()],
        )
        for section in report.sections:
            check_compliance(section.body)  # must not raise

    def test_disclaimer_section_present(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        labels = [s.label for s in report.sections]
        assert "Disclaimer" in labels

    def test_disclaimer_contains_non_advisory_statement(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        disclaimer = next(s for s in report.sections if s.label == "Disclaimer")
        assert "Not investment advice" in disclaimer.body

    def test_data_coverage_section_present(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        labels = [s.label for s in report.sections]
        assert "Data Coverage" in labels

    def test_data_coverage_reflects_priced_count(self):
        positions = [_priced_pos("AAPL"), _priced_pos("MSFT", weight=0.5)]
        snap = _snapshot(positions)
        report = build_daily_report(_DATE, snap, [], [])
        coverage = next(s for s in report.sections if s.label == "Data Coverage")
        assert "2 of 2" in coverage.body

    def test_data_coverage_lists_unpriced_tickers(self):
        positions = [_priced_pos("AAPL"), _unpriced_pos("MSFT")]
        snap = _snapshot(positions, unpriced_tickers=["MSFT"])
        report = build_daily_report(_DATE, snap, [], [])
        coverage = next(s for s in report.sections if s.label == "Data Coverage")
        assert "MSFT" in coverage.body
        assert "price data not available" in coverage.body.lower()

    def test_portfolio_snapshot_section_present(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        labels = [s.label for s in report.sections]
        assert "Portfolio Snapshot" in labels

    def test_portfolio_snapshot_includes_total_market_value(self):
        snap = _snapshot([_priced_pos("AAPL", market_value=5000.0)], total_mv=5000.0)
        report = build_daily_report(_DATE, snap, [], [])
        ss = next(s for s in report.sections if s.label == "Portfolio Snapshot")
        assert "5000.00" in ss.body

    def test_portfolio_snapshot_includes_position_counts(self):
        positions = [_priced_pos("AAPL"), _unpriced_pos("MSFT")]
        snap = _snapshot(positions, unpriced_tickers=["MSFT"])
        report = build_daily_report(_DATE, snap, [], [])
        ss = next(s for s in report.sections if s.label == "Portfolio Snapshot")
        assert "2" in ss.body  # total positions

    def test_position_weights_section_present(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        labels = [s.label for s in report.sections]
        assert "Position Weights" in labels

    def test_position_weights_includes_priced_positions(self):
        positions = [_priced_pos("AAPL", weight=0.60, market_value=6000.0)]
        snap = _snapshot(positions)
        report = build_daily_report(_DATE, snap, [], [])
        pw = next(s for s in report.sections if s.label == "Position Weights")
        assert "AAPL" in pw.body
        assert "6000.00" in pw.body

    def test_position_weights_includes_unrealised_change(self):
        pos = _priced_pos("AAPL", weight=0.5, market_value=1100.0, qty=10.0, cost_per_unit=100.0)
        snap = _snapshot([pos])
        report = build_daily_report(_DATE, snap, [], [])
        pw = next(s for s in report.sections if s.label == "Position Weights")
        assert "unrealised change in value" in pw.body

    def test_position_weights_unpriced_shows_not_available(self):
        positions = [_unpriced_pos("TSLA")]
        snap = _snapshot(positions, unpriced_tickers=["TSLA"])
        report = build_daily_report(_DATE, snap, [], [])
        pw = next(s for s in report.sections if s.label == "Position Weights")
        assert "TSLA" in pw.body
        assert "price data not available" in pw.body

    def test_all_unpriced_portfolio_handled(self):
        positions = [_unpriced_pos("AAPL"), _unpriced_pos("MSFT")]
        snap = _snapshot(positions, unpriced_tickers=["AAPL", "MSFT"])
        report = build_daily_report(_DATE, snap, [], [])
        coverage = next(s for s in report.sections if s.label == "Data Coverage")
        assert "0 of 2" in coverage.body

    def test_zero_position_portfolio_handled(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        coverage = next(s for s in report.sections if s.label == "Data Coverage")
        assert "No positions recorded" in coverage.body

    def test_alert_summary_section_present(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        labels = [s.label for s in report.sections]
        assert "Alert Summary" in labels

    def test_alert_summary_includes_fired_alert(self):
        alert = _fired_alert("AAPL")
        report = build_daily_report(_DATE, _empty_snapshot(), [alert], [])
        summary = next(s for s in report.sections if s.label == "Alert Summary")
        assert "CONC-001" in summary.body
        assert "Fired" in summary.body

    def test_alert_summary_includes_non_fired_alert(self):
        alert = _alert(fired=False, severity="informational")
        report = build_daily_report(_DATE, _empty_snapshot(), [alert], [])
        summary = next(s for s in report.sections if s.label == "Alert Summary")
        assert "CONC-001" in summary.body
        assert "Within threshold" in summary.body

    def test_alert_summary_includes_all_alerts_fired_and_non_fired(self):
        alerts = [
            _fired_alert("AAPL"),
            _alert(rule_id="DD-001", fired=False, severity="informational",
                   metric_value=0.05, threshold=0.15,
                   explanation="DD-001: drawdown is 5.00%, within the 15.00% ceiling."),
        ]
        report = build_daily_report(_DATE, _empty_snapshot(), alerts, [])
        summary = next(s for s in report.sections if s.label == "Alert Summary")
        assert "CONC-001" in summary.body
        assert "DD-001" in summary.body

    def test_alert_summary_fired_severity_appears(self):
        alert = _fired_alert("AAPL")
        report = build_daily_report(_DATE, _empty_snapshot(), [alert], [])
        summary = next(s for s in report.sections if s.label == "Alert Summary")
        assert "watch" in summary.body

    def test_alert_summary_informational_severity_appears(self):
        alert = _alert(fired=False, severity="informational")
        report = build_daily_report(_DATE, _empty_snapshot(), [alert], [])
        summary = next(s for s in report.sections if s.label == "Alert Summary")
        assert "informational" in summary.body

    def test_alert_summary_empty_shows_safe_text(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        summary = next(s for s in report.sections if s.label == "Alert Summary")
        assert "No alert rules evaluated" in summary.body

    def test_journal_entries_preserved_verbatim(self):
        entry = _journal_entry(action_taken="reviewed quarterly", reasoning="routine check")
        report = build_daily_report(_DATE, _empty_snapshot(), [], [entry])
        assert len(report.journal_entries) == 1
        assert report.journal_entries[0] is entry

    def test_journal_entries_multiple_preserved(self):
        entries = [_journal_entry(id=1), _journal_entry(id=2)]
        report = build_daily_report(_DATE, _empty_snapshot(), [], entries)
        assert len(report.journal_entries) == 2

    def test_journal_entry_with_forbidden_term_does_not_raise(self):
        entry = _journal_entry(
            action_taken="decided to buy more shares",
            reasoning="sell signal looked interesting",
        )
        # Should NOT raise — user-authored text is never compliance-scanned
        report = build_daily_report(_DATE, _empty_snapshot(), [], [entry])
        assert report.journal_entries[0].action_taken == "decided to buy more shares"

    def test_journal_section_body_contains_only_count_not_user_text(self):
        entry = _journal_entry(
            action_taken="decided to buy more shares",
            reasoning="portfolio rebalancing",
        )
        report = build_daily_report(_DATE, _empty_snapshot(), [], [entry])
        journal_section = next(s for s in report.sections if s.label == "Journal Entries")
        # User text must NOT appear in the generated section body
        assert "buy" not in journal_section.body
        assert "rebalancing" not in journal_section.body
        assert "decided" not in journal_section.body

    def test_journal_section_body_when_empty(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Journal Entries")
        assert "No entries recorded" in section.body

    def test_journal_section_body_when_one_entry(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [_journal_entry()])
        section = next(s for s in report.sections if s.label == "Journal Entries")
        assert "1" in section.body

    def test_journal_section_body_when_multiple_entries(self):
        entries = [_journal_entry(id=1), _journal_entry(id=2), _journal_entry(id=3)]
        report = build_daily_report(_DATE, _empty_snapshot(), [], entries)
        section = next(s for s in report.sections if s.label == "Journal Entries")
        assert "3" in section.body

    def test_no_section_body_contains_buy(self):
        report = build_daily_report(
            _DATE,
            _snapshot([_priced_pos("AAPL")]),
            [_alert()],
            [],
        )
        for section in report.sections:
            assert " buy " not in section.body.lower()

    def test_no_section_body_contains_sell(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        for section in report.sections:
            assert "sell" not in section.body.lower()

    def test_no_section_body_contains_profit(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        for section in report.sections:
            assert "profit" not in section.body.lower()

    def test_no_section_body_contains_loss(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        for section in report.sections:
            assert "loss" not in section.body.lower()

    def test_no_section_body_contains_opportunity(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        for section in report.sections:
            assert "opportunity" not in section.body.lower()

    def test_no_section_body_contains_recommend(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        for section in report.sections:
            assert "recommend" not in section.body.lower()


# ---------------------------------------------------------------------------
# build_weekly_report — structure and content
# ---------------------------------------------------------------------------


class TestBuildWeeklyReport:
    def test_returns_weekly_report_instance(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        assert isinstance(report, WeeklyReport)

    def test_sections_are_non_empty(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        assert len(report.sections) > 0

    def test_every_section_label_passes_compliance(self):
        report = build_weekly_report(
            _DATE, _WEEK_START,
            _snapshot([_priced_pos("AAPL")]),
            _drawdown(), _volatility(),
            [_alert(), _fired_alert()],
            [_journal_entry()],
        )
        for section in report.sections:
            check_compliance(section.label)

    def test_every_section_body_passes_compliance(self):
        report = build_weekly_report(
            _DATE, _WEEK_START,
            _snapshot([_priced_pos("AAPL"), _unpriced_pos("MSFT")], unpriced_tickers=["MSFT"]),
            _drawdown(), _volatility(),
            [_alert(), _fired_alert()],
            [_journal_entry()],
        )
        for section in report.sections:
            check_compliance(section.body)

    def test_week_range_section_present(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        labels = [s.label for s in report.sections]
        assert "Week Range" in labels

    def test_week_range_contains_week_start_and_report_date(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        wr = next(s for s in report.sections if s.label == "Week Range")
        assert _WEEK_START in wr.body
        assert _DATE in wr.body

    def test_drawdown_section_present_when_data_available(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), _drawdown(), None, [], [])
        labels = [s.label for s in report.sections]
        assert "Drawdown Summary" in labels

    def test_drawdown_section_contains_drawdown_value(self):
        dd = _drawdown(dd=0.12)
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), dd, None, [], [])
        ds = next(s for s in report.sections if s.label == "Drawdown Summary")
        assert "12.00%" in ds.body

    def test_drawdown_section_contains_peak_and_current_value(self):
        dd = _drawdown(dd=0.10)
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), dd, None, [], [])
        ds = next(s for s in report.sections if s.label == "Drawdown Summary")
        assert "10000.00" in ds.body  # peak_value
        assert "9000.00" in ds.body   # current_value

    def test_drawdown_none_produces_not_available_text(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        ds = next(s for s in report.sections if s.label == "Drawdown Summary")
        assert "not available" in ds.body

    def test_volatility_section_present_when_data_available(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, _volatility(), [], [])
        labels = [s.label for s in report.sections]
        assert "Volatility Proxy Summary" in labels

    def test_volatility_section_contains_proxy_value(self):
        vol = _volatility(vp=0.021)
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, vol, [], [])
        vs = next(s for s in report.sections if s.label == "Volatility Proxy Summary")
        assert "0.021000" in vs.body

    def test_volatility_section_contains_window_and_returns_count(self):
        vol = _volatility(vp=0.015, window=30)
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, vol, [], [])
        vs = next(s for s in report.sections if s.label == "Volatility Proxy Summary")
        assert "30" in vs.body
        assert "29" in vs.body  # returns_count = window - 1

    def test_volatility_none_produces_not_available_text(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        vs = next(s for s in report.sections if s.label == "Volatility Proxy Summary")
        assert "not available" in vs.body

    def test_journal_entries_preserved_verbatim(self):
        entry = _journal_entry()
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [entry])
        assert len(report.journal_entries) == 1
        assert report.journal_entries[0] is entry

    def test_journal_entry_with_forbidden_term_does_not_raise(self):
        entry = _journal_entry(
            action_taken="decided to sell half the position",
            reasoning="to reduce concentration",
        )
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [entry])
        assert report.journal_entries[0].action_taken == "decided to sell half the position"

    def test_disclaimer_present(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        labels = [s.label for s in report.sections]
        assert "Disclaimer" in labels

    def test_alert_summary_includes_all_alerts(self):
        alerts = [
            _fired_alert("AAPL"),
            _alert(rule_id="DD-001", fired=False, severity="informational",
                   metric_value=0.05, threshold=0.15,
                   explanation="DD-001: drawdown is 5.00%, within the 15.00% ceiling."),
        ]
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, alerts, [])
        summary = next(s for s in report.sections if s.label == "Alert Summary")
        assert "CONC-001" in summary.body
        assert "DD-001" in summary.body


# ---------------------------------------------------------------------------
# Date validation
# ---------------------------------------------------------------------------


class TestDateValidation:
    def test_invalid_report_date_raises_invalid_date_error(self):
        with pytest.raises(InvalidDateError):
            build_daily_report("not-a-date", _empty_snapshot(), [], [])

    def test_invalid_report_date_wrong_format_raises(self):
        with pytest.raises(InvalidDateError):
            build_daily_report("23-06-2026", _empty_snapshot(), [], [])

    def test_invalid_week_start_raises_invalid_date_error(self):
        with pytest.raises(InvalidDateError):
            build_weekly_report(_DATE, "not-a-date", _empty_snapshot(), None, None, [], [])

    def test_week_start_after_report_date_raises_invalid_date_error(self):
        with pytest.raises(InvalidDateError):
            build_weekly_report("2026-06-17", "2026-06-23", _empty_snapshot(), None, None, [], [])

    def test_week_start_equal_to_report_date_is_valid(self):
        report = build_weekly_report("2026-06-23", "2026-06-23", _empty_snapshot(), None, None, [], [])
        assert report.week_start == "2026-06-23"
        assert report.report_date == "2026-06-23"

    def test_valid_dates_do_not_raise(self):
        report = build_daily_report("2026-01-01", _empty_snapshot(), [], [])
        assert report.report_date == "2026-01-01"


# ---------------------------------------------------------------------------
# Boundary / purity — reports/ source files must not import forbidden modules
# ---------------------------------------------------------------------------


def _reports_source_files() -> list[Path]:
    tests_unit = Path(__file__).parent
    backend = tests_unit.parent.parent
    reports_dir = backend / "app" / "reports"
    return [f for f in reports_dir.glob("*.py") if f.name != "__pycache__"]


def _collect_imports(src_file: Path) -> list[str]:
    source = src_file.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.append(node.module)
    return imported


def test_reports_does_not_import_sqlite3():
    for src_file in _reports_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            assert "sqlite3" not in imp, f"{src_file.name} imports sqlite3"


def test_reports_does_not_import_csv():
    for src_file in _reports_source_files():
        imports = _collect_imports(src_file)
        assert "csv" not in imports, f"{src_file.name} imports csv"


def test_reports_does_not_import_os():
    for src_file in _reports_source_files():
        imports = _collect_imports(src_file)
        assert not any(
            imp == "os" or imp.startswith("os.") for imp in imports
        ), f"{src_file.name} imports os"


def test_reports_does_not_import_pathlib():
    for src_file in _reports_source_files():
        imports = _collect_imports(src_file)
        assert not any(
            imp == "pathlib" or imp.startswith("pathlib.") for imp in imports
        ), f"{src_file.name} imports pathlib"


def test_reports_does_not_import_network_libraries():
    forbidden_prefixes = ("requests", "httpx", "aiohttp", "urllib", "http.client")
    for src_file in _reports_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            for prefix in forbidden_prefixes:
                assert not (imp == prefix or imp.startswith(prefix + ".")), (
                    f"{src_file.name} imports network library: {imp}"
                )


def test_reports_does_not_import_persistence():
    for src_file in _reports_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            assert "data.persistence" not in imp, (
                f"{src_file.name} imports persistence layer: {imp}"
            )


def test_reports_does_not_import_adapters():
    for src_file in _reports_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            assert "data.adapters" not in imp, (
                f"{src_file.name} imports adapter layer: {imp}"
            )


def test_reports_does_not_import_metrics_engine():
    for src_file in _reports_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            assert imp != "app.metrics.engine", (
                f"{src_file.name} imports metrics engine"
            )


def test_reports_does_not_import_alerts_rules():
    for src_file in _reports_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            assert imp != "app.alerts.rules", (
                f"{src_file.name} imports alerts rules"
            )


def test_builder_does_not_call_system_clock():
    builder_file = Path(__file__).parent.parent.parent / "app" / "reports" / "builder.py"
    source = builder_file.read_text(encoding="utf-8")
    assert "datetime.now(" not in source, "builder.py calls datetime.now()"
    assert "date.today(" not in source, "builder.py calls date.today()"


# ---------------------------------------------------------------------------
# Compliance propagation via _make_section
# ---------------------------------------------------------------------------


def test_make_section_propagates_compliance_violation_on_label():
    with pytest.raises(ComplianceViolationError) as exc_info:
        _make_section("buy", "Safe text here.")
    assert exc_info.value.violations


def test_make_section_propagates_compliance_violation_on_body():
    with pytest.raises(ComplianceViolationError) as exc_info:
        _make_section("Safe Label", "You should sell your positions immediately.")
    assert exc_info.value.violations


def test_make_section_does_not_catch_or_rewrite_violation():
    with pytest.raises(ComplianceViolationError):
        _make_section("Header", "This is a guaranteed profit opportunity.")


# ---------------------------------------------------------------------------
# Journal text is not compliance-scanned
# ---------------------------------------------------------------------------


def test_journal_fields_not_scanned_action_taken():
    entry = JournalEntry(
        id=1,
        entry_date="2026-01-01",
        action_taken="buy and sell decisions made",
        reasoning="portfolio rebalancing",
        created_at="2026-01-01T00:00:00+00:00",
    )
    report = build_daily_report(_DATE, _empty_snapshot(), [], [entry])
    assert report.journal_entries[0].action_taken == "buy and sell decisions made"


def test_journal_fields_not_scanned_reasoning():
    entry = JournalEntry(
        id=2,
        entry_date="2026-01-01",
        action_taken="reviewed position",
        reasoning="profit target was reached so I reduced the position",
        created_at="2026-01-01T00:00:00+00:00",
    )
    report = build_daily_report(_DATE, _empty_snapshot(), [], [entry])
    assert "profit" in report.journal_entries[0].reasoning


def test_journal_section_body_never_contains_user_action_taken():
    entry = JournalEntry(
        id=3,
        entry_date="2026-01-01",
        action_taken="decided to buy more shares of AAPL",
        reasoning="diversification",
        created_at="2026-01-01T00:00:00+00:00",
    )
    report = build_daily_report(_DATE, _empty_snapshot(), [], [entry])
    journal_section = next(s for s in report.sections if s.label == "Journal Entries")
    assert "decided" not in journal_section.body
    assert "AAPL" not in journal_section.body


def test_journal_section_body_never_contains_user_reasoning():
    entry = JournalEntry(
        id=4,
        entry_date="2026-01-01",
        action_taken="reviewed",
        reasoning="quarterly review of concentration",
        created_at="2026-01-01T00:00:00+00:00",
    )
    report = build_daily_report(_DATE, _empty_snapshot(), [], [entry])
    journal_section = next(s for s in report.sections if s.label == "Journal Entries")
    assert "quarterly review of concentration" not in journal_section.body


# ---------------------------------------------------------------------------
# Phase 8B — Metric Definitions section
# ---------------------------------------------------------------------------


class TestMetricDefinitionsSection:
    def test_present_in_daily_report(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        labels = [s.label for s in report.sections]
        assert "Metric Definitions" in labels

    def test_present_in_weekly_report(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        labels = [s.label for s in report.sections]
        assert "Metric Definitions" in labels

    def test_present_in_daily_without_data_quality(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=None)
        labels = [s.label for s in report.sections]
        assert "Metric Definitions" in labels

    def test_present_in_daily_with_data_quality(self):
        from app.metrics.quality import DataQualitySummary
        dq = DataQualitySummary(
            report_date=_DATE,
            total_holding_count=0,
            priced_holding_count=0,
            unpriced_holding_count=0,
            coverage_ratio=0.0,
            unpriced_tickers=[],
            ticker_quality=[],
        )
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=dq)
        labels = [s.label for s in report.sections]
        assert "Metric Definitions" in labels

    def test_label_passes_compliance(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Metric Definitions")
        check_compliance(section.label)  # must not raise

    def test_body_passes_compliance(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Metric Definitions")
        check_compliance(section.body)  # must not raise

    def test_body_references_m001(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Metric Definitions")
        assert "M-001" in section.body

    def test_body_references_m005(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Metric Definitions")
        assert "M-005" in section.body

    def test_body_references_m006(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Metric Definitions")
        assert "M-006" in section.body

    def test_body_contains_no_advisory_terms(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Metric Definitions")
        for forbidden in ("buy", "sell", "profit", "opportunity", "recommend"):
            assert forbidden not in section.body.lower(), (
                f"Forbidden term '{forbidden}' found in Metric Definitions body"
            )

    def test_body_is_deterministic(self):
        r1 = build_daily_report(_DATE, _empty_snapshot(), [], [])
        r2 = build_daily_report(_DATE, _empty_snapshot(), [], [])
        s1 = next(s for s in r1.sections if s.label == "Metric Definitions")
        s2 = next(s for s in r2.sections if s.label == "Metric Definitions")
        assert s1.body == s2.body

    def test_weekly_body_passes_compliance(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        section = next(s for s in report.sections if s.label == "Metric Definitions")
        check_compliance(section.body)


# ---------------------------------------------------------------------------
# Phase 8B — Alert Rule Definitions section
# ---------------------------------------------------------------------------


class TestAlertRuleDefinitionsSection:
    def test_present_in_daily_report(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        labels = [s.label for s in report.sections]
        assert "Alert Rule Definitions" in labels

    def test_present_in_weekly_report(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        labels = [s.label for s in report.sections]
        assert "Alert Rule Definitions" in labels

    def test_label_passes_compliance(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Alert Rule Definitions")
        check_compliance(section.label)

    def test_body_passes_compliance(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Alert Rule Definitions")
        check_compliance(section.body)

    def test_body_references_conc001(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Alert Rule Definitions")
        assert "CONC-001" in section.body

    def test_body_references_dd001(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Alert Rule Definitions")
        assert "DD-001" in section.body

    def test_body_references_vol001(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Alert Rule Definitions")
        assert "VOL-001" in section.body

    def test_body_references_cov001(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Alert Rule Definitions")
        assert "COV-001" in section.body

    def test_body_contains_no_advisory_terms(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        section = next(s for s in report.sections if s.label == "Alert Rule Definitions")
        for forbidden in ("buy", "sell", "profit", "opportunity", "recommend"):
            assert forbidden not in section.body.lower(), (
                f"Forbidden term '{forbidden}' found in Alert Rule Definitions body"
            )

    def test_body_is_deterministic(self):
        r1 = build_daily_report(_DATE, _empty_snapshot(), [], [])
        r2 = build_daily_report(_DATE, _empty_snapshot(), [], [])
        s1 = next(s for s in r1.sections if s.label == "Alert Rule Definitions")
        s2 = next(s for s in r2.sections if s.label == "Alert Rule Definitions")
        assert s1.body == s2.body

    def test_weekly_body_passes_compliance(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        section = next(s for s in report.sections if s.label == "Alert Rule Definitions")
        check_compliance(section.body)


# ---------------------------------------------------------------------------
# Phase 8B — Data Quality Caveat section
# ---------------------------------------------------------------------------


def _make_dq_summary(
    total: int,
    priced: int,
    unpriced_tickers: list[str] | None = None,
    report_date: str = _DATE,
):
    from app.metrics.quality import DataQualitySummary
    ut = unpriced_tickers or []
    unpriced = total - priced
    ratio = priced / total if total > 0 else 0.0
    return DataQualitySummary(
        report_date=report_date,
        total_holding_count=total,
        priced_holding_count=priced,
        unpriced_holding_count=unpriced,
        coverage_ratio=ratio,
        unpriced_tickers=ut,
        ticker_quality=[],
    )


class TestDataQualityCaveatSection:
    def test_present_when_unpriced_count_greater_than_zero(self):
        dq = _make_dq_summary(3, 2, ["TSLA"])
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=dq)
        labels = [s.label for s in report.sections]
        assert "Data Quality Caveat" in labels

    def test_absent_when_all_positions_priced(self):
        dq = _make_dq_summary(2, 2)
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=dq)
        labels = [s.label for s in report.sections]
        assert "Data Quality Caveat" not in labels

    def test_absent_when_data_quality_is_none(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=None)
        labels = [s.label for s in report.sections]
        assert "Data Quality Caveat" not in labels

    def test_absent_for_empty_portfolio(self):
        dq = _make_dq_summary(0, 0)
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=dq)
        labels = [s.label for s in report.sections]
        assert "Data Quality Caveat" not in labels

    def test_label_passes_compliance(self):
        dq = _make_dq_summary(2, 1, ["MSFT"])
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=dq)
        section = next(s for s in report.sections if s.label == "Data Quality Caveat")
        check_compliance(section.label)

    def test_body_passes_compliance(self):
        dq = _make_dq_summary(2, 1, ["MSFT"])
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=dq)
        section = next(s for s in report.sections if s.label == "Data Quality Caveat")
        check_compliance(section.body)

    def test_body_references_coverage_ratio(self):
        dq = _make_dq_summary(4, 3, ["TSLA"])
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=dq)
        section = next(s for s in report.sections if s.label == "Data Quality Caveat")
        assert "75.00%" in section.body

    def test_body_references_unpriced_count(self):
        dq = _make_dq_summary(4, 2, ["TSLA", "GOOG"])
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=dq)
        section = next(s for s in report.sections if s.label == "Data Quality Caveat")
        assert "2" in section.body

    def test_body_references_affected_metric_families(self):
        dq = _make_dq_summary(2, 1, ["MSFT"])
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=dq)
        section = next(s for s in report.sections if s.label == "Data Quality Caveat")
        assert "M-005" in section.body
        assert "M-006" in section.body

    def test_body_contains_no_advisory_terms(self):
        dq = _make_dq_summary(2, 1, ["MSFT"])
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=dq)
        section = next(s for s in report.sections if s.label == "Data Quality Caveat")
        for forbidden in ("buy", "sell", "profit", "opportunity", "recommend", "suggest"):
            assert forbidden not in section.body.lower(), (
                f"Forbidden term '{forbidden}' found in Data Quality Caveat body"
            )

    def test_present_in_weekly_report_when_unpriced(self):
        dq = _make_dq_summary(2, 1, ["MSFT"])
        report = build_weekly_report(
            _DATE, _WEEK_START, _empty_snapshot(), None, None, [], [], data_quality=dq
        )
        labels = [s.label for s in report.sections]
        assert "Data Quality Caveat" in labels

    def test_absent_in_weekly_when_all_priced(self):
        dq = _make_dq_summary(2, 2)
        report = build_weekly_report(
            _DATE, _WEEK_START, _empty_snapshot(), None, None, [], [], data_quality=dq
        )
        labels = [s.label for s in report.sections]
        assert "Data Quality Caveat" not in labels

    def test_weekly_body_passes_compliance(self):
        dq = _make_dq_summary(2, 1, ["MSFT"])
        report = build_weekly_report(
            _DATE, _WEEK_START, _empty_snapshot(), None, None, [], [], data_quality=dq
        )
        section = next(s for s in report.sections if s.label == "Data Quality Caveat")
        check_compliance(section.body)


# ---------------------------------------------------------------------------
# Phase 8B — Section ordering
# ---------------------------------------------------------------------------


class TestPhase8BSectionOrdering:
    def _label_index(self, report, label: str) -> int:
        labels = [s.label for s in report.sections]
        return labels.index(label)

    def test_data_coverage_before_metric_definitions_daily(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        assert self._label_index(report, "Data Coverage") < self._label_index(report, "Metric Definitions")

    def test_metric_definitions_before_alert_rule_definitions_daily(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        assert self._label_index(report, "Metric Definitions") < self._label_index(report, "Alert Rule Definitions")

    def test_alert_rule_definitions_before_portfolio_snapshot_daily(self):
        report = build_daily_report(_DATE, _empty_snapshot(), [], [])
        assert self._label_index(report, "Alert Rule Definitions") < self._label_index(report, "Portfolio Snapshot")

    def test_data_quality_summary_before_caveat_daily(self):
        dq = _make_dq_summary(2, 1, ["MSFT"])
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=dq)
        assert self._label_index(report, "Data Quality Summary") < self._label_index(report, "Data Quality Caveat")

    def test_caveat_before_metric_definitions_when_present_daily(self):
        dq = _make_dq_summary(2, 1, ["MSFT"])
        report = build_daily_report(_DATE, _empty_snapshot(), [], [], data_quality=dq)
        assert self._label_index(report, "Data Quality Caveat") < self._label_index(report, "Metric Definitions")

    def test_data_coverage_before_metric_definitions_weekly(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        assert self._label_index(report, "Data Coverage") < self._label_index(report, "Metric Definitions")

    def test_metric_definitions_before_alert_rule_definitions_weekly(self):
        report = build_weekly_report(_DATE, _WEEK_START, _empty_snapshot(), None, None, [], [])
        assert self._label_index(report, "Metric Definitions") < self._label_index(report, "Alert Rule Definitions")


# ---------------------------------------------------------------------------
# Phase 8B — Compliance regression: all sections in a full report pass guard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("with_data_quality,with_unpriced", [
    (False, False),
    (True, False),
    (True, True),
])
def test_all_daily_sections_pass_compliance_regression(with_data_quality, with_unpriced):
    from app.metrics.quality import DataQualitySummary
    dq = None
    if with_data_quality:
        if with_unpriced:
            dq = _make_dq_summary(2, 1, ["MSFT"])
        else:
            dq = _make_dq_summary(2, 2)
    report = build_daily_report(
        _DATE,
        _snapshot([_priced_pos("AAPL"), _unpriced_pos("MSFT")], unpriced_tickers=["MSFT"]),
        [_alert(), _fired_alert()],
        [_journal_entry()],
        data_quality=dq,
    )
    for section in report.sections:
        check_compliance(section.label)
        check_compliance(section.body)


@pytest.mark.parametrize("with_data_quality,with_unpriced", [
    (False, False),
    (True, False),
    (True, True),
])
def test_all_weekly_sections_pass_compliance_regression(with_data_quality, with_unpriced):
    dq = None
    if with_data_quality:
        if with_unpriced:
            dq = _make_dq_summary(2, 1, ["MSFT"])
        else:
            dq = _make_dq_summary(2, 2)
    report = build_weekly_report(
        _DATE, _WEEK_START,
        _snapshot([_priced_pos("AAPL"), _unpriced_pos("MSFT")], unpriced_tickers=["MSFT"]),
        _drawdown(), _volatility(),
        [_alert(), _fired_alert()],
        [_journal_entry()],
        data_quality=dq,
    )
    for section in report.sections:
        check_compliance(section.label)
        check_compliance(section.body)
