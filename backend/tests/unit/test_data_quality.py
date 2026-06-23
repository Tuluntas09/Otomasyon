"""Unit tests for Phase 8A data quality analytics.

All tests are pure: no DB fixtures, no SQLite, no CSV, no file I/O.
Inputs are constructed in-memory from domain dataclasses.

Covers:
  - compute_data_quality pure function: counts, dates, days_since, coverage
  - Edge cases: empty holdings, no price records, prices after report_date
  - Frozen result dataclasses
  - Purity: no system clock, no forbidden module imports
  - Report builder integration: Data Quality Summary section
  - Compliance: section label and body pass check_compliance
  - No forbidden advisory language in generated text
"""

import ast
from pathlib import Path

import pytest

from app.compliance.guard import check_compliance
from app.core.exceptions import ComplianceViolationError, InvalidDateError
from app.core.models import Holding, PriceRecord
from app.metrics.quality import DataQualitySummary, TickerQuality, compute_data_quality
from app.reports.builder import build_daily_report, build_weekly_report
from app.reports.models import DailyReport, WeeklyReport


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_DATE = "2024-01-15"
_WEEK_START = "2024-01-08"


def _holding(ticker: str, qty: float = 10.0, cost: float = 100.0) -> Holding:
    return Holding(ticker=ticker, quantity=qty, cost_basis=cost)


def _price(ticker: str, price_date: str, close: float = 100.0) -> PriceRecord:
    return PriceRecord(ticker=ticker, price_date=price_date, close_price=close)


# ---------------------------------------------------------------------------
# compute_data_quality — empty portfolio
# ---------------------------------------------------------------------------


class TestComputeDataQualityEmpty:
    def test_empty_holdings_returns_zero_counts(self):
        result = compute_data_quality([], [], _DATE)
        assert result.total_holding_count == 0
        assert result.priced_holding_count == 0
        assert result.unpriced_holding_count == 0

    def test_empty_holdings_coverage_ratio_zero(self):
        result = compute_data_quality([], [], _DATE)
        assert result.coverage_ratio == 0.0

    def test_empty_holdings_empty_lists(self):
        result = compute_data_quality([], [], _DATE)
        assert result.unpriced_tickers == []
        assert result.ticker_quality == []

    def test_empty_holdings_report_date_stored(self):
        result = compute_data_quality([], [], _DATE)
        assert result.report_date == _DATE

    def test_result_is_frozen(self):
        result = compute_data_quality([], [], _DATE)
        import dataclasses
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
            result.total_holding_count = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# compute_data_quality — holding with no price records
# ---------------------------------------------------------------------------


class TestHoldingWithNoPriceRecords:
    def test_unpriced_holding_count_incremented(self):
        result = compute_data_quality([_holding("AAPL")], [], _DATE)
        assert result.unpriced_holding_count == 1
        assert result.priced_holding_count == 0

    def test_total_holding_count_correct(self):
        result = compute_data_quality([_holding("AAPL")], [], _DATE)
        assert result.total_holding_count == 1

    def test_coverage_ratio_zero(self):
        result = compute_data_quality([_holding("AAPL")], [], _DATE)
        assert result.coverage_ratio == 0.0

    def test_unpriced_tickers_list_populated(self):
        result = compute_data_quality([_holding("AAPL")], [], _DATE)
        assert "AAPL" in result.unpriced_tickers

    def test_ticker_quality_entry_created(self):
        result = compute_data_quality([_holding("AAPL")], [], _DATE)
        assert len(result.ticker_quality) == 1
        tq = result.ticker_quality[0]
        assert tq.ticker == "AAPL"

    def test_ticker_quality_price_record_count_zero(self):
        result = compute_data_quality([_holding("AAPL")], [], _DATE)
        tq = result.ticker_quality[0]
        assert tq.price_record_count == 0

    def test_ticker_quality_dates_are_none(self):
        result = compute_data_quality([_holding("AAPL")], [], _DATE)
        tq = result.ticker_quality[0]
        assert tq.earliest_price_date is None
        assert tq.latest_price_date is None

    def test_ticker_quality_days_since_is_none(self):
        result = compute_data_quality([_holding("AAPL")], [], _DATE)
        tq = result.ticker_quality[0]
        assert tq.days_since_last_price is None

    def test_ticker_quality_has_price_false(self):
        result = compute_data_quality([_holding("AAPL")], [], _DATE)
        tq = result.ticker_quality[0]
        assert tq.has_price_on_or_before_report_date is False

    def test_ticker_quality_is_frozen(self):
        result = compute_data_quality([_holding("AAPL")], [], _DATE)
        import dataclasses
        with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
            result.ticker_quality[0].ticker = "X"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# compute_data_quality — price records after report_date ignored for support
