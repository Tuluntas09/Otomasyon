"""Alert rule evaluation engine.

Consumes already-computed metric result objects (Phase 4) and AlertConfig
to produce AlertResult objects. Does not compute metrics, access I/O, or
mutate any input objects.

Threshold rule (D-043): all comparisons are strict greater-than.
  metric_value == threshold does NOT fire an alert.

Every explanation is passed through check_compliance before an AlertResult
is constructed. If check_compliance raises, the error propagates to the caller.
"""

from app.alerts.results import AlertConfig, AlertResult
from app.compliance.guard import check_compliance
from app.metrics.results import DrawdownResult, PortfolioSnapshot, VolatilityResult


# ---------------------------------------------------------------------------
# Severity helper
# ---------------------------------------------------------------------------


def _severity(value: float, threshold: float) -> str:
    """Return severity for a *fired* alert.

    When threshold == 0.0 the 2× comparison is undefined → always "watch".
    Otherwise: value > 2 * threshold → "elevated"; else → "watch".
    """
    if threshold == 0.0:
        return "watch"
    if value > 2.0 * threshold:
        return "elevated"
    return "watch"


# ---------------------------------------------------------------------------
# CONC-001 — single-position concentration
# ---------------------------------------------------------------------------


def _evaluate_conc(
    snapshot: PortfolioSnapshot, config: AlertConfig
) -> list[AlertResult]:
    priced = [p for p in snapshot.positions if p.weight is not None]

    if not priced:
        explanation = (
            "Concentration check [CONC-001]: no priced positions are available"
            " for concentration evaluation."
        )
        check_compliance(explanation)
        return [
            AlertResult(
                rule_id="CONC-001",
                fired=False,
                severity="informational",
                metric_value=0.0,
                threshold=config.concentration_ceiling,
                explanation=explanation,
                ticker=None,
            )
        ]

    fired_results: list[AlertResult] = []
    for pos in priced:
        if pos.weight > config.concentration_ceiling:  # strict greater-than (D-043)
            explanation = (
                f"Concentration alert [CONC-001]: {pos.ticker} weight is"
                f" {pos.weight:.1%}, above the single-position ceiling of"
                f" {config.concentration_ceiling:.1%}."
            )
            check_compliance(explanation)
            fired_results.append(
                AlertResult(
                    rule_id="CONC-001",
                    fired=True,
                    severity=_severity(pos.weight, config.concentration_ceiling),
                    metric_value=pos.weight,
                    threshold=config.concentration_ceiling,
                    explanation=explanation,
                    ticker=pos.ticker,
                )
            )

    if fired_results:
        return fired_results

    explanation = (
        f"Concentration check [CONC-001]: all priced positions are within the"
        f" {config.concentration_ceiling:.1%} single-position ceiling."
    )
    check_compliance(explanation)
    return [
        AlertResult(
            rule_id="CONC-001",
            fired=False,
            severity="informational",
            metric_value=0.0,
            threshold=config.concentration_ceiling,
            explanation=explanation,
            ticker=None,
        )
    ]


# ---------------------------------------------------------------------------
# DD-001 — drawdown from peak
# ---------------------------------------------------------------------------


def _evaluate_dd(
    drawdown: DrawdownResult | None, config: AlertConfig
) -> AlertResult:
    if drawdown is None:
        explanation = (
            "Drawdown check [DD-001]: insufficient price history to compute"
            " a drawdown value."
        )
        check_compliance(explanation)
        return AlertResult(
            rule_id="DD-001",
            fired=False,
            severity="informational",
            metric_value=0.0,
            threshold=config.drawdown_ceiling,
            explanation=explanation,
            ticker=None,
        )

    fired = drawdown.drawdown > config.drawdown_ceiling  # strict greater-than (D-043)
    if fired:
        explanation = (
            f"Drawdown alert [DD-001]: portfolio value is {drawdown.drawdown:.1%}"
            f" below its {drawdown.window_days}-day peak, above the"
            f" {config.drawdown_ceiling:.1%} ceiling."
        )
        severity = _severity(drawdown.drawdown, config.drawdown_ceiling)
    else:
        explanation = (
            f"Drawdown check [DD-001]: portfolio value is {drawdown.drawdown:.1%}"
            f" below its {drawdown.window_days}-day peak, within the"
            f" {config.drawdown_ceiling:.1%} ceiling."
        )
        severity = "informational"

    check_compliance(explanation)
    return AlertResult(
        rule_id="DD-001",
        fired=fired,
        severity=severity,
        metric_value=drawdown.drawdown,
        threshold=config.drawdown_ceiling,
        explanation=explanation,
        ticker=None,
    )


