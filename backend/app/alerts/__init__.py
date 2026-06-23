"""Alert rule evaluation engine.

Evaluates named threshold rules against computed metrics.
Alerts describe threshold crossings; they never prescribe action.
"""

from app.alerts.results import AlertConfig, AlertResult
from app.alerts.rules import evaluate_alerts

__all__ = ["AlertConfig", "AlertResult", "evaluate_alerts"]