# ---------------------------------------------------------------------------


class TestPriceRecordsAfterReportDateIgnoredForSupport:
    def test_future_only_price_does_not_count_as_priced(self):
        prices = [_price("AAPL", "2024-01-20")]  # after report_date 2024-01-15
        result = compute_data_quality([_holding("AAPL")], prices, _DATE)
        assert result.priced_holding_count == 0
        assert result.unpriced_holding_count == 1

    def test_future_only_price_has_price_false(self):
        prices = [_price("AAPL", "2024-01-20")]
        result = compute_data_quality([_holding("AAPL")], prices, _DATE)
        tq = result.ticker_quality[0]
        assert tq.has_price_on_or_before_report_date is False

    def test_future_only_price_days_since_is_none(self):
        prices = [_price("AAPL", "2024-01-20")]
        result = compute_data_quality([_holding("AAPL")], prices, _DATE)
        tq = result.ticker_quality[0]
        assert tq.days_since_last_price is None

    def test_future_price_record_still_counted_in_price_record_count(self):
        prices = [_price("AAPL", "2024-01-20")]
        result = compute_data_quality([_holding("AAPL")], prices, _DATE)
        tq = result.ticker_quality[0]
        assert tq.price_record_count == 1

    def test_future_price_shows_in_latest_price_date(self):
        prices = [_price("AAPL", "2024-01-20")]
        result = compute_data_quality([_holding("AAPL")], prices, _DATE)
        tq = result.ticker_quality[0]
        assert tq.latest_price_date == "2024-01-20"

    def test_mix_past_and_future_uses_past_for_days_since(self):
        prices = [
            _price("AAPL", "2024-01-10"),  # before report_date
            _price("AAPL", "2024-01-20"),  # after report_date
        ]
        result = compute_data_quality([_holding("AAPL")], prices, _DATE)
        tq = result.ticker_quality[0]
        assert tq.has_price_on_or_before_report_date is True
        # days_since should use 2024-01-10, not 2024-01-20
        assert tq.days_since_last_price == 5  # 2024-01-15 - 2024-01-10


# ---------------------------------------------------------------------------
# compute_data_quality — days_since_last_price calculation
# ---------------------------------------------------------------------------


class TestDaysSinceLastPrice:
    def test_price_on_report_date_gives_zero_days(self):
        prices = [_price("AAPL", _DATE)]
        result = compute_data_quality([_holding("AAPL")], prices, _DATE)
        tq = result.ticker_quality[0]
        assert tq.days_since_last_price == 0

    def test_price_one_day_before_gives_one_day(self):
        prices = [_price("AAPL", "2024-01-14")]
        result = compute_data_quality([_holding("AAPL")], prices, _DATE)
        tq = result.ticker_quality[0]
        assert tq.days_since_last_price == 1

    def test_price_five_days_before(self):
        prices = [_price("AAPL", "2024-01-10")]
        result = compute_data_quality([_holding("AAPL")], prices, _DATE)
        tq = result.ticker_quality[0]
        assert tq.days_since_last_price == 5

    def test_most_recent_prior_date_used_when_multiple_dates(self):
        prices = [
            _price("AAPL", "2024-01-08"),
            _price("AAPL", "2024-01-12"),  # most recent on or before 2024-01-15
            _price("AAPL", "2024-01-10"),
        ]
        result = compute_data_quality([_holding("AAPL")], prices, _DATE)
        tq = result.ticker_quality[0]
        assert tq.days_since_last_price == 3  # 2024-01-15 - 2024-01-12

    def test_earliest_and_latest_dates_correct(self):
        prices = [
            _price("AAPL", "2024-01-08"),
            _price("AAPL", "2024-01-12"),
            _price("AAPL", "2024-01-10"),
        ]
        result = compute_data_quality([_holding("AAPL")], prices, _DATE)
        tq = result.ticker_quality[0]
        assert tq.earliest_price_date == "2024-01-08"
        assert tq.latest_price_date == "2024-01-12"


