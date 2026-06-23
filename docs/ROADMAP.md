# ROADMAP.md

## Phase status

| Phase | Name | Status |
|---|---|---|
| 0 | Documentation | ✅ accepted |
| 1 | Empty skeleton | ✅ complete |
| 2 | Data model + local storage | ✅ complete — awaiting human review |
| 3 | CSV data adapter | ✅ complete — awaiting human review |
| 4 | Metrics engine | ✅ complete — awaiting human review |
| 5 | Alerts + compliance guard | ✅ complete — awaiting human review |
| 6 | Decision journal | ✅ complete — awaiting human review |
| 7A | Reports — pure builder | ✅ complete — awaiting human review |
| 7B | API layer — FastAPI routes | ✅ accepted |
| 8 | Phase 8 gate review (Option B selected — Tier 2 analytics) | ✅ gate accepted |
| 8A | Data quality analytics (Option B implementation) | ✅ complete |

---

## Phase 0 — Documentation

**Scope:** Create all planning documents. Establish non-negotiable invariants in writing.

**Acceptance criteria:**
- `PROJECT_BRAIN.md` written and reflects project identity.
- All `docs/` files present and internally consistent.
- `DECISIONS.md` contains D-013 through D-019.
- Human review completed and phase accepted.

**Status:** ✅ Accepted.

---

## Phase 1 — Empty skeleton

**Scope:** Create the repository structure, empty module boundaries, and the one
substantive test: the architectural invariant.

**Acceptance criteria:**
- Git repository initialised.
- `README.md` with disclaimer present.
- All `backend/app/` module boundaries present as `__init__.py` with docstrings only.
- `backend/pyproject.toml` with pytest configured.
- `backend/tests/architecture/test_no_broker_no_execution.py` present and passing.
- `python -m pytest` from `backend/` returns `3 passed, 9 skipped`.
- No application logic in any module.
- `frontend/` empty shell with safety component placeholder.
- `ci/` stub present.

**Status:** ✅ Complete.

---

## Phase 2 — Data model + local storage

**Scope:** Define domain types, implement SQLite schema, and build the repository layer.

**Key deliverables:**
- `backend/app/core/models.py` — `Holding`, `WatchlistEntry`, `PriceRecord` domain types.
- `backend/app/core/validation.py` — typed validation (CurrencyError, NegativeQuantityError,
  DuplicateTickerError).
- `backend/app/data/adapters/base.py` — `DataAdapter` ABC.
- `backend/app/data/persistence/db.py` — DB init, schema DDL.
- `backend/app/data/persistence/holdings_repo.py`, `watchlist_repo.py`, `prices_repo.py`.
- Phase 2 unit and integration tests.
- `DECISIONS.md` updated with D-020 through D-024.

**Acceptance criteria:**
- Architecture test still passes (`3 passed, 9 skipped` minimum — new tests add to count).
- All validation rules enforced and tested.
- Repositories round-trip correctly in in-memory SQLite.
- No CSV parsing, metrics, alerts, or API routes in this phase.

**Status:** ✅ Complete. Awaiting human review before Phase 3 begins.

---

## Phase 3 — CSV data adapter

**Scope:** Implement the CSV adapter that reads holdings, watchlist, and prices CSVs and
writes them to the database via the repository layer. Implement the concrete
`SQLiteDataAdapter` satisfying the Phase 2 `DataAdapter` ABC.

**Key deliverables:**
- `backend/app/data/adapters/sqlite_adapter.py` — `SQLiteDataAdapter` concrete class.
- `backend/app/data/adapters/csv_importer.py` — `import_holdings_csv`,
  `import_watchlist_csv`, `import_prices_csv`; `ImportResult`; `RowImportError`.
- `backend/app/core/exceptions.py` — `MissingColumnError`, `CsvImportError`.
- Phase 3 unit and integration tests.
- `DECISIONS.md` updated with D-024 through D-029.

**Acceptance criteria:**
- Architecture invariant still passes.
- All Phase 3 placeholder skips replaced with passing tests.
- `SQLiteDataAdapter` satisfies `DataAdapter` ABC.
- Holdings/watchlist all-or-nothing: no partial writes on error.
- Prices partial import: valid rows written, invalid rows in `ImportResult.errors`.
- DB duplicate pre-check in Pass 1 prevents any write before validation is complete.
- `pyproject.toml` dependencies unchanged (no third-party packages).

**Status:** ✅ Complete. Awaiting human review before Phase 4 begins.

---

## Phase 4 — Metrics engine

**Scope:** Implement the pure metrics engine. M-001 through M-006 from `METRICS_SPEC.md`.

