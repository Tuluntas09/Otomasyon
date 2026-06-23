# Phase 7A Closeout Report — Pure Report Builder

**Date:** 2026-06-23
**Phase:** 7A — Reports: pure builder
**Status:** Complete. Awaiting human review before Phase 7B begins.

---

## 1. Scope implemented

Phase 7A implements the pure report builder: a composition layer that receives
already-computed result objects and journal entries as function arguments and returns
frozen report dataclasses. The builder has no I/O, no DB access, no DataAdapter calls,
no filesystem or network access, and no system clock use.

All system-generated `ReportSection` text passes through `check_compliance()` before
being stored. User-authored journal fields are never compliance-scanned and are carried
verbatim in the report's `journal_entries` field.

---

## 2. Files created

| File | Purpose |
|---|---|
| `backend/app/reports/models.py` | `ReportSection`, `DailyReport`, `WeeklyReport` frozen dataclasses |
| `backend/app/reports/builder.py` | `build_daily_report`, `build_weekly_report`, `_make_section` |
| `backend/tests/unit/test_reports.py` | 93 unit tests; no DB fixtures |
| `docs/reports/PHASE7A_CLOSEOUT.md` | This file |

---

## 3. Files modified

| File | Change |
|---|---|
| `backend/app/reports/__init__.py` | Exports `ReportSection`, `DailyReport`, `WeeklyReport`, `build_daily_report`, `build_weekly_report` |
| `docs/DECISIONS.md` | Appended D-051 through D-057 |
| `docs/ROADMAP.md` | Phase 7 split into 7A (complete) and 7B (not started); acceptance criteria added |
| `PROJECT_BRAIN.md` | Phase 7A status updated; D-051–D-057 index added; completion summary updated |

---

## 4. Report dataclasses implemented

```
ReportSection (frozen):
    label: str          # system-generated, compliance-checked
    body: str           # system-generated, compliance-checked

DailyReport (frozen):
    report_date: str
    report_type: str    # always "daily"
    sections: list[ReportSection]
    journal_entries: list[JournalEntry]   # verbatim, NOT compliance-checked

WeeklyReport (frozen):
    report_date: str
    week_start: str
    report_type: str    # always "weekly"
    sections: list[ReportSection]
    journal_entries: list[JournalEntry]   # verbatim, NOT compliance-checked
```

---

## 5. Daily report behaviour

`build_daily_report(report_date, snapshot, alert_results, journal_entries)` produces
a `DailyReport` with the following sections in order:

| Section | Content |
|---|---|
| Report | Type, date, non-advisory note |
| Data Coverage | Priced count, total count, unpriced ticker list if any |
| Portfolio Snapshot | Total market value (USD), priced positions count, total positions count |
| Position Weights | Per-position: ticker, weight, market value, unrealised change in value (if available); unpriced shown as "price data not available" |
| Alert Summary | All alert results (fired and non-fired): rule_id, status, severity, measured value, threshold, explanation |
| Journal Entries | Count of user-authored entries, or "No entries recorded for this period." |
| Method Note | Factual description of computation method and data limitations |
| Disclaimer | Non-advisory, non-prescriptive disclaimer |

Edge cases handled:
- Zero positions: coverage body "No positions recorded."
- All unpriced: "0 of N position(s) priced. Price data not available for all positions: ..."
- No alerts evaluated: "No alert rules evaluated."
- No journal entries: "No entries recorded for this period."

---

## 6. Weekly report behaviour

`build_weekly_report(report_date, week_start, snapshot, drawdown, volatility, alert_results, journal_entries)`
produces a `WeeklyReport` with all daily sections plus:

| Section | Content |
|---|---|
| Week Range | `week_start` to `report_date` |
| Drawdown Summary | M-005 value, peak, current, window, coverage ratios — or "not available — insufficient data" |
| Volatility Proxy Summary | M-006 value, window, returns count, coverage ratios — or "not available — insufficient data" |

Week Range section is inserted after the header. Drawdown and Volatility sections are
inserted after Portfolio Snapshot, before Position Weights.

---

## 7. Compliance behaviour

- `_make_section(label, body)` calls `check_compliance(label)` then `check_compliance(body)`.
- If either raises `ComplianceViolationError`, it propagates immediately. The builder
  never catches or rewrites compliance errors.