# ---------------------------------------------------------------------------
# compute_data_quality — portfolio coverage ratio
# ---------------------------------------------------------------------------


class TestCoverageRatio:
    def test_all_priced_coverage_ratio_one(self):
        holdings = [_holding("AAPL"), _holding("MSFT")]
        prices = [_price("AAPL", _DATE), _price("MSFT", _DATE)]
        result = compute_data_quality(holdings, prices, _DATE)
        assert result.coverage_ratio == 1.0

    def test_half_priced_coverage_ratio_half(self):
        holdings = [_holding("AAPL"), _holding("MSFT")]
        prices = [_price("AAPL", _DATE)]
        result = compute_data_quality(holdings, prices, _DATE)
        assert result.coverage_ratio == 0.5

    def test_none_priced_coverage_ratio_zero(self):
        holdings = [_holding("AAPL"), _holding("MSFT")]
        result = compute_data_quality(holdings, [], _DATE)
        assert result.coverage_ratio == 0.0

    def test_three_of_four_priced(self):
        holdings = [_holding("AAPL"), _holding("MSFT"), _holding("GOOG"), _holding("AMZN")]
        prices = [
            _price("AAPL", _DATE),
            _price("MSFT", _DATE),
            _price("GOOG", _DATE),
        ]
        result = compute_data_quality(holdings, prices, _DATE)
        assert result.coverage_ratio == pytest.approx(0.75)
        assert result.priced_holding_count == 3
        assert result.unpriced_holding_count == 1

    def test_unpriced_tickers_list_correct(self):
        holdings = [_holding("AAPL"), _holding("MSFT")]
        prices = [_price("AAPL", _DATE)]
        result = compute_data_quality(holdings, prices, _DATE)
        assert result.unpriced_tickers == ["MSFT"]


# ---------------------------------------------------------------------------
# compute_data_quality — per-ticker isolation
# ---------------------------------------------------------------------------


class TestPerTickerIsolation:
    def test_price_records_for_other_ticker_not_counted(self):
        holdings = [_holding("AAPL"), _holding("MSFT")]
        prices = [_price("AAPL", _DATE)]  # only AAPL priced
        result = compute_data_quality(holdings, prices, _DATE)
        aapl = next(tq for tq in result.ticker_quality if tq.ticker == "AAPL")
        msft = next(tq for tq in result.ticker_quality if tq.ticker == "MSFT")
        assert aapl.price_record_count == 1
        assert msft.price_record_count == 0

    def test_ticker_quality_count_equals_holding_count(self):
        holdings = [_holding("AAPL"), _holding("MSFT"), _holding("GOOG")]
        result = compute_data_quality(holdings, [], _DATE)
        assert len(result.ticker_quality) == 3

    def test_price_records_from_non_held_tickers_ignored(self):
        holdings = [_holding("AAPL")]
        prices = [_price("MSFT", _DATE)]  # MSFT not held
        result = compute_data_quality(holdings, prices, _DATE)
        assert result.priced_holding_count == 0
        assert result.ticker_quality[0].price_record_count == 0

    def test_multiple_prices_same_ticker_counted_individually(self):
        holdings = [_holding("AAPL")]
        prices = [
            _price("AAPL", "2024-01-08"),
            _price("AAPL", "2024-01-10"),
            _price("AAPL", "2024-01-12"),
            _price("AAPL", _DATE),
        ]
        result = compute_data_quality(holdings, prices, _DATE)
        assert result.ticker_quality[0].price_record_count == 4


# ---------------------------------------------------------------------------
# compute_data_quality — report_date validation
# ---------------------------------------------------------------------------


class TestReportDateValidation:
    def test_invalid_report_date_raises(self):
        with pytest.raises(InvalidDateError):
            compute_data_quality([], [], "not-a-date")

    def test_wrong_format_raises(self):
        with pytest.raises(InvalidDateError):
            compute_data_quality([], [], "15-01-2024")

    def test_valid_report_date_stored(self):
        result = compute_data_quality([_holding("AAPL")], [], "2024-06-01")
        assert result.report_date == "2024-06-01"