# ---------------------------------------------------------------------------
# VOL-001 — volatility proxy
# ---------------------------------------------------------------------------


def _evaluate_vol(
    volatility: VolatilityResult | None, config: AlertConfig
) -> AlertResult:
    if volatility is None:
        explanation = (
            "Volatility check [VOL-001]: insufficient price history to compute"
            " a volatility proxy."
        )
        check_compliance(explanation)
        return AlertResult(
            rule_id="VOL-001",
            fired=False,
            severity="informational",
            metric_value=0.0,
            threshold=config.volatility_ceiling,
            explanation=explanation,
            ticker=None,
        )

    fired = volatility.volatility_proxy > config.volatility_ceiling  # strict (D-043)
    if fired:
        explanation = (
            f"Volatility alert [VOL-001]: rolling standard deviation of daily"
            f" returns is {volatility.volatility_proxy:.2%}, above the"
            f" {config.volatility_ceiling:.2%} threshold."
        )
        severity = _severity(volatility.volatility_proxy, config.volatility_ceiling)
    else:
        explanation = (
            f"Volatility check [VOL-001]: rolling standard deviation of daily"
            f" returns is {volatility.volatility_proxy:.2%}, within the"
            f" {config.volatility_ceiling:.2%} threshold."
        )
        severity = "informational"

    check_compliance(explanation)
    return AlertResult(
        rule_id="VOL-001",
        fired=fired,
        severity=severity,
        metric_value=volatility.volatility_proxy,
        threshold=config.volatility_ceiling,
        explanation=explanation,
        ticker=None,
    )


# ---------------------------------------------------------------------------
# COV-001 — missing price coverage
# ---------------------------------------------------------------------------


def _evaluate_cov(
    snapshot: PortfolioSnapshot, config: AlertConfig
) -> AlertResult:
    count = len(snapshot.unpriced_tickers)
    threshold = float(config.max_unpriced_holdings)
    metric_value = float(count)
    fired = count > config.max_unpriced_holdings  # strict greater-than (D-043)

    if fired:
        ticker_list = ", ".join(snapshot.unpriced_tickers)
        explanation = (
            f"Coverage alert [COV-001]: {count} position(s) have no price data:"
            f" {ticker_list}."
        )
        severity = _severity(metric_value, threshold)
    else:
        explanation = (
            f"Coverage check [COV-001]: {count} position(s) have no price data,"
            f" within the configured maximum of {config.max_unpriced_holdings}."
        )
        severity = "informational"

    check_compliance(explanation)
    return AlertResult(
        rule_id="COV-001",
        fired=fired,
        severity=severity,
        metric_value=metric_value,
        threshold=threshold,
        explanation=explanation,
        ticker=None,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def evaluate_alerts(
    snapshot: PortfolioSnapshot,
    drawdown: DrawdownResult | None,
    volatility: VolatilityResult | None,
    config: AlertConfig = AlertConfig(),
) -> list[AlertResult]:
    """Evaluate all four alert rule families and return a result for each.

    Returns results for every rule, not only fired ones.
    Explanations pass through check_compliance before AlertResult construction.
    """
    results: list[AlertResult] = []
    results.extend(_evaluate_conc(snapshot, config))
    results.append(_evaluate_dd(drawdown, config))
    results.append(_evaluate_vol(volatility, config))
    results.append(_evaluate_cov(snapshot, config))
    return results
