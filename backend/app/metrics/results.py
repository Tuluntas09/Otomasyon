"""Result dataclasses for the Phase 4 pure metrics engine.

All dataclasses are frozen (immutable after construction).
No import from data persistence or adapter layers — results are plain value objects.

Language rule (M-004, METRICS_SPEC.md): fields describing gain/decline use
'unrealised_change' — never 'profit' or 'loss'.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionMetrics:
    """Per-position metrics snapshot (M-001, M-002, M-003, M-004)."""

    ticker: str
    quantity: float
    cost_basis_per_unit: float
    total_cost_basis: float
    market_value: float | None
    weight: float | None
    unrealised_change_usd: float | None
    unrealised_change_pct: float | None


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Whole-portfolio snapshot produced by compute_portfolio_snapshot."""

    total_market_value: float
    positions: list[PositionMetrics]
    priced_count: int
    unpriced_tickers: list[str]


@dataclass(frozen=True)
class DrawdownResult:
    """Result of compute_drawdown (M-005).

    drawdown: proportion in [0, 1] — (peak - current) / peak.
    dates_in_window: number of distinct price dates used.
    min_coverage_ratio: lowest fraction of holdings priced on any date in the window.
    latest_coverage_ratio: fraction of holdings priced on the latest date in the window.
    """

    drawdown: float
    peak_value: float
    current_value: float
    window_days: int
    dates_in_window: int
    min_coverage_ratio: float
    latest_coverage_ratio: float


@dataclass(frozen=True)
class VolatilityResult:
    """Result of compute_volatility_proxy (M-006).

    volatility_proxy: population std dev of daily percentage returns.
    returns_count: number of daily returns used in the calculation.
    min_coverage_ratio: lowest fraction of holdings priced on any date in the window.
    latest_coverage_ratio: fraction of holdings priced on the latest date in the window.
    """

    volatility_proxy: float
    window_days: int
    returns_count: int
    min_coverage_ratio: float
    latest_coverage_ratio: float
