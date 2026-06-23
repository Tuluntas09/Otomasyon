"""Pure metrics engine — M-001 through M-006.

All functions are stateless, deterministic, and free of I/O.
No import from data persistence or adapter layers.

Inputs: plain domain objects (Holding, PriceRecord lists).
Outputs: plain result dataclasses (PositionMetrics, PortfolioSnapshot, etc.).

Window behavior (D-031):
  All time windows are calculated backwards from the latest price_date present
  in the supplied price_records — never from the system clock.
"""

import statistics
from datetime import date, timedelta

from app.core.models import Holding, PriceRecord
from app.metrics.results import (
    DrawdownResult,
    PortfolioSnapshot,
    PositionMetrics,
    VolatilityResult,
)


def _latest_prices(price_records: list[PriceRecord]) -> dict[str, float]:
    """Return {ticker: close_price} for the most recent price_date per ticker."""
    latest: dict[str, tuple[str, float]] = {}
    for pr in price_records:
        existing = latest.get(pr.ticker)
        if existing is None or pr.price_date > existing[0]:
            latest[pr.ticker] = (pr.price_date, pr.close_price)
    return {ticker: price for ticker, (_, price) in latest.items()}


def _portfolio_daily_values(
    holdings: list[Holding],
    price_records: list[PriceRecord],
    window_days: int,
) -> list[tuple[str, float, float]]:
    """Return [(iso_date, portfolio_value, coverage_ratio), ...] sorted ascending by date.

    The window is measured backwards from the latest price_date in price_records.
    coverage_ratio = fraction of holdings that have a price on that date.
    Portfolio value on each date = sum(quantity * close_price) for holdings priced
    on that date (D-032: unpriced holdings excluded, not valued at zero).
    """
    if not holdings or not price_records:
        return []

    latest_date = date.fromisoformat(max(pr.price_date for pr in price_records))
    cutoff_date = latest_date - timedelta(days=window_days)

    total_holdings = len(holdings)
    qty_by_ticker: dict[str, float] = {h.ticker: h.quantity for h in holdings}

    # Build {date_str -> {ticker -> close_price}} for dates within the window.
    # Duplicate (date, ticker) entries: last encountered wins (consistent with D-022).
    date_prices: dict[str, dict[str, float]] = {}
    for pr in price_records:
        d = date.fromisoformat(pr.price_date)
        if d < cutoff_date:
            continue
        if pr.price_date not in date_prices:
            date_prices[pr.price_date] = {}
        date_prices[pr.price_date][pr.ticker] = pr.close_price

    result: list[tuple[str, float, float]] = []
    for date_str in sorted(date_prices):
        prices_on_date = date_prices[date_str]
        portfolio_value = sum(
            qty_by_ticker[ticker] * price
            for ticker, price in prices_on_date.items()
            if ticker in qty_by_ticker
        )
        holdings_priced = sum(1 for h in holdings if h.ticker in prices_on_date)
        coverage_ratio = holdings_priced / total_holdings
        result.append((date_str, portfolio_value, coverage_ratio))

    return result


def compute_portfolio_snapshot(
    holdings: list[Holding],
    price_records: list[PriceRecord],
) -> PortfolioSnapshot:
    """Compute per-position and portfolio-level snapshot metrics.

    Implements M-001 (position weight), M-002 (portfolio market value),
    M-003 (cost basis per position), and M-004 (unrealised change in value).

    Holdings with no price in price_records have market_value=None, weight=None,
    unrealised_change_usd=None, unrealised_change_pct=None (D-032).
    """
    prices = _latest_prices(price_records)

    # First pass: compute market value per position and sum total.
    position_mv: dict[str, float | None] = {}
    total_market_value = 0.0
    for h in holdings:
        price = prices.get(h.ticker)
        if price is not None:
            mv = h.quantity * price
            position_mv[h.ticker] = mv
            total_market_value += mv
        else:
            position_mv[h.ticker] = None

    # Second pass: compute all per-position metrics.
    positions: list[PositionMetrics] = []
    unpriced_tickers: list[str] = []
    priced_count = 0

    for h in holdings:
        mv = position_mv[h.ticker]
        price = prices.get(h.ticker)
        total_cost_basis = h.quantity * h.cost_basis

        if mv is not None and price is not None:
            priced_count += 1
            weight = mv / total_market_value if total_market_value > 0.0 else None
            unrealised_change_usd = (price - h.cost_basis) * h.quantity
            unrealised_change_pct = (
                (price - h.cost_basis) / h.cost_basis
                if h.cost_basis != 0.0
                else None
            )
        else:
            unpriced_tickers.append(h.ticker)
            weight = None
            unrealised_change_usd = None
            unrealised_change_pct = None

        positions.append(
            PositionMetrics(
                ticker=h.ticker,
                quantity=h.quantity,
                cost_basis_per_unit=h.cost_basis,
                total_cost_basis=total_cost_basis,
                market_value=mv,
                weight=weight,
                unrealised_change_usd=unrealised_change_usd,
                unrealised_change_pct=unrealised_change_pct,
            )
        )

    return PortfolioSnapshot(
        total_market_value=total_market_value,
        positions=positions,
        priced_count=priced_count,
        unpriced_tickers=unpriced_tickers,
    )


def compute_drawdown(
    holdings: list[Holding],
    price_records: list[PriceRecord],
    window_days: int = 90,
) -> DrawdownResult | None:
    """Compute drawdown from peak (M-005).

    The window runs backwards from the latest price_date in price_records (D-031).
    Returns None if holdings is empty, no usable dates exist, or peak_value <= 0.
    Returns drawdown=0.0 if exactly one usable date exists (at peak by definition).
    """
    if not holdings:
        return None

    daily_values = _portfolio_daily_values(holdings, price_records, window_days)
    if not daily_values:
        return None

    values = [v for _, v, _ in daily_values]
    coverages = [c for _, _, c in daily_values]

    peak_value = max(values)
    if peak_value <= 0.0:
        return None

    current_value = values[-1]
    drawdown = (peak_value - current_value) / peak_value

    return DrawdownResult(
        drawdown=drawdown,
        peak_value=peak_value,
        current_value=current_value,
        window_days=window_days,
        dates_in_window=len(daily_values),
        min_coverage_ratio=min(coverages),
        latest_coverage_ratio=coverages[-1],
    )


def compute_volatility_proxy(
    holdings: list[Holding],
    price_records: list[PriceRecord],
    window_days: int = 30,
) -> VolatilityResult | None:
    """Compute 30-day return volatility proxy (M-006).

    Uses daily percentage returns: (v[t] - v[t-1]) / v[t-1].
    Standard deviation is population std dev via statistics.pstdev (D-034).
    Not annualised.
    The window runs backwards from the latest price_date in price_records (D-031).

    Returns None if holdings is empty, fewer than 2 usable dates exist, or no
    valid returns remain after skipping zero-denominator days.
    """
    if not holdings:
        return None

    daily_values = _portfolio_daily_values(holdings, price_records, window_days)
    if len(daily_values) < 2:
        return None

    coverages = [c for _, _, c in daily_values]

    returns: list[float] = []
    for i in range(1, len(daily_values)):
        _, prev_value, _ = daily_values[i - 1]
        _, curr_value, _ = daily_values[i]
        if prev_value == 0.0:
            continue
        returns.append((curr_value - prev_value) / prev_value)

    if not returns:
        return None

    volatility = statistics.pstdev(returns)

    return VolatilityResult(
        volatility_proxy=volatility,
        window_days=window_days,
        returns_count=len(returns),
        min_coverage_ratio=min(coverages),
        latest_coverage_ratio=coverages[-1],
    )