- All eight (daily) / eleven (weekly) sections are constructed via `_make_section`.
- All section text is authored against the known-safe vocabulary:
  - "unrealised change in value" (not "profit" or "loss")
  - "price data not available" (not any advisory phrasing)
  - "within threshold" / "above threshold" (not "hold", "sell", etc.)
  - "not available — insufficient data"
  - "Not investment advice."
- Forbidden words verified absent: buy, sell, hold, profit, loss, opportunity, recommend,
  suggest, should, must, guaranteed, order, broker, execute, reduce, increase.

---

## 8. User-authored journal text behaviour

- `JournalEntry` objects are passed as-is and stored in `DailyReport.journal_entries` /
  `WeeklyReport.journal_entries`.
- `check_compliance()` is NOT called on `action_taken`, `reasoning`, `hypothesis`,
  or `tags`. Consistent with D-046.
- The system-generated "Journal Entries" section body contains only a count ("N user-authored
  entries recorded for this period.") — never any user-authored text.
- Journal entries may contain compliance-forbidden terms; this is accepted and tested.
- JOURNAL_SCHEMA.md: "The system may display journal entries verbatim — it does not
  paraphrase or summarise them in v0.1."

---

## 9. Date / timestamp behaviour

- `report_date` is caller-provided and validated with `validate_iso_date()`.
- `week_start` is caller-provided and validated with `validate_iso_date()`.
- If `week_start` is strictly after `report_date`, `InvalidDateError` is raised.
- `week_start == report_date` is valid (same-day weekly report).
- The builder contains no calls to `datetime.now()` or `date.today()`.
- Verified by `test_builder_does_not_call_system_clock` which reads the source file.

---

## 10. Test results

```
451 passed, 0 skipped
```

Previous count: 358 (Phase 6). New tests: +93 (all in `tests/unit/test_reports.py`).

Test categories:
- Dataclass frozen invariants: 6 tests
- `_make_section` helper: 4 tests
- `build_daily_report` content and behaviour: 39 tests
- `build_weekly_report` content and behaviour: 18 tests
- Date validation: 6 tests
- Boundary / purity (no forbidden imports, no system clock): 11 tests
- Compliance propagation via `_make_section`: 3 tests
- Journal fields not compliance-scanned: 6 tests

Architecture invariant: all three tests still pass (no broker, no execution, no advisory).

---

## 11. Decisions recorded

| Decision | Summary |
|---|---|
| D-051 | Phase 7A boundary: pure builder only; Phase 7B API routes require separate approval |
| D-052 | Report builder inputs: already-computed result objects as arguments; no I/O |
| D-053 | Report builder outputs: frozen `DailyReport`/`WeeklyReport`/`ReportSection` dataclasses |
| D-054 | Report compliance: all `ReportSection` text checked; journal fields verbatim |
| D-055 | Alert inclusion: all evaluated alerts (fired and non-fired) in every report |
| D-056 | Report date policy: caller-provided dates; no system clock in builder |
| D-057 | v0.1 closeout: complete only after Phase 7B acceptance |

---

## 12. Out-of-scope items (not implemented)

The following were explicitly out of scope and were not implemented:

- FastAPI routes
- `backend/main.py`
- API orchestration layer
- Frontend UI
- Manual-run command
- Report file export
- Notification delivery (email, SMS, push)
- Scheduled jobs / cron
- External APIs / HTTP clients / web scraping
- Technical indicators / backtesting / paper trading
- Live trading / broker integration / order placement
- Portfolio optimization / instrument ranking
- Advisory, trading, or profit language

---

## 13. Deviations from implementation prompt

None. All specified deliverables were implemented as described. No decisions diverged
from the prompt.

One clarification applied: the implementation prompt listed "ARCHITECTURE.md boundary
table states `reports/` may read from `data/adapters/`" — this potential conflict was
resolved by the conservative plan (D-052): the builder accepts already-computed arguments
only, and the ARCHITECTURE.md boundary table reflects what the API orchestration layer
(Phase 7B) may do, not the builder itself. No change to ARCHITECTURE.md was made in
Phase 7A; it will be updated in Phase 7B to clarify the builder's tighter boundary.

---

*Phase 7A complete. Awaiting human review before Phase 7B.*
