# ARCHITECTURE.md

## Guiding principles

1. **Boundaries before logic.** Every module is a named boundary with a clear contract.
   Logic is added phase by phase, never speculatively.
2. **The metrics engine is pure.** No I/O in `metrics/`. All data flows in as arguments;
   all results flow out as return values.
3. **All data access through DataAdapter.** Nothing outside `data/` reads the database
   directly. The adapter is the only gate.
4. **Compliance is a chokepoint.** All system-generated user-facing text passes through
   `compliance/` before reaching the user.
5. **No execution, ever.** The `api/` layer has no endpoints that place, cancel, or modify
   any market position. The architecture test enforces this continuously.

---

## Stack

| Layer | Technology |
|---|---|
| Backend language | Python ≥ 3.11 |
| Backend framework | FastAPI |
| Local database | SQLite (via stdlib `sqlite3`) |
| Test runner | pytest |
| Frontend language | TypeScript |
| Frontend framework | React / Vite |
| Package manager (Python) | pip / pyproject.toml |

---

## Module map

```
backend/app/
  api/             FastAPI router boundary. No execution endpoints. Routes added Phase 3+.
  core/            Shared domain types and models. Dataclasses / Pydantic. Phase 2.
  data/
    adapters/      DataAdapter ABC — the only interface through which other modules read data.
                   Concrete: SQLiteAdapter. Phase 2.
    persistence/   SQLite repositories. Write-side of the DB. Phase 2.
  metrics/         Pure metrics engine. No I/O. Phase 4.
  alerts/          Alert rule evaluation. Reads metrics, emits alert objects. Phase 5.
  compliance/      Safety guard. Scans all generated text before it reaches the user. Phase 5.
  journal/         Decision journal CRUD. Append-only. Phase 6.
  reports/         Report assembly (daily / weekly). Phase 7.
```

---

## Data flow (v0.1)

```
CSV file
  → CSV Adapter (Phase 3)
    → Validation (core/validation.py)
      → SQLite Repositories (data/persistence/)
        → DataAdapter (data/adapters/)
          → Metrics Engine (metrics/) — pure
          → Alert Engine (alerts/)
            → Compliance Guard (compliance/)
              → API layer (api/)
                → Frontend
```

---

## Architectural invariants (enforced by test)

The following must hold at all times. The file
`backend/tests/architecture/test_no_broker_no_execution.py` scans all source files and
fails the build if any violation is found.

1. No broker API library is imported anywhere in `backend/app/` or `frontend/src/`.
2. No function named `place_order`, `execute_order`, `submit_order`, `buy_stock`,
   `sell_stock`, `paper_trade`, or `run_backtest` exists in application source.
3. No advisory function names (`get_buy_signal`, `get_sell_signal`,
   `get_hold_recommendation`, `generate_trade_signal`) exist in application source.

---

## Module boundary rules

| Caller | May read from | May NOT read from |
|---|---|---|
| `metrics/` | Arguments passed in | DB, filesystem, network |
| `alerts/` | `metrics/` output, `data/adapters/` | DB directly, `persistence/` |
| `api/` | `data/adapters/`, `metrics/`, `alerts/`, `reports/` | `persistence/` directly |
| `reports/` | `data/adapters/`, `metrics/`, `alerts/` | DB directly |
| `journal/` | `data/adapters/` | `metrics/` (journal is independent) |

---

## Phase gates

Each phase adds logic to exactly one layer. Empty `__init__.py` boundaries exist from
Phase 1 so that the module map is always correct even before implementation.

| Phase | Layer(s) touched |
|---|---|
| 1 | Skeleton only — empty boundaries + architecture test |
| 2 | `core/`, `data/persistence/`, `data/adapters/` |
| 3 | `data/adapters/` (CSV adapter) |
| 4 | `metrics/` |
| 5 | `alerts/`, `compliance/` |
| 6 | `journal/` |
| 7 | `reports/`, `api/` |
| 8 | Research boundary review (Tier 3 gate) |
