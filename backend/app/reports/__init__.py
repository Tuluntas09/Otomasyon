"""Report assembly module.

Produces daily and weekly human-readable summaries of portfolio state and alerts.
All generated text passes through the compliance guard. Implemented in Phase 7A.
"""

from app.reports.builder import build_daily_report, build_weekly_report
from app.reports.models import DailyReport, ReportSection, WeeklyReport

__all__ = [
    "ReportSection",
    "DailyReport",
    "WeeklyReport",
    "build_daily_report",
    "build_weekly_report",
]
