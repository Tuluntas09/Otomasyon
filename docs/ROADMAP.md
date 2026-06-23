# ROADMAP.md

## Phase status

| Phase | Name | Status |
|---|---|---|
| 0 | Documentation | ✅ accepted |
| 1 | Empty skeleton | ✅ complete |
| 2 | Data model + local storage | ✅ complete — awaiting human review |
| 3 | CSV data adapter | ✅ complete — awaiting human review |
| 4 | Metrics engine | ⛔ not started |
| 5 | Alerts + compliance guard | ⛔ not started |
| 6 | Decision journal | ⛔ not started |
| 7 | Reports + API layer | ⛔ not started |
| 8 | Tier 3 gate review (paper trading research boundary) | ⛔ not started |

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

**Status:** ⛔ Not started.

---

## Phase 5 — Alerts + compliance guard

**Scope:** Implement alert rule evaluation and the compliance guard. All system-generated
text routed through the guard from this phase onward.

**Status:** ⛔ Not started.

---

## Phase 6 — Decision journal

**Scope:** Implement journal entry CRUD (append-only writes, queries).

**Status:** ⛔ Not started.

---

## Phase 7 — Reports + API layer

**Scope:** Assemble daily/weekly reports. Wire FastAPI routes for frontend consumption.

**Status:** ⛔ Not started.

---

## Phase 8 — Tier 3 gate review

**Scope:** Evaluate whether Tier 3 (paper trading research boundary) is appropriate.
This is a deliberate review gate, not a development phase. Tier 3 requires a new
`DECISIONS.md` entry and explicit human approval before any code is written.

**Status:** ⛔ Not started.

---

## Off-roadmap (will not be implemented without major re-scoping)

- Live trading (Tier 4)
- Broker API integration
- News scraping / sentiment
- Arbitrage detection
- ML trade signals
- Multi-currency aggregation (v0.2+ candidate)
- Multi-portfolio (v0.2+ candidate)
