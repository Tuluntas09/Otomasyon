"""Unit tests for the Phase 5 alert engine.

All tests are pure: no DB fixtures, no file I/O, no CSV parsing.
Inputs are constructed in-memory from metrics result dataclasses.
"""

import ast
import dataclasses
from pathlib import Path

import pytest

from app.alerts.results import AlertConfig, AlertResult
from app.alerts.rules import evaluate_alerts
from app.compliance.guard import check_compliance
from app.core.exceptions import ComplianceViolationError
from app.metrics.results import (
    DrawdownResult,
    PortfolioSnapshot,
    PositionMetrics,
    VolatilityResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pos(ticker: str, weight: float | None, qty: float = 10.0, cost: float = 100.0) -> PositionMetrics:
    mv = qty * cost if weight is not None else None
    return PositionMetrics(
        ticker=ticker,
        quantity=qty,
        cost_basis_per_unit=cost,
        total_cost_basis=qty * cost,
        market_value=mv,
        weight=weight,
        unrealised_change_usd=None,
        unrealised_change_pct=None,
    )


def _snapshot(positions: list[PositionMetrics], unpriced: list[str] | None = None) -> PortfolioSnapshot:
    total_mv = sum(p.market_value for p in positions if p.market_value is not None)
    priced = sum(1 for p in positions if p.market_value is not None)
    return PortfolioSnapshot(
        total_market_value=total_mv,
        positions=positions,
        priced_count=priced,
        unpriced_tickers=unpriced or [],
    )


def _drawdown(dd: float, window: int = 90) -> DrawdownResult:
    peak = 1.0
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


def _volatility(vp: float, window: int = 30) -> VolatilityResult:
    return VolatilityResult(
        volatility_proxy=vp,
        window_days=window,
        returns_count=window - 1,
        min_coverage_ratio=1.0,
        latest_coverage_ratio=1.0,
    )


def _empty_snapshot() -> PortfolioSnapshot:
    return PortfolioSnapshot(
        total_market_value=0.0,
        positions=[],
        priced_count=0,
        unpriced_tickers=[],
    )


# ---------------------------------------------------------------------------
# Dataclass structure
# ---------------------------------------------------------------------------


def test_alert_config_is_frozen():
    config = AlertConfig()
    with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
        config.concentration_ceiling = 0.5  # type: ignore[misc]


def test_alert_result_is_frozen():
    result = AlertResult(
        rule_id="CONC-001",
        fired=False,
        severity="informational",
        metric_value=0.0,
        threshold=0.25,
        explanation="test",
        ticker=None,
    )
    with pytest.raises((dataclasses.FrozenInstanceError, TypeError)):
        result.fired = True  # type: ignore[misc]


def test_default_thresholds():
    config = AlertConfig()
    assert config.concentration_ceiling == pytest.approx(0.25)
    assert config.drawdown_ceiling == pytest.approx(0.15)
    assert config.volatility_ceiling == pytest.approx(0.02)
    assert config.max_unpriced_holdings == 0


# ---------------------------------------------------------------------------
# evaluate_alerts — returns results for all four rule families
# ---------------------------------------------------------------------------


def test_evaluate_alerts_returns_all_four_rule_families():
    snapshot = _empty_snapshot()
    results = evaluate_alerts(snapshot, None, None)
    rule_ids = [r.rule_id for r in results]
    assert "CONC-001" in rule_ids
    assert "DD-001" in rule_ids
    assert "VOL-001" in rule_ids
    assert "COV-001" in rule_ids


# ---------------------------------------------------------------------------
# CONC-001
# ---------------------------------------------------------------------------


def test_conc_fires_when_weight_above_threshold():
    snapshot = _snapshot([_pos("AAPL", 0.30)])
    results = evaluate_alerts(snapshot, None, None)
    conc = [r for r in results if r.rule_id == "CONC-001"]
    assert any(r.fired for r in conc)


def test_conc_does_not_fire_below_threshold():
    snapshot = _snapshot([_pos("AAPL", 0.20)])
    results = evaluate_alerts(snapshot, None, None)
    conc = [r for r in results if r.rule_id == "CONC-001"]
    assert all(not r.fired for r in conc)


def test_conc_does_not_fire_at_exact_threshold():
    # Exact equality must NOT fire (D-043)
    config = AlertConfig(concentration_ceiling=0.25)
    snapshot = _snapshot([_pos("AAPL", 0.25)])
    results = evaluate_alerts(snapshot, None, None, config)
    conc = [r for r in results if r.rule_id == "CONC-001"]
    assert all(not r.fired for r in conc)
    assert all(r.severity == "informational" for r in conc)


def test_conc_multiple_positions_only_breaching_fire():
    config = AlertConfig(concentration_ceiling=0.25)
    snapshot = _snapshot([
        _pos("AAPL", 0.30),   # above threshold — fires
        _pos("MSFT", 0.20),   # below threshold — does not fire
        _pos("GOOG", 0.50),   # above threshold — fires
    ])
    results = evaluate_alerts(snapshot, None, None, config)
    conc = [r for r in results if r.rule_id == "CONC-001"]
    fired_tickers = {r.ticker for r in conc if r.fired}
    assert "AAPL" in fired_tickers
    assert "GOOG" in fired_tickers
    assert "MSFT" not in fired_tickers


def test_conc_no_priced_positions_returns_informational():
    snapshot = _snapshot([_pos("AAPL", None)])
    results = evaluate_alerts(snapshot, None, None)
    conc = [r for r in results if r.rule_id == "CONC-001"]
    assert len(conc) == 1
    assert not conc[0].fired
    assert conc[0].severity == "informational"
    assert conc[0].ticker is None


def test_conc_fired_result_has_ticker_populated():
    snapshot = _snapshot([_pos("AAPL", 0.30)])
    results = evaluate_alerts(snapshot, None, None)
    conc_fired = [r for r in results if r.rule_id == "CONC-001" and r.fired]
    assert len(conc_fired) == 1
    assert conc_fired[0].ticker == "AAPL"


# ---------------------------------------------------------------------------
# DD-001
# ---------------------------------------------------------------------------


def test_dd_fires_when_drawdown_above_threshold():
    config = AlertConfig(drawdown_ceiling=0.15)
    dd = _drawdown(0.20)
    results = evaluate_alerts(_empty_snapshot(), dd, None, config)
    dd_result = next(r for r in results if r.rule_id == "DD-001")
    assert dd_result.fired


def test_dd_does_not_fire_below_threshold():
    config = AlertConfig(drawdown_ceiling=0.15)
    dd = _drawdown(0.10)
    results = evaluate_alerts(_empty_snapshot(), dd, None, config)
    dd_result = next(r for r in results if r.rule_id == "DD-001")
    assert not dd_result.fired


def test_dd_does_not_fire_at_exact_threshold():
    # Exact equality must NOT fire (D-043)
    config = AlertConfig(drawdown_ceiling=0.15)
    dd = _drawdown(0.15)
    results = evaluate_alerts(_empty_snapshot(), dd, None, config)
    dd_result = next(r for r in results if r.rule_id == "DD-001")
    assert not dd_result.fired
    assert dd_result.severity == "informational"


def test_dd_none_returns_informational():
    results = evaluate_alerts(_empty_snapshot(), None, None)
    dd_result = next(r for r in results if r.rule_id == "DD-001")
    assert not dd_result.fired
    assert dd_result.severity == "informational"
    assert dd_result.metric_value == pytest.approx(0.0)


def test_dd_ticker_is_none():
    dd = _drawdown(0.20)
    results = evaluate_alerts(_empty_snapshot(), dd, None)
    dd_result = next(r for r in results if r.rule_id == "DD-001")
    assert dd_result.ticker is None


# ---------------------------------------------------------------------------
# VOL-001
# ---------------------------------------------------------------------------


def test_vol_fires_when_volatility_above_threshold():
    config = AlertConfig(volatility_ceiling=0.02)
    vol = _volatility(0.03)
    results = evaluate_alerts(_empty_snapshot(), None, vol, config)
    vol_result = next(r for r in results if r.rule_id == "VOL-001")
    assert vol_result.fired


def test_vol_does_not_fire_below_threshold():
    config = AlertConfig(volatility_ceiling=0.02)
    vol = _volatility(0.01)
    results = evaluate_alerts(_empty_snapshot(), None, vol, config)
    vol_result = next(r for r in results if r.rule_id == "VOL-001")
    assert not vol_result.fired


def test_vol_does_not_fire_at_exact_threshold():
    # Exact equality must NOT fire (D-043)
    config = AlertConfig(volatility_ceiling=0.02)
    vol = _volatility(0.02)
    results = evaluate_alerts(_empty_snapshot(), None, vol, config)
    vol_result = next(r for r in results if r.rule_id == "VOL-001")
    assert not vol_result.fired
    assert vol_result.severity == "informational"


def test_vol_none_returns_informational():
    results = evaluate_alerts(_empty_snapshot(), None, None)
    vol_result = next(r for r in results if r.rule_id == "VOL-001")
    assert not vol_result.fired
    assert vol_result.severity == "informational"
    assert vol_result.metric_value == pytest.approx(0.0)


def test_vol_ticker_is_none():
    vol = _volatility(0.03)
    results = evaluate_alerts(_empty_snapshot(), None, vol)
    vol_result = next(r for r in results if r.rule_id == "VOL-001")
    assert vol_result.ticker is None


# ---------------------------------------------------------------------------
# COV-001
# ---------------------------------------------------------------------------


def test_cov_fires_when_unpriced_count_above_max():
    config = AlertConfig(max_unpriced_holdings=0)
    snapshot = PortfolioSnapshot(
        total_market_value=0.0,
        positions=[],
        priced_count=0,
        unpriced_tickers=["AAPL"],
    )
    results = evaluate_alerts(snapshot, None, None, config)
    cov = next(r for r in results if r.rule_id == "COV-001")
    assert cov.fired


def test_cov_does_not_fire_when_count_equals_max():
    # Exact equality must NOT fire (D-043)
    config = AlertConfig(max_unpriced_holdings=1)
    snapshot = PortfolioSnapshot(
        total_market_value=0.0,
        positions=[],
        priced_count=0,
        unpriced_tickers=["AAPL"],
    )
    results = evaluate_alerts(snapshot, None, None, config)
    cov = next(r for r in results if r.rule_id == "COV-001")
    assert not cov.fired
    assert cov.severity == "informational"


def test_cov_does_not_fire_below_max():
    config = AlertConfig(max_unpriced_holdings=2)
    snapshot = PortfolioSnapshot(
        total_market_value=0.0,
        positions=[],
        priced_count=0,
        unpriced_tickers=["AAPL"],
    )
    results = evaluate_alerts(snapshot, None, None, config)
    cov = next(r for r in results if r.rule_id == "COV-001")
    assert not cov.fired


# ---------------------------------------------------------------------------
# Severity policy
# ---------------------------------------------------------------------------


def test_fired_alerts_have_severity_watch_or_elevated():
    config = AlertConfig(concentration_ceiling=0.25, drawdown_ceiling=0.15)
    snapshot = _snapshot([_pos("AAPL", 0.30)])
    dd = _drawdown(0.20)
    results = evaluate_alerts(snapshot, dd, None, config)
    for r in results:
        if r.fired:
            assert r.severity in ("watch", "elevated"), (
                f"{r.rule_id} fired but has severity {r.severity!r}"
            )


def test_non_fired_alerts_have_severity_informational():
    snapshot = _snapshot([_pos("AAPL", 0.10)])
    results = evaluate_alerts(snapshot, None, None)
    for r in results:
        if not r.fired:
            assert r.severity == "informational", (
                f"{r.rule_id} did not fire but has severity {r.severity!r}"
            )


def test_elevated_severity_when_value_greater_than_2x_threshold():
    # CONC-001: ceiling=0.25, weight=0.60 → 0.60 > 2*0.25=0.50 → elevated
    config = AlertConfig(concentration_ceiling=0.25)
    snapshot = _snapshot([_pos("AAPL", 0.60)])
    results = evaluate_alerts(snapshot, None, None, config)
    conc_fired = [r for r in results if r.rule_id == "CONC-001" and r.fired]
    assert len(conc_fired) == 1
    assert conc_fired[0].severity == "elevated"


def test_watch_severity_when_value_not_greater_than_2x_threshold():
    # CONC-001: ceiling=0.25, weight=0.30 → 0.30 < 2*0.25=0.50 → watch
    config = AlertConfig(concentration_ceiling=0.25)
    snapshot = _snapshot([_pos("AAPL", 0.30)])
    results = evaluate_alerts(snapshot, None, None, config)
    conc_fired = [r for r in results if r.rule_id == "CONC-001" and r.fired]
    assert len(conc_fired) == 1
    assert conc_fired[0].severity == "watch"


def test_cov_threshold_zero_uses_watch_when_fired():
    # COV-001 with max_unpriced_holdings==0: 2×threshold is undefined → watch
    config = AlertConfig(max_unpriced_holdings=0)
    snapshot = PortfolioSnapshot(
        total_market_value=0.0,
        positions=[],
        priced_count=0,
        unpriced_tickers=["AAPL"],
    )
    results = evaluate_alerts(snapshot, None, None, config)
    cov = next(r for r in results if r.rule_id == "COV-001")
    assert cov.fired
    assert cov.severity == "watch"


# ---------------------------------------------------------------------------
# Custom AlertConfig
# ---------------------------------------------------------------------------


def test_custom_config_changes_thresholds():
    config = AlertConfig(
        concentration_ceiling=0.10,
        drawdown_ceiling=0.05,
        volatility_ceiling=0.01,
        max_unpriced_holdings=3,
    )
    # Weight 0.15 fires with ceiling=0.10 but would not fire with default 0.25
    snapshot = _snapshot([_pos("AAPL", 0.15)])
    results = evaluate_alerts(snapshot, None, None, config)
    conc = [r for r in results if r.rule_id == "CONC-001" and r.fired]
    assert len(conc) == 1
    assert conc[0].threshold == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# Compliance integration
# ---------------------------------------------------------------------------


def test_every_explanation_passes_compliance():
    config = AlertConfig(
        concentration_ceiling=0.25,
        drawdown_ceiling=0.15,
        volatility_ceiling=0.02,
        max_unpriced_holdings=0,
    )
    snapshot = _snapshot([
        _pos("AAPL", 0.30),
        _pos("MSFT", 0.10),
        _pos("UNPRICED", None),
    ], unpriced=["UNPRICED"])
    dd = _drawdown(0.20)
    vol = _volatility(0.03)
    results = evaluate_alerts(snapshot, dd, vol, config)
    for r in results:
        # Must not raise
        check_compliance(r.explanation)


def test_every_explanation_passes_compliance_all_unfired():
    config = AlertConfig()
    snapshot = _snapshot([_pos("AAPL", 0.10)])
    dd = _drawdown(0.05)
    vol = _volatility(0.01)
    results = evaluate_alerts(snapshot, dd, vol, config)
    for r in results:
        check_compliance(r.explanation)


# ---------------------------------------------------------------------------
# Boundary / purity — alert engine source files
# ---------------------------------------------------------------------------


def _alerts_source_files() -> list[Path]:
    tests_unit = Path(__file__).parent
    backend = tests_unit.parent.parent
    alerts_dir = backend / "app" / "alerts"
    return [f for f in alerts_dir.glob("*.py") if f.stem != "__pycache__"]


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


def test_alerts_does_not_import_sqlite3():
    for src_file in _alerts_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            assert "sqlite3" not in imp, f"{src_file.name} imports sqlite3"


def test_alerts_does_not_import_csv():
    for src_file in _alerts_source_files():
        imports = _collect_imports(src_file)
        assert "csv" not in imports, f"{src_file.name} imports csv"


def test_alerts_does_not_import_os():
    for src_file in _alerts_source_files():
        imports = _collect_imports(src_file)
        assert not any(
            imp == "os" or imp.startswith("os.") for imp in imports
        ), f"{src_file.name} imports os"


def test_alerts_does_not_import_pathlib():
    for src_file in _alerts_source_files():
        imports = _collect_imports(src_file)
        assert not any(
            imp == "pathlib" or imp.startswith("pathlib.") for imp in imports
        ), f"{src_file.name} imports pathlib"


def test_alerts_does_not_import_network_libraries():
    forbidden_prefixes = ("requests", "httpx", "aiohttp", "urllib", "http.client")
    for src_file in _alerts_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            for prefix in forbidden_prefixes:
                assert not (imp == prefix or imp.startswith(prefix + ".")), (
                    f"{src_file.name} imports network library: {imp}"
                )


def test_alerts_does_not_import_persistence():
    for src_file in _alerts_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            assert "data.persistence" not in imp, (
                f"{src_file.name} imports persistence layer: {imp}"
            )


def test_alerts_does_not_import_adapters():
    for src_file in _alerts_source_files():
        imports = _collect_imports(src_file)
        for imp in imports:
            assert "data.adapters" not in imp, (
                f"{src_file.name} imports adapter layer: {imp}"
            )
