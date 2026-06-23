# Phase 7B Closeout Report — API Layer: Read-Only Report Routes

**Date:** 2026-06-23
**Phase:** 7B — API layer: FastAPI routes
**Status:** Implementation complete. Awaiting human acceptance audit before v0.1 is declared done.

---

## 1. Scope implemented

Phase 7B implements the minimal read-only FastAPI API layer under `backend/app/api/`.
The API exposes three GET-only routes:
- `GET /health` — smoke-test endpoint; no data access
- `GET /reports/daily?report_date=YYYY-MM-DD` — daily report
- `GET /reports/weekly?week_start=YYYY-MM-DD&report_date=YYYY-MM-DD` — weekly report

Each report route follows the approved orchestration sequence (D-062):
connection → `init_schema` → `SQLiteDataAdapter` → holdings/prices/journal entries
→ metrics engine → alert engine → report builder → `dataclasses.asdict()` → JSON.

The `DataAdapter` ABC was extended with `get_journal_entries(date_from, date_to)` (D-066)
so that route modules access journal data through the adapter boundary, not directly
through persistence repos.

---

## 2. Files created

| File | Purpose |
|---|---|
| `backend/app/api/app.py` | FastAPI app instance; mounts health and report routers |
| `backend/app/api/deps.py` | Per-request DB connection dependency (D-061) |
| `backend/app/api/routes/__init__.py` | Routes sub-package |
| `backend/app/api/routes/health.py` | `GET /health` — no data access |
| `backend/app/api/routes/reports.py` | `GET /reports/daily`, `GET /reports/weekly` |
| `backend/main.py` | ASGI entry point; exposes `app` for uvicorn |
| `backend/tests/integration/test_api_reports.py` | 49 API integration tests |
| `docs/reports/PHASE7B_CLOSEOUT.md` | This file |

---

## 3. Files modified

| File | Change |
|---|---|
| `backend/pyproject.toml` | Added `fastapi>=0.100.0` runtime dep; added `dev = ["httpx2"]` optional dep |
| `backend/app/api/__init__.py` | Updated docstring to reflect Phase 7B implementation |
| `backend/app/data/adapters/base.py` | Added `get_journal_entries(date_from, date_to)` abstract method; imported `JournalEntry` |
| `backend/app/data/adapters/sqlite_adapter.py` | Implemented `get_journal_entries`; added `JournalRepo` as internal repo |
| `backend/app/data/persistence/journal_repo.py` | Added `get_by_date_range(date_from, date_to)`; added `InvalidDateError`/`validate_iso_date` imports |
| `backend/app/data/persistence/db.py` | Added `check_same_thread=False` to `sqlite3.connect()` (D-061) |
| `docs/DECISIONS.md` | Appended D-058 through D-066 |
| `docs/ROADMAP.md` | Phase 7B status updated to complete (awaiting audit); Phase 7B acceptance criteria added |
| `PROJECT_BRAIN.md` | Phase 7B status updated; D-058–D-066 added to decision index; completion summary updated |
| `docs/ARCHITECTURE.md` | Module boundary table updated to reflect `api/routes/` and `api/deps.py` boundaries (D-066) |

---

## 4. Route behavior

### GET /health
- Returns `{"status": "ok"}` with HTTP 200.
- No DB access. No metrics. No external calls.

### GET /reports/daily?report_date=YYYY-MM-DD
- `report_date` is required. Invalid format → HTTP 422 with `{error, field, value, message}`.
- Opens connection via `deps.get_conn()`.
- `adapter = SQLiteDataAdapter(conn)`.
- `holdings = adapter.get_holdings()`.
- `prices = adapter.get_prices()`.
- `journal_entries = adapter.get_journal_entries(date_from=report_date, date_to=report_date)`.
- Computes snapshot, drawdown, volatility, evaluates all four alert rules.
- `report = build_daily_report(report_date, snapshot, alert_results, journal_entries)`.
- Returns `dataclasses.asdict(report)` as JSON.

### GET /reports/weekly?week_start=YYYY-MM-DD&report_date=YYYY-MM-DD
- Both params required. Invalid dates → HTTP 422. `week_start > report_date` → HTTP 422
  with `{error: "invalid_date_range", field: "week_start"}`.
- Same adapter/metrics/alerts sequence as daily.
- `journal_entries = adapter.get_journal_entries(date_from=week_start, date_to=report_date)`.
- `report = build_weekly_report(report_date, week_start, snapshot, drawdown, volatility, alert_results, journal_entries)`.
- Returns `dataclasses.asdict(report)` as JSON.

---

## 5. API boundary rules enforced

- `api/routes/*.py` imports no persistence repos (`HoldingsRepo`, `JournalRepo`, etc.).
- `api/routes/*.py` does not import `sqlite3`.
- `api/routes/*.py` contains no external HTTP client imports.
- `api/routes/*.py` contains no `POST`, `PUT`, `PATCH`, or `DELETE` decorators.
- `api/deps.py` owns the connection lifecycle: opens, calls `init_schema`, yields, closes.
- `backend/main.py` does not call `uvicorn.run`.

---

## 6. DataAdapter journal extension (D-066)

