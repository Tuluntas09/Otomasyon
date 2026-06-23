"""Unit tests for the Phase 4 pure metrics engine.

All tests are pure: no DB fixtures, no SQLite connections, no CSV parsing.
Inputs are constructed in-memory as Holding and PriceRecord objects.
All floating-point comparisons use pytest.approx.
"""

import ast
import dataclasses
import statistics
from pathlib import Path

import pytest

from app.core.models import Holding, PriceRecord
from app.metrics.engine import (
    compute_drawdown,
    compute_portfolio_snapshot,
    compute_volatility_proxy,
)
from app.metrics.results import (
    DrawdownResult,
    PortfolioSnapshot,
    PositionMetrics,
    VolatilityResult,
)

# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------


def _h(ticker: str, qty: float, cost: float) -> Holding:
    return Holding(ticker=ticker, quantity=qty, cost_basis=cost)


def _p(ticker: str, date: str, close: float) -> PriceRecord:
    return PriceRecord(ticker=ticker, price_date=date, close_price=close)


# ---------------------------------------------------------------------------
# compute_portfolio_snapshot — M-001, M-002, M-003, M-004
# ---------------------------------------------------------------------------


class TestComputePortfolioSnapshot:
    def test_empty_holdings(self):
        result = compute_portfolio_snapshot([], [])
        assert isinstance(result, PortfolioSnapshot)
        assert result.total_market_value == pytest.approx(0.0)
        assert result.positions == []
        assert result.priced_count == 0
        assert result.unpriced_tickers == []

    def test_single_priced_holding(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [_p("AAPL", "2024-01-15", 150.0)]
        result = compute_portfolio_snapshot(holdings, prices)
        assert result.total_market_value == pytest.approx(1500.0)
        assert result.priced_count == 1
        assert result.unpriced_tickers == []
        pos = result.positions[0]
        assert pos.ticker == "AAPL"
        assert pos.quantity == pytest.approx(10.0)
        assert pos.cost_basis_per_unit == pytest.approx(100.0)
        assert pos.total_cost_basis == pytest.approx(1000.0)
        assert pos.market_value == pytest.approx(1500.0)
        assert pos.weight == pytest.approx(1.0)

    def test_two_equal_weight_holdings(self):
        holdings = [_h("AAPL", 10.0, 100.0), _h("MSFT", 10.0, 100.0)]
        prices = [_p("AAPL", "2024-01-15", 100.0), _p("MSFT", "2024-01-15", 100.0)]
        result = compute_portfolio_snapshot(holdings, prices)
        assert result.total_market_value == pytest.approx(2000.0)
        weights = {pos.ticker: pos.weight for pos in result.positions}
        assert weights["AAPL"] == pytest.approx(0.5)
        assert weights["MSFT"] == pytest.approx(0.5)

    def test_two_unequal_weight_holdings(self):
        # AAPL: 10 * 300 = 3000, MSFT: 5 * 200 = 1000, total = 4000
        holdings = [_h("AAPL", 10.0, 100.0), _h("MSFT", 5.0, 100.0)]
        prices = [_p("AAPL", "2024-01-15", 300.0), _p("MSFT", "2024-01-15", 200.0)]
        result = compute_portfolio_snapshot(holdings, prices)
        assert result.total_market_value == pytest.approx(4000.0)
        weights = {pos.ticker: pos.weight for pos in result.positions}
        assert weights["AAPL"] == pytest.approx(3000.0 / 4000.0)
        assert weights["MSFT"] == pytest.approx(1000.0 / 4000.0)

    def test_weights_sum_to_one_when_all_priced(self):
        holdings = [_h("AAPL", 7.0, 100.0), _h("MSFT", 3.0, 200.0), _h("GOOG", 5.0, 150.0)]
        prices = [
            _p("AAPL", "2024-01-15", 180.0),
            _p("MSFT", "2024-01-15", 420.0),
            _p("GOOG", "2024-01-15", 160.0),
        ]
        result = compute_portfolio_snapshot(holdings, prices)
        total_weight = sum(pos.weight for pos in result.positions if pos.weight is not None)
        assert total_weight == pytest.approx(1.0)

    def test_holding_with_no_price(self):
        holdings = [_h("AAPL", 10.0, 100.0), _h("MSFT", 5.0, 100.0)]
        prices = [_p("AAPL", "2024-01-15", 150.0)]  # no MSFT price
        result = compute_portfolio_snapshot(holdings, prices)
        assert result.priced_count == 1
        assert result.unpriced_tickers == ["MSFT"]
        msft_pos = next(p for p in result.positions if p.ticker == "MSFT")
        assert msft_pos.market_value is None
        assert msft_pos.weight is None
        assert msft_pos.unrealised_change_usd is None
        assert msft_pos.unrealised_change_pct is None

    def test_all_holdings_unpriced(self):
        holdings = [_h("AAPL", 10.0, 100.0), _h("MSFT", 5.0, 100.0)]
        result = compute_portfolio_snapshot(holdings, [])
        assert result.total_market_value == pytest.approx(0.0)
        assert result.priced_count == 0
        assert set(result.unpriced_tickers) == {"AAPL", "MSFT"}
        for pos in result.positions:
            assert pos.market_value is None
            assert pos.weight is None

    def test_total_cost_basis_no_price_required(self):
        holdings = [_h("AAPL", 10.0, 150.0)]
        result = compute_portfolio_snapshot(holdings, [])
        pos = result.positions[0]
        assert pos.total_cost_basis == pytest.approx(1500.0)

    def test_positive_unrealised_change(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [_p("AAPL", "2024-01-15", 150.0)]
        result = compute_portfolio_snapshot(holdings, prices)
        pos = result.positions[0]
        assert pos.unrealised_change_usd == pytest.approx(500.0)  # (150-100)*10
        assert pos.unrealised_change_pct == pytest.approx(0.5)    # (150-100)/100

    def test_negative_unrealised_change(self):
        holdings = [_h("AAPL", 10.0, 200.0)]
        prices = [_p("AAPL", "2024-01-15", 150.0)]
        result = compute_portfolio_snapshot(holdings, prices)
        pos = result.positions[0]
        assert pos.unrealised_change_usd == pytest.approx(-500.0)  # (150-200)*10
        assert pos.unrealised_change_pct == pytest.approx(-0.25)   # (150-200)/200

    def test_zero_cost_basis_gives_unrealised_change_pct_none(self):
        holdings = [_h("FREE", 5.0, 0.0)]
        prices = [_p("FREE", "2024-01-15", 100.0)]
        result = compute_portfolio_snapshot(holdings, prices)
        pos = result.positions[0]
        assert pos.unrealised_change_usd == pytest.approx(500.0)  # (100-0)*5
        assert pos.unrealised_change_pct is None

    def test_no_price_gives_unrealised_change_fields_none(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        result = compute_portfolio_snapshot(holdings, [])
        pos = result.positions[0]
        assert pos.unrealised_change_usd is None
        assert pos.unrealised_change_pct is None

    def test_latest_price_per_ticker_is_used(self):
        # Two price records for AAPL; the later date must be used
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),  # older
            _p("AAPL", "2024-01-15", 200.0),  # latest — must be used
        ]
        result = compute_portfolio_snapshot(holdings, prices)
        assert result.total_market_value == pytest.approx(2000.0)
        assert result.positions[0].market_value == pytest.approx(2000.0)

    def test_position_order_matches_holdings_order(self):
        holdings = [_h("GOOG", 1.0, 100.0), _h("AAPL", 2.0, 100.0), _h("MSFT", 3.0, 100.0)]
        prices = [
            _p("AAPL", "2024-01-15", 100.0),
            _p("MSFT", "2024-01-15", 100.0),
            _p("GOOG", "2024-01-15", 100.0),
        ]
        result = compute_portfolio_snapshot(holdings, prices)
        tickers = [pos.ticker for pos in result.positions]
        assert tickers == ["GOOG", "AAPL", "MSFT"]


# ---------------------------------------------------------------------------
# compute_drawdown — M-005
# ---------------------------------------------------------------------------


class TestComputeDrawdown:
    def test_empty_holdings_returns_none(self):
        prices = [_p("AAPL", "2024-01-15", 100.0)]
        assert compute_drawdown([], prices) is None

    def test_no_prices_returns_none(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        assert compute_drawdown(holdings, []) is None

    def test_single_date_returns_zero_drawdown(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [_p("AAPL", "2024-01-15", 150.0)]
        result = compute_drawdown(holdings, prices, window_days=90)
        assert result is not None
        assert result.drawdown == pytest.approx(0.0)
        assert result.dates_in_window == 1
        assert result.peak_value == pytest.approx(1500.0)
        assert result.current_value == pytest.approx(1500.0)

    def test_current_equals_peak_returns_zero(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),
            _p("AAPL", "2024-01-02", 110.0),
            _p("AAPL", "2024-01-03", 110.0),  # current == peak
        ]
        result = compute_drawdown(holdings, prices)
        assert result is not None
        assert result.drawdown == pytest.approx(0.0)
        assert result.current_value == pytest.approx(result.peak_value)

    def test_known_ten_percent_drawdown(self):
        # peak = 1000, current = 900 → drawdown = 0.1
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),  # value = 1000 (peak)
            _p("AAPL", "2024-01-02", 90.0),   # value = 900 (current)
        ]
        result = compute_drawdown(holdings, prices)
        assert result is not None
        assert result.peak_value == pytest.approx(1000.0)
        assert result.current_value == pytest.approx(900.0)
        assert result.drawdown == pytest.approx(0.1)

    def test_window_days_filters_relative_to_latest_input_date(self):
        # latest = 2024-02-20; window_days=20 → cutoff = 2024-01-31
        # 2024-01-01 is excluded; 2024-02-01 and 2024-02-20 are included
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("AAPL", "2024-01-01", 200.0),  # old peak — excluded by window
            _p("AAPL", "2024-02-01", 150.0),  # peak in window
            _p("AAPL", "2024-02-20", 120.0),  # current (latest)
        ]
        result = compute_drawdown(holdings, prices, window_days=20)
        assert result is not None
        assert result.dates_in_window == 2
        assert result.peak_value == pytest.approx(1500.0)
        assert result.current_value == pytest.approx(1200.0)
        assert result.drawdown == pytest.approx((1500.0 - 1200.0) / 1500.0)

    def test_result_contains_correct_window_days(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),
            _p("AAPL", "2024-01-02", 90.0),
        ]
        result = compute_drawdown(holdings, prices, window_days=45)
        assert result is not None
        assert result.window_days == 45

    def test_partial_coverage_reports_min_and_latest_coverage_ratio(self):
        # Two holdings; AAPL has prices on both dates, MSFT only on the second
        holdings = [_h("AAPL", 10.0, 100.0), _h("MSFT", 5.0, 200.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),  # coverage = 1/2 = 0.5
            _p("AAPL", "2024-01-02", 100.0),
            _p("MSFT", "2024-01-02", 200.0),  # coverage = 2/2 = 1.0
        ]
        result = compute_drawdown(holdings, prices, window_days=90)
        assert result is not None
        assert result.min_coverage_ratio == pytest.approx(0.5)
        assert result.latest_coverage_ratio == pytest.approx(1.0)

    def test_full_coverage_reports_one_point_zero(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [_p("AAPL", "2024-01-15", 100.0)]
        result = compute_drawdown(holdings, prices)
        assert result is not None
        assert result.min_coverage_ratio == pytest.approx(1.0)
        assert result.latest_coverage_ratio == pytest.approx(1.0)

    def test_multi_holding_drawdown(self):
        # Day 1: AAPL=100*10=1000, MSFT=200*5=1000 → total=2000 (peak)
        # Day 2: AAPL=90*10=900,  MSFT=180*5=900  → total=1800 (current)
        # drawdown = 200/2000 = 0.1
        holdings = [_h("AAPL", 10.0, 100.0), _h("MSFT", 5.0, 200.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),
            _p("MSFT", "2024-01-01", 200.0),
            _p("AAPL", "2024-01-02", 90.0),
            _p("MSFT", "2024-01-02", 180.0),
        ]
        result = compute_drawdown(holdings, prices)
        assert result is not None
        assert result.peak_value == pytest.approx(2000.0)
        assert result.current_value == pytest.approx(1800.0)
        assert result.drawdown == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# compute_volatility_proxy — M-006
# ---------------------------------------------------------------------------


class TestComputeVolatilityProxy:
    def test_empty_holdings_returns_none(self):
        prices = [_p("AAPL", "2024-01-15", 100.0)]
        assert compute_volatility_proxy([], prices) is None

    def test_no_prices_returns_none(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        assert compute_volatility_proxy(holdings, []) is None

    def test_single_date_returns_none(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [_p("AAPL", "2024-01-15", 100.0)]
        assert compute_volatility_proxy(holdings, prices) is None

    def test_constant_portfolio_value_returns_zero_volatility(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),
            _p("AAPL", "2024-01-02", 100.0),
            _p("AAPL", "2024-01-03", 100.0),
        ]
        result = compute_volatility_proxy(holdings, prices)
        assert result is not None
        assert result.volatility_proxy == pytest.approx(0.0)

    def test_known_returns_produce_expected_pstdev(self):
        # portfolio values: 1000, 1100, 990
        # daily returns: (1100-1000)/1000 = 0.1, (990-1100)/1100 ≈ -0.1
        # For clean math use: 1000 → 1100 → 1100*0.9 ... actually let's pick exact values:
        # values: 1000, 1100, 990 → returns: [0.1, -10/110]
        # Use simpler: values 1000, 1100, 900
        # returns: [0.1, (900-1100)/1100] = [0.1, -2/11]
        # pstdev([0.1, -2/11]) — not clean.
        # Use values: 1000, 1100, 1100 * (1 - 0.1) ... no, use price 1000 → 1100 → 990
        # Actually the cleanest: portfolio = 1000, 1100, 1000
        # returns = [0.1, (1000-1100)/1100] = [0.1, -1/11]
        # Also not clean. Let's use symmetric: 1000, 1100, 900
        # returns = [0.1, (900-1100)/1100] ≈ [0.1, -0.18182]
        # pstdev is messy.
        #
        # Use the cleanest possible: 1000 → 1100 → 1100 (flat for second step)
        # returns = [0.1, 0.0] → pstdev([0.1, 0.0]) = pstdev = 0.05
        # Verify: mean=0.05, deviations=[0.05, -0.05], sq=[0.0025, 0.0025], var=0.0025, sd=0.05 ✓
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),   # value = 1000
            _p("AAPL", "2024-01-02", 110.0),   # value = 1100, return = 0.1
            _p("AAPL", "2024-01-03", 110.0),   # value = 1100, return = 0.0
        ]
        result = compute_volatility_proxy(holdings, prices)
        assert result is not None
        expected = statistics.pstdev([0.1, 0.0])
        assert result.volatility_proxy == pytest.approx(expected)

    def test_symmetric_returns_produce_expected_pstdev(self):
        # values: 1000 → 1100 → 990  (from portfolio)
        # returns: [0.1, -0.1]
        # pstdev([0.1, -0.1]): mean=0.0, pvar=0.01, pstdev=0.1
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),  # value = 1000
            _p("AAPL", "2024-01-02", 110.0),  # value = 1100, return = +0.1
            _p("AAPL", "2024-01-03", 99.0),   # value = 990,  return = -10/110 ≈ -0.0909
        ]
        # returns = [0.1, (990-1100)/1100]
        # pstdev([0.1, -10/110]) — let's compute exactly:
        r1, r2 = 0.1, (990.0 - 1100.0) / 1100.0
        result = compute_volatility_proxy(holdings, prices)
        assert result is not None
        assert result.volatility_proxy == pytest.approx(statistics.pstdev([r1, r2]))

    def test_window_days_filters_relative_to_latest_input_date(self):
        # latest = 2024-02-20; window_days=10 → cutoff = 2024-02-10
        # Only 2024-02-15 and 2024-02-20 fall in window; 2024-01-01 excluded
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),  # outside window
            _p("AAPL", "2024-02-15", 110.0),  # in window
            _p("AAPL", "2024-02-20", 120.0),  # in window (latest)
        ]
        result = compute_volatility_proxy(holdings, prices, window_days=10)
        assert result is not None
        assert result.returns_count == 1  # one return from 2 dates
        expected_return = (120.0 * 10 - 110.0 * 10) / (110.0 * 10)
        assert result.volatility_proxy == pytest.approx(statistics.pstdev([expected_return]))

    def test_zero_previous_value_return_is_skipped(self):
        # Portfolio value of zero on day 1 means day 1→2 return is skipped.
        # Only tickers NOT in holdings can produce a zero-value day in practice,
        # but we test the skipping logic via a price record for an unknown ticker.
        # Use two valid holdings days with one "bad" day in between where holdings
        # aren't priced (portfolio_value=0 for that date if prices only cover
        # a ticker not in holdings).
        # Simpler: directly supply a price for a ticker not in holdings to create
        # a date-slot with portfolio_value=0.
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("MSFT", "2024-01-01", 100.0),  # creates a date, but MSFT not in holdings → value=0
            _p("AAPL", "2024-01-02", 100.0),  # value=1000
            _p("AAPL", "2024-01-03", 110.0),  # value=1100, return=(1100-1000)/1000=0.1
        ]
        result = compute_volatility_proxy(holdings, prices)
        assert result is not None
        # day1→day2 return has prev_value=0 → skipped
        # day2→day3 return = (1100-1000)/1000 = 0.1
        assert result.returns_count == 1
        assert result.volatility_proxy == pytest.approx(statistics.pstdev([0.1]))

    def test_returns_count_reported_correctly(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),
            _p("AAPL", "2024-01-02", 110.0),
            _p("AAPL", "2024-01-03", 120.0),
            _p("AAPL", "2024-01-04", 130.0),
        ]
        result = compute_volatility_proxy(holdings, prices)
        assert result is not None
        assert result.returns_count == 3  # 4 dates → 3 returns

    def test_partial_coverage_min_and_latest_coverage_ratio(self):
        # Two holdings; AAPL only on day 1, both on day 2
        holdings = [_h("AAPL", 10.0, 100.0), _h("MSFT", 5.0, 200.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),  # coverage = 0.5
            _p("AAPL", "2024-01-02", 110.0),
            _p("MSFT", "2024-01-02", 200.0),  # coverage = 1.0
        ]
        result = compute_volatility_proxy(holdings, prices)
        assert result is not None
        assert result.min_coverage_ratio == pytest.approx(0.5)
        assert result.latest_coverage_ratio == pytest.approx(1.0)

    def test_result_contains_correct_window_days(self):
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("AAPL", "2024-01-01", 100.0),
            _p("AAPL", "2024-01-02", 110.0),
        ]
        result = compute_volatility_proxy(holdings, prices, window_days=30)
        assert result is not None
        assert result.window_days == 30

    def test_all_zero_returns_skipped_gives_none(self):
        # Only a ticker NOT in holdings produces value=0 for every date,
        # so every day→day return has prev=0 → all skipped → return None.
        holdings = [_h("AAPL", 10.0, 100.0)]
        prices = [
            _p("MSFT", "2024-01-01", 100.0),  # value=0 (MSFT not in holdings)
            _p("MSFT", "2024-01-02", 110.0),  # value=0
            _p("MSFT", "2024-01-03", 120.0),  # value=0
        ]
        # All portfolio values are 0 → all returns have prev_value=0 → skipped → None
        assert compute_volatility_proxy(holdings, prices) is None


