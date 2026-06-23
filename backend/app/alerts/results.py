"""Result and config dataclasses for the Phase 5 alert engine.

All dataclasses are frozen (immutable after construction).
No imports from data persistence, adapters, or I/O layers.

Allowed severity values: "informational", "watch", "elevated".
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AlertConfig:
    """Thresholds for the four alert rule families.

    Callers supply a custom instance or rely on the conservative defaults.
    """

    concentration_ceiling: float = 0.25
    drawdown_ceiling: float = 0.15
    volatility_ceiling: float = 0.02
    max_unpriced_holdings: int = 0


@dataclass(frozen=True)
class AlertResult:
    """Result of evaluating a single alert rule against current metrics.

    All results are returned, not only fired ones, so the caller can
    distinguish an explicit non-firing from a missing evaluation.

    severity: one of "informational", "watch", "elevated".
    ticker: populated for per-position rules (CONC-001 fired); None otherwise.
    """

    rule_id: str
    fired: bool
    severity: str
    metric_value: float
    threshold: float
    explanation: str
    ticker: str | None