`DataAdapter` ABC (`base.py`) gains:
```python
@abstractmethod
def get_journal_entries(self, date_from: str, date_to: str) -> list[JournalEntry]:
    ...
```

`SQLiteDataAdapter` implements it by delegating to `JournalRepo.get_by_date_range()`.

`JournalRepo` gains `get_by_date_range(date_from, date_to)`:
- Validates both dates with `validate_iso_date()`.
- Raises `InvalidDateError` if `date_from > date_to`.
- Returns entries with `entry_date >= date_from AND entry_date <= date_to`.
- Orders by `entry_date DESC, created_at DESC` (consistent with D-049).
- Never compliance-scans user-authored fields.

---

## 7. Serialization behavior

`dataclasses.asdict(report)` converts the frozen `DailyReport` / `WeeklyReport`
dataclasses recursively. All nested `ReportSection` and `JournalEntry` objects
become plain Python dicts. All field types (`str`, `int`, `list`, `None`) are
JSON-serializable. FastAPI serializes the returned dict to JSON.

Journal text in `journal_entries` is carried verbatim through `asdict()` without
rewriting, paraphrasing, or compliance scanning. Consistent with D-046, D-054, D-063.

---

## 8. Compliance behavior

- Every system-generated `ReportSection` was compliance-checked by the report builder
  before the route received it (D-054). The API layer does not call `check_compliance()`
  again on system text.
- User-authored journal fields are never compliance-scanned at any layer.
- Error responses contain no advisory language, no forbidden terms, and no user-authored text.
- No new system-generated text is added by the API layer.

---

## 9. Dependency injection for tests

Tests use `app.dependency_overrides[get_conn]` to inject an isolated in-memory
SQLite connection instead of the production DB path. Data is seeded through existing
repos (`HoldingsRepo`, `PricesRepo`, `JournalRepo`) before each test request.
The `check_same_thread=False` flag (D-061) allows the test-thread-created connection
to be used inside FastAPI's thread-pool-based sync handler execution.

---

## 10. Test results

```
500 passed, 0 skipped
```

Previous count: 451 (Phase 7A). New tests: +49 (all in `tests/integration/test_api_reports.py`).

Test categories:
- Health route: 1 test
- Daily report structure: 5 tests
- Daily report metrics content: 2 tests
- Daily report alert behavior: 3 tests
- Daily report journal filtering: 3 tests
- Daily report compliance: 1 test
- Weekly report structure: 6 tests
- Weekly report metrics and journal: 4 tests
- Edge cases (empty/unpriced portfolio, no journal): 3 tests
- Error handling (invalid dates, missing params): 7 tests
- DataAdapter/JournalRepo extension: 8 tests
- Boundary checks (no forbidden imports, no write decorators): 6 tests

Architecture invariant: all three tests still pass (no broker, no execution, no advisory).

---

## 11. Decisions recorded

| Decision | Summary |
|---|---|
| D-058 | Phase 7B API boundary: read-only routes only |
| D-059 | FastAPI dependency: `fastapi>=0.100.0` runtime; `httpx2` dev; no uvicorn |
| D-060 | API date params: required caller-provided ISO dates; 422 on invalid |
| D-061 | API DB path: D-023 policy; per-request connection; `check_same_thread=False` |
| D-062 | API orchestration sequence |
| D-063 | Serialization: `dataclasses.asdict()`; journal text verbatim |
| D-064 | Alert inclusion: embedded in report sections; no separate alerts array |
| D-065 | v0.1 completion: accepted after audit, not merely implementation |
| D-066 | DataAdapter journal extension: `get_journal_entries` on ABC and adapter |

---

## 12. Out-of-scope items (not implemented)

- Frontend UI
- Notification delivery (email, SMS, push)
- Scheduled jobs / cron
- External market data API calls
- HTTP clients for external services in application code
- Web scraping
- Technical indicators / backtesting / paper trading / live trading
- Broker integration / order placement
- Portfolio optimization / instrument ranking
- Authentication / user accounts
- Cloud deployment
- Multi-portfolio / multi-currency aggregation
- Write routes (`POST`, `PUT`, `PATCH`, `DELETE`)
- Buy / sell / hold / target-price / profit / opportunity language
- AI-generated decisions or directional market views
- Async route handlers
- uvicorn as a project dependency

---

## 13. Deviations from implementation prompt

**One addition beyond the prompt:**
`check_same_thread=False` was added to `sqlite3.connect()` in `db.py`. This was
necessary because FastAPI runs synchronous route handlers in a thread pool via
`anyio.to_thread.run_sync`. Without this flag, the SQLite connection (created in the
test fixture's thread) cannot be used by the route handler running in a worker thread.
In production the flag is also correct: each connection is owned by exactly one request
at a time, so there is no actual concurrent access across threads. This change is
recorded in D-061.

**httpx2 instead of httpx:**
starlette 1.2.1 requires `httpx2` for `TestClient` (httpx deprecated). The
`[project.optional-dependencies] dev` section uses `httpx2` instead of the
`httpx>=0.23.0` specified in the planning report. The behavior is identical.
This is recorded in D-059.

No other deviations from the implementation prompt.

---

*Phase 7B implementation complete. Awaiting human acceptance audit.*