**Key deliverables:**
- `backend/app/metrics/results.py` — `PositionMetrics`, `PortfolioSnapshot`, `DrawdownResult`, `VolatilityResult` frozen dataclasses.
- `backend/app/metrics/engine.py` — `compute_portfolio_snapshot`, `compute_drawdown`, `compute_volatility_proxy`.
- `backend/tests/unit/test_metrics.py` — 44 unit tests; no DB fixtures.
- `DECISIONS.md` updated with D-030 through D-035.

**Acceptance criteria:**
- All six metrics (M-001 through M-006) implemented.
- Metrics engine imports no forbidden modules (sqlite3, csv, os, pathlib, network, persistence, adapters).
- No result field named `profit` or `loss`.
- Window calculations use latest input price date, not system date.
- Architecture invariant still passes.
- `pyproject.toml` dependencies unchanged.

**Status:** ✅ Complete. Awaiting human review before Phase 5 begins.

---

## Phase 5 — Alerts + compliance guard

**Scope:** Implement alert rule evaluation and the compliance guard. All system-generated
text routed through the guard from this phase onward.

**Key deliverables:**
- `backend/app/compliance/guard.py` — `ComplianceViolation` dataclass, `check_compliance()`.
- `backend/app/alerts/results.py` — `AlertConfig`, `AlertResult` frozen dataclasses.
- `backend/app/alerts/rules.py` — `evaluate_alerts()` consuming Phase 4 metric results.
- `backend/app/core/exceptions.py` — `ComplianceViolationError` added.
- `backend/tests/unit/test_compliance.py` — compliance guard unit tests.
- `backend/tests/unit/test_alerts.py` — alert engine unit and boundary tests.
- `DECISIONS.md` updated with D-036 through D-043.

**Acceptance criteria:**
- All four alert rules (CONC-001, DD-001, VOL-001, COV-001) implemented.
- Strict greater-than threshold comparison — exact equality does not fire.
- Every alert explanation passes check_compliance before AlertResult construction.
- Alert engine imports no forbidden modules (sqlite3, csv, os, pathlib, network, persistence, adapters).
- Architecture invariant still passes.
- pyproject.toml dependencies unchanged.

**Status:** ✅ Complete. Awaiting human review before Phase 6 begins.

---

## Phase 6 — Decision journal

**Scope:** Implement journal entry CRUD (append-only writes, queries).

**Key deliverables:**
- `backend/app/journal/models.py` — `JournalEntry` frozen dataclass, `validate_new_entry()`.
- `backend/app/data/persistence/journal_repo.py` — `JournalRepo` (add_entry, get_all, get_by_ticker).
- `backend/app/data/persistence/db.py` — `journal_entries` DDL added (idempotent).
- `backend/app/core/exceptions.py` — `JournalValidationError` added.
- `backend/tests/unit/test_journal.py` — unit tests for domain model and validation.
- `backend/tests/integration/test_journal_repo.py` — integration tests against in-memory SQLite.
- `DECISIONS.md` updated with D-044 through D-050.

**Acceptance criteria:**
- Journal domain model and validation implemented and tested.
- Persistence append-only: add_entry, get_all, get_by_ticker; no update or delete.
- created_at uses UTC: datetime.now(timezone.utc).isoformat().
- Compliance guard is NOT applied to user-authored journal text.
- Architecture invariant still passes.
- pyproject.toml dependencies unchanged.
- Total test count: 358 passed, 0 skipped.

**Status:** ✅ Complete. Awaiting human review before Phase 7 begins.

---

## Phase 7A — Reports: pure builder

**Scope:** Implement pure daily/weekly report builder under `backend/app/reports/`.
No I/O, no DB, no API routes. All system-generated text passes through compliance guard.
Journal entries carried verbatim without compliance scanning.

**Key deliverables:**
- `backend/app/reports/models.py` — `ReportSection`, `DailyReport`, `WeeklyReport` frozen dataclasses.
- `backend/app/reports/builder.py` — `build_daily_report`, `build_weekly_report`, `_make_section`.
- `backend/tests/unit/test_reports.py` — 93 unit tests; no DB fixtures.
- `docs/DECISIONS.md` updated with D-051 through D-057.

**Acceptance criteria:**
- `build_daily_report` and `build_weekly_report` return frozen dataclasses.
- Every `ReportSection` label and body passes `check_compliance()` before construction.
- `ComplianceViolationError` propagates — never caught inside builder.
- Journal entries carried verbatim in `journal_entries`; `check_compliance()` not called on user fields.
- All evaluated alerts (fired and non-fired) included in alert summary section.
- `DrawdownResult=None` and `VolatilityResult=None` produce safe "not available" text.
- Zero-position and all-unpriced portfolios produce valid reports.
- `reports/` imports no `sqlite3`, `csv`, `os`, `pathlib`, network libs, persistence, or adapters.
- No `datetime.now()` or `date.today()` call in builder.
- Architecture invariant still passes.
- `pyproject.toml` dependencies unchanged.
- Total test count: 451 passed, 0 skipped.

