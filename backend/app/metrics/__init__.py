"""Pure metrics engine — no I/O, no side effects.

Accepts plain data structures, returns computed metric values.
Deterministic and stateless. Implemented in Phase 4.

Public API:
  compute_portfolio_snapshot — M-001 through M-004 (snapshot metrics)
  compute_drawdown           — M-005 (drawdown from peak)
  compute_volatility_proxy   — M-006 (30-day return volatility proxy)
"""

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

__all__ = [
    "compute_drawdown",
    "compute_portfolio_snapshot",
    "compute_volatility_proxy",
    "DrawdownResult",
    "PortfolioSnapshot",
    "PositionMetrics",
    "VolatilityResult",
]