# ---------------------------------------------------------------------------
# Report builder integration — Data Quality Summary section
# ---------------------------------------------------------------------------


class TestDailyReportDataQualitySection:
    def _minimal_dq(self) -> DataQualitySummary:
        return compute_data_quality(
            [_holding("AAPL")],
            [_price("AAPL", _DATE)],
            _DATE,
        )

    def test_section_present_when_data_quality_provided(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        report = build_daily_report(_DATE, snap, [], [], self._minimal_dq())
        labels = [s.label for s in report.sections]
        assert "Data Quality Summary" in labels

    def test_section_absent_when_data_quality_is_none(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        report = build_daily_report(_DATE, snap, [], [], None)
        labels = [s.label for s in report.sections]
        assert "Data Quality Summary" not in labels

    def test_data_quality_field_stored_on_report(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        dq = self._minimal_dq()
        report = build_daily_report(_DATE, snap, [], [], dq)
        assert report.data_quality is dq

    def test_data_quality_none_stored_when_not_provided(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        report = build_daily_report(_DATE, snap, [], [])
        assert report.data_quality is None

    def test_section_label_passes_compliance(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        report = build_daily_report(_DATE, snap, [], [], self._minimal_dq())
        dq_section = next(
            s for s in report.sections if s.label == "Data Quality Summary"
        )
        check_compliance(dq_section.label)  # must not raise

    def test_section_body_passes_compliance(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        report = build_daily_report(_DATE, snap, [], [], self._minimal_dq())
        dq_section = next(
            s for s in report.sections if s.label == "Data Quality Summary"
        )
        check_compliance(dq_section.body)  # must not raise

    def test_section_body_no_forbidden_advisory_language(self):
        import re
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        dq = compute_data_quality(
            [_holding("AAPL"), _holding("MSFT")],
            [_price("AAPL", _DATE)],
            _DATE,
        )
        report = build_daily_report(_DATE, snap, [], [], dq)
        dq_section = next(s for s in report.sections if s.label == "Data Quality Summary")
        forbidden = re.compile(
            r"\b(buy|sell|hold|recommend|suggest|profit|guaranteed|opportunity"
            r"|target price|price prediction)\b",
            re.IGNORECASE,
        )
        assert not forbidden.search(dq_section.body), (
            f"Forbidden language in Data Quality Summary body: {dq_section.body!r}"
        )

    def test_section_placed_after_data_coverage(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        report = build_daily_report(_DATE, snap, [], [], self._minimal_dq())
        labels = [s.label for s in report.sections]
        coverage_idx = labels.index("Data Coverage")
        quality_idx = labels.index("Data Quality Summary")
        assert quality_idx == coverage_idx + 1

    def test_other_sections_still_present(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        report = build_daily_report(_DATE, snap, [], [], self._minimal_dq())
        labels = [s.label for s in report.sections]
        for expected in ("Data Coverage", "Portfolio Snapshot", "Alert Summary", "Disclaimer"):
            assert expected in labels


class TestWeeklyReportDataQualitySection:
    def _minimal_dq(self) -> DataQualitySummary:
        return compute_data_quality(
            [_holding("AAPL")],
            [_price("AAPL", _DATE)],
            _DATE,
        )

    def test_section_present_when_data_quality_provided(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        report = build_weekly_report(
            _DATE, _WEEK_START, snap, None, None, [], [], self._minimal_dq()
        )
        labels = [s.label for s in report.sections]
        assert "Data Quality Summary" in labels

    def test_section_absent_when_data_quality_is_none(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        report = build_weekly_report(_DATE, _WEEK_START, snap, None, None, [], [], None)
        labels = [s.label for s in report.sections]
        assert "Data Quality Summary" not in labels

    def test_data_quality_field_stored_on_report(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        dq = self._minimal_dq()
        report = build_weekly_report(_DATE, _WEEK_START, snap, None, None, [], [], dq)
        assert report.data_quality is dq

    def test_section_label_passes_compliance(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        report = build_weekly_report(
            _DATE, _WEEK_START, snap, None, None, [], [], self._minimal_dq()
        )
        dq_section = next(s for s in report.sections if s.label == "Data Quality Summary")
        check_compliance(dq_section.label)  # must not raise

    def test_section_body_passes_compliance(self):
        from app.metrics.results import PortfolioSnapshot
        snap = PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )
        report = build_weekly_report(
            _DATE, _WEEK_START, snap, None, None, [], [], self._minimal_dq()
        )
        dq_section = next(s for s in report.sections if s.label == "Data Quality Summary")
        check_compliance(dq_section.body)  # must not raise


# ---------------------------------------------------------------------------
# Section body content
# ---------------------------------------------------------------------------


class TestDataQualitySectionBodyContent:
    def _snap(self):
        from app.metrics.results import PortfolioSnapshot
        return PortfolioSnapshot(
            total_market_value=0.0, positions=[], priced_count=0, unpriced_tickers=[]
        )

    def test_body_contains_coverage_ratio(self):
        dq = compute_data_quality([_holding("AAPL")], [_price("AAPL", _DATE)], _DATE)
        report = build_daily_report(_DATE, self._snap(), [], [], dq)
        section = next(s for s in report.sections if s.label == "Data Quality Summary")
        assert "100.00%" in section.body

    def test_body_contains_priced_count(self):
        dq = compute_data_quality([_holding("AAPL")], [_price("AAPL", _DATE)], _DATE)
        report = build_daily_report(_DATE, self._snap(), [], [], dq)
        section = next(s for s in report.sections if s.label == "Data Quality Summary")
        assert "1 of 1" in section.body

    def test_body_lists_unpriced_ticker(self):
        dq = compute_data_quality(
            [_holding("AAPL"), _holding("MSFT")],
            [_price("AAPL", _DATE)],
            _DATE,
        )
        report = build_daily_report(_DATE, self._snap(), [], [], dq)
        section = next(s for s in report.sections if s.label == "Data Quality Summary")
        assert "MSFT" in section.body

    def test_body_empty_portfolio(self):
        dq = compute_data_quality([], [], _DATE)
        report = build_daily_report(_DATE, self._snap(), [], [], dq)
        section = next(s for s in report.sections if s.label == "Data Quality Summary")
        assert "No positions recorded" in section.body

    def test_body_contains_days_since_last_price(self):
        prices = [_price("AAPL", "2024-01-10")]  # 5 days before 2024-01-15
        dq = compute_data_quality([_holding("AAPL")], prices, _DATE)
        report = build_daily_report(_DATE, self._snap(), [], [], dq)
        section = next(s for s in report.sections if s.label == "Data Quality Summary")
        assert "5" in section.body

    def test_body_reports_ticker_with_no_records(self):
        dq = compute_data_quality([_holding("AAPL")], [], _DATE)
        report = build_daily_report(_DATE, self._snap(), [], [], dq)
        section = next(s for s in report.sections if s.label == "Data Quality Summary")
        assert "AAPL" in section.body
        assert "no price records" in section.body.lower()


# ---------------------------------------------------------------------------
# Purity: no system clock in quality module source
# ---------------------------------------------------------------------------


class TestQualityModulePurity:
    _QUALITY_FILE = (
        Path(__file__).parent.parent.parent / "app" / "metrics" / "quality.py"
    )

    def test_quality_module_does_not_call_datetime_now(self):
        source = self._QUALITY_FILE.read_text(encoding="utf-8")
        assert "datetime.now(" not in source
        assert ".now(" not in source

    def test_quality_module_does_not_call_date_today(self):
        source = self._QUALITY_FILE.read_text(encoding="utf-8")
        assert "date.today(" not in source
        assert ".today(" not in source

    def test_quality_module_does_not_call_time_time(self):
        source = self._QUALITY_FILE.read_text(encoding="utf-8")
        assert "time.time(" not in source

    def test_quality_module_does_not_import_sqlite3(self):
        source = self._QUALITY_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        assert not any("sqlite3" in imp for imp in imports)

    def test_quality_module_does_not_import_persistence(self):
        source = self._QUALITY_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        assert not any("data.persistence" in imp for imp in imports)

    def test_quality_module_does_not_import_adapters(self):
        source = self._QUALITY_FILE.read_text(encoding="utf-8")
        assert "data.adapters" not in source

    def test_quality_module_does_not_import_network_libraries(self):
        source = self._QUALITY_FILE.read_text(encoding="utf-8")
        for lib in ("requests", "httpx", "aiohttp", "urllib"):
            assert lib not in source
