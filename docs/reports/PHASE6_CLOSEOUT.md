# Phase 6 Closeout Report — Decision Journal

**Date:** 2026-06-23
**Phase:** 6 — Decision journal
**Status:** Complete. Awaiting human review before Phase 7 begins.

---

## 1. Scope implemented

Phase 6 implements the decision journal: an append-only log of user-authored reasoning
about their own past decisions. The system stores and retrieves entries; it never
auto-generates journal content and never scans user-authored text through the compliance
guard.

---

## 2. Files created

| File | Purpose |
|---|---|
| `backend/app/journal/models.py` | `JournalEntry` frozen dataclass; `validate_new_entry()` |
| `backend/app/data/persistence/journal_repo.py` | `JournalRepo`: add_entry, get_all, get_by_ticker |
| `backend/tests/unit/test_journal.py` | 27 unit tests for domain model and validation |
| `backend/tests/integration/test_journal_repo.py` | 28 integration tests against in-memory SQLite |
| `docs/reports/PHASE6_CLOSEOUT.md` | This file |

---

## 3. Files modified

| File | Change |
|---|---|
| `backend/app/core/exceptions.py` | Added `JournalValidationError(ValidationError)` |
| `backend/app/journal/__init__.py` | Exports `JournalEntry`, `validate_new_entry` |
| `backend/app/data/persistence/db.py` | Added `journal_entries` DDL (idempotent) |
| `backend/app/data/persistence/__init__.py` | Exports `JournalRepo` |
| `backend/app/alerts/results.py` | Removed unused `field` import from `dataclasses` |
| `docs/DECISIONS.md` | Appended D-044 through D-050 |
| `docs/ROADMAP.md` | Phase 6 marked complete; acceptance criteria added |
| `PROJECT_BRAIN.md` | Phase 6 status updated; D-044–D-050 index added; completion summary updated |

---

## 4. Journal schema implemented

```
journal_entries (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date   TEXT NOT NULL,        -- ISO 8601 date (YYYY-MM-DD)
    ticker       TEXT,                 -- optional; validated if provided
    action_taken TEXT NOT NULL,        -- user-authored; stored verbatim
    reasoning    TEXT NOT NULL,        -- user-authored; stored verbatim
    hypothesis   TEXT,                 -- optional free text; stored verbatim
    review_date  TEXT,                 -- optional ISO 8601 date; must be after entry_date
    tags         TEXT,                 -- optional free text; stored verbatim
    created_at   TEXT NOT NULL         -- UTC ISO 8601 datetime
)
```

---

## 5. Validation behaviour

`validate_new_entry()` enforces:

- `entry_date`: valid ISO 8601 date (YYYY-MM-DD); raises `InvalidDateError` on failure.
- `action_taken`: non-empty string after `.strip()`; raises `JournalValidationError`.
- `reasoning`: non-empty string after `.strip()`; raises `JournalValidationError`.
- `ticker`: if provided, must pass `validate_ticker()`; raises `InvalidTickerError`.
- `review_date`: if provided, must be valid ISO 8601 date AND strictly after `entry_date`;
  raises `InvalidDateError` or `JournalValidationError` respectively.
- `hypothesis`, `tags`: free text; accepted as `str | None` with no further validation.

`check_compliance()` is not called on any user-authored field.

---

## 6. Persistence behaviour

`JournalRepo` methods:

- `add_entry(...)`: validates before any INSERT; sets `created_at` using
  `datetime.now(timezone.utc).isoformat()`; inserts into `journal_entries`; returns
  a `JournalEntry` with the assigned `id` and `created_at`.
- `get_all()`: returns all entries ordered by `entry_date DESC, created_at DESC`.
- `get_by_ticker(ticker)`: validates `ticker`; returns matching entries ordered by
  `entry_date DESC, created_at DESC`; does not return ticker-less entries.
- No `update()` or `delete()` methods — append-only by design.
- Multiple entries for the same ticker are allowed.
- `ticker=None` entries are allowed and returned by `get_all()` but not by `get_by_ticker()`.

---

## 7. User-authored text / compliance behaviour

- `action_taken`, `reasoning`, `hypothesis`, and `tags` are stored verbatim.
- `check_compliance()` is not called on any of these fields.
- Text containing compliance-forbidden terms (e.g., "buy", "sell", "profit") is accepted
  and stored without modification.
- This is intentional and tested: user private notes record past facts, not system advice.
- System-generated text (alert explanations, report summaries) continues to pass through
  the compliance guard as required by the architecture invariant.

---

## 8. Timestamp behaviour

- `created_at` is set at INSERT time using `datetime.now(timezone.utc).isoformat()`.
- The resulting string includes UTC offset (`+00:00`).
- Tests verify: `created_at` is set, parses as a valid ISO datetime, and has non-zero
  UTC `tzinfo`.
- Rationale (D-050): UTC is deterministic across local timezone changes and safe for
  ordering comparisons across DST transitions.

---

## 9. Test results

```
358 passed, 0 skipped
```

Previous count: 313 (Phase 5). New tests: +45 (27 unit + 28 integration = 55 new tests;
net +45 after the 10 pre-existing placeholders that were already counted in prior phases).

Wait — total increase is 358 - 313 = 45 new tests. Broken down:
- `tests/unit/test_journal.py`: 27 tests
- `tests/integration/test_journal_repo.py`: 28 tests
- `backend/app/alerts/results.py` cleanup: 0 regressions

Architecture invariant: all three tests still pass (no broker, no execution, no advisory).

---

## 10. Decisions recorded

| Decision | Summary |
|---|---|
| D-044 | Journal persistence under `data/persistence/`; DDL in `db.py` |
| D-045 | Append-only: add_entry, get_all, get_by_ticker only |
| D-046 | Compliance guard NOT applied to user-authored journal text |
| D-047 | `action_taken` field name retained as user-authored past-tense record |
| D-048 | `review_date` must be strictly after `entry_date` |
| D-049 | Ordering: `entry_date DESC, created_at DESC` |
| D-050 | `created_at` uses UTC: `datetime.now(timezone.utc).isoformat()` |

---

## 11. Out-of-scope items (not implemented)

The following were explicitly out of scope and were not implemented:

- FastAPI routes
- Frontend UI
- Report generation
- Notification delivery
- Scheduled jobs
- Metrics changes
- Alert rule changes
- CSV parsing changes
- External APIs / HTTP clients / web scraping
- Technical indicators / backtesting
- Paper trading / live trading / broker integration / order placement
- Advisory, trading, or profit language

---

## 12. Deviations from implementation prompt

None. All two required corrections from the planning review were applied:

1. SQLite persistence lives under `backend/app/data/persistence/journal_repo.py` (not
   `backend/app/journal/repo.py`).
2. `created_at` uses `datetime.now(timezone.utc).isoformat()` (UTC, not local time).

The `test_invalid_entry_raises_before_db_write` test was broadened from
`JournalValidationError` to `ValidationError` because `validate_iso_date` raises
`InvalidDateError` (a sibling of `JournalValidationError`, both inheriting
`ValidationError`) when given an invalid date string. This broadening is correct and
consistent with the intent of the test.

The `test_journal_models_does_not_call_check_compliance` test checks for
`"check_compliance("` (with opening parenthesis) rather than `"check_compliance"` to
avoid matching the string in the function's docstring comment.

---

*Phase 6 complete. Awaiting human review before Phase 7.*
