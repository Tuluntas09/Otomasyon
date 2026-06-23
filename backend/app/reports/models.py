"""Frozen dataclasses for daily and weekly report output.

All dataclasses are immutable after construction.
No I/O, no DB access, no compliance scanning here — this module is plain value objects.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.journal.models import JournalEntry
from app.metrics.quality import DataQualitySummary


@dataclass(frozen=True)
class ReportSection:
    """One labelled section of a report.

    Both label and body are system-generated and have been passed through
    check_compliance() by the builder before being placed here.
    """

    label: str
    body: str


@dataclass(frozen=True)
class DailyReport:
    """Complete daily report produced by build_daily_report().

    sections: system-generated, compliance-checked text blocks.
    journal_entries: user-authored entries carried verbatim; NOT compliance-scanned.
    data_quality: structured price history depth summary (Phase 8A); None when
    the caller did not supply a DataQualitySummary.
    """

    report_date: str
    report_type: str
    sections: list[ReportSection]
    journal_entries: list[JournalEntry]
    data_quality: DataQualitySummary | None = None


@dataclass(frozen=True)
class WeeklyReport:
    """Complete weekly report produced by build_weekly_report().

    sections: system-generated, compliance-checked text blocks.
    journal_entries: user-authored entries carried verbatim; NOT compliance-scanned.
    data_quality: structured price history depth summary (Phase 8A); None when
    the caller did not supply a DataQualitySummary.
    """

    report_date: str
    week_start: str
    report_type: str
    sections: list[ReportSection]
    journal_entries: list[JournalEntry]
    data_quality: DataQualitySummary | None = None
