# PHASE1_SKELETON_PLAN.md

## Purpose

This document specifies exactly what Phase 1 creates. Phase 1 is an empty skeleton — it
establishes every module boundary and the one substantive architectural test. No application
logic is written. The goal is a green test suite on an empty codebase.

---

## Deliverables

### 1. Git repository

- `git init` in the project root.
- No CI/CD wired yet; `ci/` is a stub directory only.

### 2. Top-level structure

```
README.md                    project front door + disclaimer
PROJECT_BRAIN.md             orientation document (pre-existing)
docs/                        all specification documents
backend/                     Python backend
frontend/                    React/Vite frontend (empty shell)
ci/                          CI stub
```

### 3. Documentation (`docs/`)

All documents listed in `PROJECT_BRAIN.md §7` are present. Content is concise but
coherent — enough to guide Phase 2 implementation without speculative detail.

Files:
- `PRODUCT_PLAN.md`
- `MVP_SCOPE.md`
- `RISK_POLICY.md`
- `ALERT_POLICY.md`
- `METRICS_SPEC.md`
- `JOURNAL_SCHEMA.md`
- `DATA_SOURCES.md`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `TEST_PLAN.md`
- `DECISIONS.md` (contains D-013 through D-019)
- `PHASE1_SKELETON_PLAN.md` (this file)
- `reports/.gitkeep` (empty placeholder for future phase closeout reports)

### 4. Backend package boundaries

Each `__init__.py` contains only a module-level docstring. No imports, no classes, no
functions, no logic.

```
backend/
  pyproject.toml             pytest configured; runtime deps = []
  app/
    __init__.py
    api/__init__.py          "FastAPI boundary — no execution endpoints."
    core/__init__.py         "Shared domain types and models."
    data/__init__.py         "Data layer."
    data/adapters/__init__.py    "DataAdapter abstract interface."
    data/persistence/__init__.py "SQLite persistence repositories."
    metrics/__init__.py      "Pure metrics engine — no I/O."
    alerts/__init__.py       "Alert rule evaluation engine."
    compliance/__init__.py   "Compliance safety guard."
    journal/__init__.py      "Decision journal."
    reports/__init__.py      "Report assembly."
```

### 5. Backend tests

```
backend/tests/
  __init__.py
  architecture/
    __init__.py
    test_no_broker_no_execution.py    ← 3 substantive passing tests
  unit/
    __init__.py
    test_phase2_placeholder.py        ← 3 skipped (phase gate)
    test_phase3_placeholder.py        ← 3 skipped (phase gate)
  integration/
    __init__.py
    test_phase2_placeholder.py        ← 3 skipped (phase gate)
```

**Expected pytest result:** `3 passed, 9 skipped`

### 6. Architecture test content

`test_no_broker_no_execution.py` contains exactly three test functions:

1. `test_no_broker_integration` — scans `backend/app/` and `frontend/src/` for broker
   library import statements (alpaca, ibkr, ccxt, robinhood, etc.).
2. `test_no_execution_logic` — scans for execution function or class definitions
   (`place_order`, `execute_order`, `paper_trade`, `run_backtest`, etc.).
3. `test_no_advisory_language_in_source` — scans for advisory function/variable names
   (`get_buy_signal`, `sell_signal`, `hold_recommendation`, etc.).

**Excluded from scan:** `backend/tests/`, `docs/`, `PROJECT_BRAIN.md`, `README.md`.
Rationale: policy documents mention prohibited words to ban them; scanning them would
produce false positives.

### 7. Frontend shell

```
frontend/
  src/
    components/
      safety/
        .gitkeep
        README.md    "Safety disclaimer UI component — implementation deferred to Phase 3+."
```

No React code, no TypeScript, no package.json yet.

### 8. CI stub

```
ci/
  README.md    "CI configuration — implementation deferred."
```

---

## What Phase 1 does NOT create

- SQLite schema or database file.
- Domain models (`Holding`, `WatchlistEntry`, `PriceRecord`).
- DataAdapter implementation.
- CSV parsing logic.
- Metrics computation.
- Alert rules.
- Compliance guard logic.
- Journal logic.
- FastAPI routes.
- React components with logic.
- Any application dependency beyond pytest.

---

## Acceptance criteria

- `git status` shows a clean working tree after commit.
- `python -m pytest` from `backend/` returns exactly `3 passed, 9 skipped`.
- No application logic exists in any `backend/app/` module.
- Architecture invariant test passes on the empty codebase.
- `PROJECT_BRAIN.md` status block accurately reflects Phase 1 as complete.