# ---------------------------------------------------------------------------
# Boundary / purity tests
# ---------------------------------------------------------------------------

def _metrics_source_files() -> list[Path]:
    tests_unit = Path(__file__).parent
    backend = tests_unit.parent.parent
    metrics_dir = backend / "app" / "metrics"
    return [f for f in metrics_dir.glob("*.py") if f.stem != "__pycache__"]


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


def test_metrics_does_not_import_sqlite3():
    for src_file in _metrics_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            assert "sqlite3" not in imp, f"{src_file.name} imports sqlite3"


def test_metrics_does_not_import_csv():
    for src_file in _metrics_source_files():
        imports = _collect_imports(src_file)
        assert "csv" not in imports, f"{src_file.name} imports csv"


def test_metrics_does_not_import_os():
    for src_file in _metrics_source_files():
        imports = _collect_imports(src_file)
        assert not any(
            imp == "os" or imp.startswith("os.") for imp in imports
        ), f"{src_file.name} imports os"


def test_metrics_does_not_import_pathlib():
    for src_file in _metrics_source_files():
        imports = _collect_imports(src_file)
        assert "pathlib" not in imports, f"{src_file.name} imports pathlib"


def test_metrics_does_not_import_persistence():
    for src_file in _metrics_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            assert "data.persistence" not in imp, (
                f"{src_file.name} imports from data.persistence: {imp}"
            )


def test_metrics_does_not_import_adapters():
    for src_file in _metrics_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            assert "data.adapters" not in imp, (
                f"{src_file.name} imports from data.adapters: {imp}"
            )


def test_metrics_does_not_import_network_libraries():
    forbidden_roots = {"requests", "httpx", "aiohttp", "urllib3"}
    for src_file in _metrics_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            root = imp.split(".")[0]
            assert root not in forbidden_roots, (
                f"{src_file.name} imports network library: {imp}"
            )


def test_no_result_field_uses_profit_or_loss():
    for cls in [PositionMetrics, PortfolioSnapshot, DrawdownResult, VolatilityResult]:
        for f in dataclasses.fields(cls):
            assert "profit" not in f.name, (
                f"Field {f.name!r} in {cls.__name__} uses 'profit'"
            )
            assert "loss" not in f.name, (
                f"Field {f.name!r} in {cls.__name__} uses 'loss'"
            )