**Status:** ✅ Complete. Awaiting human review before Phase 7B begins.

---

## Phase 7B — API layer: FastAPI routes

**Scope:** Wire minimal read-only FastAPI routes for frontend consumption of reports.

**Key deliverables:**
- `backend/app/api/app.py` — FastAPI app instance.
- `backend/app/api/routes/health.py` — `GET /health`.
- `backend/app/api/routes/reports.py` — `GET /reports/daily`, `GET /reports/weekly`.
- `backend/app/api/deps.py` — per-request DB connection dependency.
- `backend/main.py` — ASGI entry point.
- `backend/app/data/adapters/base.py` — `DataAdapter` extended with `get_journal_entries`.
- `backend/app/data/adapters/sqlite_adapter.py` — `get_journal_entries` implemented.
- `backend/app/data/persistence/journal_repo.py` — `get_by_date_range` added.
- `backend/tests/integration/test_api_reports.py` — 49 integration tests.
- `docs/DECISIONS.md` updated with D-058 through D-066.

**Acceptance criteria:**
- Architecture invariant still passes.
- All routes are GET-only. No write endpoints.
- `GET /reports/daily?report_date=YYYY-MM-DD` returns a serialized DailyReport.
- `GET /reports/weekly?week_start=YYYY-MM-DD&report_date=YYYY-MM-DD` returns a serialized WeeklyReport.
- Invalid date parameters return HTTP 422 with structured error detail.
- Journal entries returned verbatim; compliance guard not applied to user-authored text.
- System-generated sections contain no forbidden language.
- API routes import no persistence repos directly.
- pyproject.toml has `fastapi>=0.100.0` runtime dependency and dev optional dependency.
- Total test count > 451. Zero skipped.

**Status:** ✅ Accepted. v0.1 implementation accepted. Phase 8 (Tier 3 gate review) requires its own deliberate decision and explicit human approval before any code is written.

---

## Phase 8 — Gate review

**Scope:** Evaluate which boundary option to pursue after v0.1. Options A–D documented
in `docs/PHASE8_GATE_PLAN.md`. **Option B (richer local analytics, Tier 2 only)**
selected by human decision.

**Status:** ✅ Gate accepted. Option B selected. Phase 8A implemented.

---

## Phase 8A — Data quality analytics (Option B, Tier 2)

**Scope:** Pure data quality analytics within Tier 2. No paper trading, no simulated
execution, no broker abstraction, no technical indicators, no backtesting, no external
market data.

**Key deliverables:**
- `backend/app/metrics/quality.py` — `TickerQuality`, `DataQualitySummary` frozen
  dataclasses; `compute_data_quality(holdings, price_records, report_date)` pure function.
- `backend/app/reports/models.py` — `data_quality: DataQualitySummary | None = None`
  field added to `DailyReport` and `WeeklyReport`.
- `backend/app/reports/builder.py` — `_data_quality_section()` builder; `data_quality`
  optional parameter added to `build_daily_report` and `build_weekly_report`.
- `backend/app/api/routes/reports.py` — `compute_data_quality` called in orchestration;
  result passed to builders; `data_quality` exposed as top-level key in both API responses.
- `backend/tests/unit/test_data_quality.py` — 71 unit tests; no DB fixtures.
- `backend/tests/integration/test_api_reports.py` — 14 new integration tests.
- `backend/tests/architecture/test_no_broker_no_execution.py` — 3 new invariant tests.
- `docs/DECISIONS.md` — D-067 through D-074 recorded.

**Acceptance criteria:**
- Architecture invariant still passes (6 tests total — original 3 + 3 new).
- Data quality function is pure: no I/O, no system clock, no persistence imports.
- "Data Quality Summary" section present in daily and weekly reports when data_quality provided.
- All section text passes check_compliance().
- `data_quality` top-level key in both API responses, populated via dataclasses.asdict().
- No new runtime dependencies.
- Total test count: 585 passed, 0 skipped.

**Status:** ✅ Complete.

---

## Off-roadmap (will not be implemented without major re-scoping)

- Live trading (Tier 4)
- Broker API integration
- News scraping / sentiment
- Arbitrage detection
- ML trade signals
- Multi-currency aggregation (v0.2+ candidate)
- Multi-portfolio (v0.2+ candidate)
