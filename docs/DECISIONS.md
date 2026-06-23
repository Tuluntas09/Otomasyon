# DECISIONS.md

Append-only decision log. Each entry records a locked decision, the date it was made, the
options considered, and the rationale. Entries are never deleted or overwritten — add a
superseding entry instead.

---

## D-013 — Stack selection

**Date:** 2025-06 (Phase 0)
**Decision:** Python / FastAPI (backend) + React / Vite (frontend) + SQLite (local DB) +
pytest (test runner). Manual refresh first; no real-time data infrastructure in v0.1.
**Options considered:** Node/Fastify backend (rejected — Python ecosystem better suited for
numeric/data work; team familiarity).
**Rationale:** Mature, well-documented stack; SQLite keeps local-first promise with zero
infrastructure overhead.

---

## D-014 — Base currency

**Date:** 2025-06 (Phase 0)
**Decision:** USD-only in v0.1. Non-USD inputs are flagged and excluded — never silently
converted or summed.
**Rationale:** Multi-currency aggregation introduces FX risk and conversion complexity out of
scope for v0.1. Explicit exclusion prevents silent errors.

---

## D-015 — First data path

**Date:** 2025-06 (Phase 0)
**Decision:** CSV / file import is the first and only data path in v0.1. No external market
data API provider is chosen in Phase 0.
**Rationale:** CSV-first keeps the tool offline-capable and avoids binding to any provider's
Terms of Service before a ToS review checklist is completed.

---

## D-016 — Negative quantities

**Date:** 2025-06 (Phase 0)
**Decision:** Negative quantities are rejected on input. No short positions in v0.1.
**Rationale:** Short selling introduces margin, leverage, and loss-beyond-principal risk that
are out of scope for this instrument's v0.1 safety posture.

---

## D-017 — Duplicate tickers

**Date:** 2025-06 (Phase 0)
**Decision:** Duplicate tickers are rejected on input. No silent merging of lots.
**Rationale:** Silent lot-merging could mask cost-basis errors. Explicit rejection forces the
user to resolve ambiguity before it enters the system.

---

## D-018 — Single portfolio

**Date:** 2025-06 (Phase 0)
**Decision:** Single portfolio only in v0.1. No `portfolio_id` foreign key required.
**Rationale:** Multi-portfolio support adds schema and UI complexity that is out of scope for
v0.1. The single-portfolio constraint is a hard boundary, not an oversight.

---

## D-019 — Phase 0 acceptance

**Date:** 2025-06 (Phase 0)
**Decision:** Phase 0 documents are accepted for planning purposes only — not as
implementation approval. Each subsequent phase requires its own human review gate.
**Rationale:** Separating doc acceptance from implementation approval prevents scope creep
and ensures each phase is consciously authorized.

---

## D-020 — SQLite driver: synchronous stdlib sqlite3

**Date:** 2026-06-23 (Phase 2)
**Decision:** Use synchronous `stdlib sqlite3` for all database access in Phase 2. Do not
add `aiosqlite` or any async DB driver.
**Options considered:** `aiosqlite` (rejected — FastAPI async endpoints are not implemented
until Phase 7; adding async I/O now would add complexity with no benefit).
**Rationale:** The persistence layer is accessed from synchronous code in Phases 2–6.
Switching to async can be deferred to Phase 7 when the API layer is introduced, and only if
benchmarks justify it.

---

## D-021 — Watchlist duplicate ticker behaviour

**Date:** 2026-06-23 (Phase 2)
**Decision:** Inserting a ticker that already exists in the watchlist raises
`DuplicateTickerError`. No silent update or merge.
**Rationale:** Consistent with D-017 (holdings duplicate policy). Explicit rejection forces
the caller to be intentional; silent merging could mask data entry errors.

---

## D-022 — Price duplicate behaviour on (ticker, price_date)

**Date:** 2026-06-23 (Phase 2)
**Decision:** Inserting a price record where (ticker, price_date) already exists performs
an upsert — the newer value wins. No error is raised.
**Rationale:** End-of-day price CSV files may be re-ingested (e.g., after a correction).
Upsert makes re-ingestion idempotent. Unlike holdings or watchlist entries, a price
correction for the same date is a legitimate and expected operation.

---

## D-023 — DB file location: OTOMASYON_DB_PATH environment variable

**Date:** 2026-06-23 (Phase 2)
**Decision:** The SQLite database file path is read from the `OTOMASYON_DB_PATH` environment
variable, defaulting to `./data/otomasyon.db` relative to the process working directory.
**Options considered:** `DATABASE_URL` (rejected — that convention implies a URL-format
string; `sqlite3` takes a plain file path; using `OTOMASYON_DB_PATH` avoids the mismatch
and is more discoverable for a local-first tool).
**Rationale:** Environment variable override allows tests to use `:memory:` without
patching code. The project-specific name (`OTOMASYON_DB_PATH`) avoids collisions with
other tools in the same environment.

---

## D-024 — CSV parser: stdlib csv only

**Date:** 2026-06-23 (Phase 3)
**Decision:** Use Python stdlib `csv.DictReader` for all CSV parsing. No `pandas`, `polars`,
`numpy`, or any third-party CSV library.
**Rationale:** `pyproject.toml` keeps `dependencies = []`. `csv.DictReader` satisfies all
v0.1 requirements (header-based parsing, comma delimiter, string extraction) with zero
added dependencies.

---

## D-025 — CSV import transaction behavior

**Date:** 2026-06-23 (Phase 3)
**Decision:** Holdings and watchlist imports are all-or-nothing. Pass 1 validates every row
and pre-checks DB duplicates (loading existing tickers from the repo) before any write
begins. Pass 2 writes only when Pass 1 produced zero errors. Any failure raises
`CsvImportError`. Prices imports use row-level error collection: valid rows are upserted
immediately; invalid rows are appended to `ImportResult.errors`; the function always
returns an `ImportResult` and never raises `CsvImportError`.
**Options considered:** all-or-nothing for all three types (simpler, but would make
re-ingesting large price files impractical if one row is malformed).
**Rationale:** A portfolio is only meaningful when complete — partial holdings produce wrong
metrics. Price records are independent; partial ingestion is safe and consistent with the
D-022 upsert policy that already assumes re-imports are normal.

---

## D-026 — Supported CSV import types in v0.1

**Date:** 2026-06-23 (Phase 3)
**Decision:** Three import types are supported: `holdings`, `watchlist`, `prices`. Each has
its own named function (`import_holdings_csv`, `import_watchlist_csv`,
`import_prices_csv`). No generic dispatcher is implemented in Phase 3.
**Rationale:** Three types map directly to the three Phase 2 repositories. Direct function
calls are more Pythonic and remove indirection with no current consumer to justify it.

---

## D-027 — Required CSV columns per import type

**Date:** 2026-06-23 (Phase 3)
**Decision:**

| Import type | Required columns |
|---|---|
| holdings | `ticker`, `quantity`, `cost_basis`, `currency` |
| watchlist | `ticker` |
| prices | `ticker`, `date`, `close`, `currency` |

Absence of any required column raises `MissingColumnError` after reading the header row,
before any data rows are processed.
**Rationale:** Column names match `DATA_SOURCES.md` exactly for holdings and prices.
Watchlist format is new in Phase 3; `ticker` is the only meaningful field.

---

## D-028 — Unknown extra CSV columns: ignore

**Date:** 2026-06-23 (Phase 3)
**Decision:** Extra columns beyond the required set are silently ignored.
**Options considered:** warn (no output mechanism exists yet in Phase 3); reject (breaks
CSV exports from spreadsheets or brokerage tools that include metadata columns).
**Rationale:** Ignoring extra columns reduces friction with zero safety risk — the importer
only reads the named columns it needs. Rejecting them would force users to manually clean
exports.

---

## D-029 — CSV delimiter: comma only

**Date:** 2026-06-23 (Phase 3)
**Decision:** Comma (`,`) is the only supported delimiter in v0.1. `csv.Sniffer` is not
used.
**Options considered:** `csv.Sniffer` for automatic detection (rejected — unreliable on
short files; a wrong sniff silently produces malformed parses).
**Rationale:** Comma is the universal standard and matches any spreadsheet CSV export
default. If the user provides a non-comma-delimited file, the `MissingColumnError` on the
header check surfaces it clearly.

---

## D-030 — Metrics engine purity boundary

**Date:** 2026-06-23 (Phase 4)
**Decision:** `backend/app/metrics/` must not import `sqlite3`, `csv`, `os`, `pathlib`,
any network library (`requests`, `httpx`, `aiohttp`), `app.data.persistence.*`, or
`app.data.adapters.*`. All data arrives as function arguments (`list[Holding]`,
`list[PriceRecord]`). No environment variables, no file I/O, no network access, no
dependence on the system clock. Enforced by boundary tests in `test_metrics.py`.
**Rationale:** Purity is a non-negotiable invariant per `PROJECT_BRAIN.md` §2 and
`ARCHITECTURE.md` §2. Pure functions are trivially testable, deterministic, and composable
with any future data source without modification.

---

## D-031 — Valuation date policy: latest available input price date

**Date:** 2026-06-23 (Phase 4)
**Decision:** The metrics engine does not accept an explicit "as-of date" parameter.
It always uses the most recent `price_date` in the `price_records` list supplied as input
as its reference point. Time windows (drawdown, volatility) are measured backwards from
that latest input date — never from `date.today()`, `datetime.now()`, or any system clock.
**Options considered:** Explicit `as_of_date` parameter (rejected for Phase 4 — filtering
belongs in the orchestration layer, not the pure engine; callers pass pre-filtered data).
**Rationale:** System-clock dependence would make tests fragile (date-sensitive) and
violate the determinism invariant. Caller-provided data defines the temporal context.

---

## D-032 — Missing price behavior: exclude from valuation and report

**Date:** 2026-06-23 (Phase 4)
**Decision:** A `Holding` with no corresponding `PriceRecord` in the input is excluded
from market value, weight, and unrealised-change calculations. It is never valued at zero
(zero would corrupt weight percentages). `PortfolioSnapshot.unpriced_tickers` lists
every excluded holding. For time-series metrics (M-005, M-006), portfolio value on a given
date is the sum of `quantity × close_price` for holdings that have a price on that date;
dates where a holding has no price are included in the series using the holdings that do
have prices; `min_coverage_ratio` and `latest_coverage_ratio` in `DrawdownResult` and
`VolatilityResult` expose the data quality so callers can surface warnings.
**Rationale:** Silently valuing a missing price at zero corrupts all percentage calculations
downstream. Explicit exclusion with reporting is more transparent and consistent with the
project's policy of surfacing data quality issues rather than hiding them.

---

## D-033 — Numeric precision: Python float, no engine-side rounding

**Date:** 2026-06-23 (Phase 4)
**Decision:** All internal and result values use Python `float` (IEEE 754 double precision).
No `Decimal`. No rounding inside the engine. All result dataclass fields that hold computed
values are `float` (or `float | None`). Callers and formatters apply display rounding.
**Rationale:** EOD portfolio metrics do not require accounting-grade reconciliation.
`Decimal` adds complexity with no v0.1 benefit. Returning raw floats lets the alert engine
(Phase 5) compare thresholds cleanly without double-rounding artifacts.

---

## D-034 — M-006 return basis: percentage returns, population standard deviation

**Date:** 2026-06-23 (Phase 4)
**Decision:** M-006 computes standard deviation of **daily percentage returns**
`(v[t] - v[t-1]) / v[t-1]`, not absolute dollar changes. Standard deviation is computed
using `statistics.pstdev` (population std dev). The result is not annualised (v0.1
constraint per `METRICS_SPEC.md`). If `v[t-1] == 0.0`, that return is skipped.
**Options considered:** Dollar-change std dev (rejected — scale-dependent; grows with
portfolio value, making alert thresholds non-portable across portfolio sizes).
**Rationale:** `ALERT_POLICY.md` example shows "2.8%", implying a dimensionless result.
Percentage returns are scale-independent. Population std dev is appropriate because we
are measuring the actual returns in the window, not estimating an unobserved population
parameter.

---

## D-035 — Phase 4 scope: both snapshot and time-series metrics (M-001 through M-006)

**Date:** 2026-06-23 (Phase 4)
**Decision:** Phase 4 implements all six v0.1 metrics from `METRICS_SPEC.md`. M-001
through M-004 are snapshot metrics (no price history required beyond the latest price
per ticker). M-005 (drawdown from peak) and M-006 (30-day return volatility proxy) are
time-series metrics computed from the supplied price history. Minimum data requirements:
M-005 requires at least 1 date in the window; M-006 requires at least 2 dates (to produce
at least 1 daily return). Both return `None` when minimum data is not met — they never
raise for insufficient data.
**Rationale:** Deferring M-005 and M-006 to a later phase would leave the alert engine
(Phase 5) without the drawdown and volatility inputs it needs. All six metrics are
defined in `METRICS_SPEC.md` for v0.1; implementing them together is the right gate.

---

## D-036 — Alert engine boundary

**Date:** 2026-06-23 (Phase 5)
**Decision:** The alert engine (`backend/app/alerts/`) receives already-computed metric
result objects (`PortfolioSnapshot`, `DrawdownResult | None`, `VolatilityResult | None`)
and an `AlertConfig`. It does not call Phase 4 metric functions, does not access the
database, and performs no file or network I/O. It returns a list of `AlertResult` objects.
**Rationale:** Keeping the alert engine as a pure consumer of metric results (not a
producer) preserves the same purity invariant that governs the metrics engine. It also
makes alert evaluation trivially testable without any database fixtures.

---

## D-037 — AlertConfig: caller-provided thresholds with conservative defaults

**Date:** 2026-06-23 (Phase 5)
**Decision:** Alert thresholds are expressed as a frozen `AlertConfig` dataclass supplied
by the caller. Conservative defaults: concentration 0.25, drawdown 0.15, volatility 0.02,
max_unpriced_holdings 0.
**Rationale:** Frozen dataclasses prevent accidental mutation. Caller-supplied config
decouples threshold policy from engine logic. Conservative defaults ensure the engine
is safe out of the box.

---

## D-038 — AlertResult schema: all evaluations returned, not only fired ones

**Date:** 2026-06-23 (Phase 5)
**Decision:** `AlertResult` is a frozen dataclass with fields: `rule_id`, `fired`,
`severity`, `metric_value`, `threshold`, `explanation`, `ticker`. `evaluate_alerts`
returns a result for every evaluated rule, not only the ones that fired.
**Rationale:** Returning all results (including non-firing ones) lets callers display
a complete picture — showing that a rule was evaluated and did not fire is informative
in itself. It avoids silent absence where a missing result is ambiguous.

---

## D-039 — Compliance guard behavior: raise with all violations, never rewrite

**Date:** 2026-06-23 (Phase 5)
**Decision:** `check_compliance(text)` passes silently for compliant or empty text.
If any forbidden term is found it raises `ComplianceViolationError` listing every matched
term. It never rewrites, sanitizes, or truncates the input text.
**Rationale:** Silently sanitizing text would allow non-compliant strings to reach the
user in a modified form without the developer being alerted. Hard failure forces the
caller to supply compliant text from the outset.

---

## D-040 — Compliance as a hard chokepoint inside evaluate_alerts

**Date:** 2026-06-23 (Phase 5)
**Decision:** Every alert explanation is passed through `check_compliance()` inside
`evaluate_alerts`, before the `AlertResult` is constructed. If `check_compliance` raises,
the error propagates to the caller.
**Rationale:** This makes compliance non-optional — no `AlertResult` can exist with an
explanation that has not been checked. It is consistent with `ARCHITECTURE.md` §4:
"Compliance is a chokepoint."

---

## D-041 — Severity labels: informational, watch, elevated only

**Date:** 2026-06-23 (Phase 5)
**Decision:** Alert severity uses exactly three labels: `"informational"` (not fired),
`"watch"` (fired, value ≤ 2× threshold), `"elevated"` (fired, value > 2× threshold).
Labels `"urgent"`, `"critical"`, and any action-oriented label are prohibited.
**Rationale:** Action-oriented severity labels (urgent, critical) imply the user must act.
This violates the policy that alerts describe facts, not prescribe action.

---

## D-042 — Compliance matching: whole-word for single terms, bounded phrase for multi-word

**Date:** 2026-06-23 (Phase 5)
**Decision:** Single-word forbidden terms use `\b<term>\b` (whole-word, case-insensitive,
Unicode). Multi-word phrases use `\b<phrase>\b` with word boundaries only at the start and
end of the phrase. Explicit false-positive verifications: "threshold" does not trigger
"hold"; "glossy" does not trigger "loss"; "total" and "capital" do not trigger Turkish "al"
— all confirmed by `\b` semantics (the preceding character is a word character, so no
boundary exists before the substring).
**Rationale:** Whole-word matching prevents substring false positives. Unicode flag
ensures Turkish characters (ı, ş, ç, ğ, ö, ü, etc.) are treated as word characters.

---

## D-043 — Alert threshold equality: strict greater-than only

**Date:** 2026-06-23 (Phase 5)
**Decision:** All alert rule comparisons use strict greater-than (`>`). A metric value
exactly equal to the threshold does NOT fire the alert. This applies to all four rules:
CONC-001, DD-001, VOL-001, and COV-001.
**Rationale:** Alert wording uses "above", "exceeds", and "ceiling breach" semantics.
Firing at exact equality would contradict "above the ceiling of X%" when the value IS X%.
Strict greater-than is also consistent with standard threshold-alarm conventions.

---

## D-044 — Journal persistence location

**Date:** 2026-06-23 (Phase 6)
**Decision:** The `journal_entries` table is added to the existing SQLite database via
`CREATE TABLE IF NOT EXISTS` in `backend/app/data/persistence/db.py`. The journal
persistence repository lives at `backend/app/data/persistence/journal_repo.py`, not under
`backend/app/journal/`. The `journal/` module contains domain model and validation only.
**Rationale:** All SQLite access must remain under `backend/app/data/persistence/` per the
architecture boundary. Mixing persistence into the domain module would break the layering
invariant enforced by architecture tests.

---

## D-045 — Journal append-only constraint

**Date:** 2026-06-23 (Phase 6)
**Decision:** `JournalRepo` exposes `add_entry()`, `get_all()`, and `get_by_ticker()` only.
No `update()` or `delete()` methods exist. Multiple entries for the same ticker are allowed.
**Rationale:** The decision journal is a factual record of past reasoning. Editing or
deleting past entries would undermine its value as an honest log. Append-only semantics
match `JOURNAL_SCHEMA.md` ("entries are append-only").

---

## D-046 — User-authored journal text and the compliance guard

**Date:** 2026-06-23 (Phase 6)
**Decision:** `check_compliance()` is NOT called on `action_taken`, `reasoning`,
`hypothesis`, or `tags`. These fields are stored verbatim as user-authored private notes.
**Rationale:** `JOURNAL_SCHEMA.md` states: "action_taken and reasoning fields are the
user's own words — they are not scanned by the compliance guard (they record past facts,
not system advice)." Compliance scanning is reserved for system-generated text only.

---

## D-047 — action_taken field name retained

**Date:** 2026-06-23 (Phase 6)
**Decision:** The field is named `action_taken` as specified in `JOURNAL_SCHEMA.md`.
It is user-authored past-tense record text describing what the user did, not
system-generated advice.
**Rationale:** `action_taken` accurately names the field's semantics (past tense, user
record) and does not imply any system recommendation or advisory signal.

---

## D-048 — review_date must be strictly after entry_date

**Date:** 2026-06-23 (Phase 6)
**Decision:** If `review_date` is provided, it must be strictly after `entry_date`.
Equal dates raise `JournalValidationError`. `None` is always valid.
**Rationale:** A review date equal to the entry date is logically meaningless — the user
cannot review a decision on the same day it was recorded in a forward-looking sense.
Strict inequality matches `JOURNAL_SCHEMA.md`: "must be a valid ISO-8601 date after entry_date."

---

## D-049 — Journal ordering: entry_date DESC, created_at DESC

**Date:** 2026-06-23 (Phase 6)
**Decision:** `get_all()` and `get_by_ticker()` return entries ordered by `entry_date DESC,
created_at DESC`. Most recent decision date first; for same-date entries, most recently
inserted first.
**Rationale:** Users most often want to see recent decisions first. Secondary sort by
`created_at` gives a deterministic and natural order when multiple entries share a date.

---

## D-050 — created_at uses UTC timestamp

**Date:** 2026-06-23 (Phase 6)
**Decision:** `created_at` is set using `datetime.now(timezone.utc).isoformat()`.
The resulting string includes UTC timezone information (e.g., `+00:00`).
**Rationale:** UTC timestamps are deterministic across local timezone changes, safe for
ordering comparisons across DST transitions, and unambiguous for any future log analysis.

---

## D-051 — Phase 7A implementation boundary

**Date:** 2026-06-23 (Phase 7A)
**Decision:** Phase 7A implements the pure report builder only (`backend/app/reports/`).
Phase 7B (minimal FastAPI routes under `backend/app/api/`) requires separate human approval
before implementation begins. No report delivery, scheduling, push, email, frontend UI, or
manual-run surface is included in Phase 7A.
**Rationale:** Incremental phase gates allow each layer to be audited independently.
The report builder is a pure composition function that can be reviewed in isolation from
any API surface.

---

## D-052 — Report builder input model

**Date:** 2026-06-23 (Phase 7A)
**Decision:** `build_daily_report()` and `build_weekly_report()` accept
already-computed result objects (`PortfolioSnapshot`, `DrawdownResult | None`,
`VolatilityResult | None`, `list[AlertResult]`, `list[JournalEntry]`) as plain function
arguments. The report builder does not access `DataAdapter`, SQLite repositories, CSV
importers, filesystem, network, or the system clock. The caller is responsible for
fetching and pre-filtering all data before invoking the builder.
**Rationale:** Keeping the builder pure and I/O-free makes it trivially testable (no
fixtures), composable with any future orchestration layer, and consistent with the purity
invariant already established for the metrics and alert engines.

---

## D-053 — Report builder output format

**Date:** 2026-06-23 (Phase 7A)
**Decision:** The builder returns frozen dataclasses: `DailyReport` and `WeeklyReport`,
each containing `list[ReportSection]` (system-generated, compliance-checked text blocks)
and `list[JournalEntry]` (user-authored entries carried verbatim, not compliance-scanned).
`ReportSection` holds a `label` and a `body` — both compliance-checked strings.
Rendering, serialisation, and formatting are the caller's responsibility.
**Rationale:** Frozen dataclasses are immutable, safely hashable, and consistent with the
pattern used throughout the project (metrics results, alert results, journal entry).
Separating journal entries from system-generated sections makes the verbatim/not-scanned
boundary unambiguous.

---

## D-054 — Compliance policy for report text

**Date:** 2026-06-23 (Phase 7A)
**Decision:** Every system-generated string placed in a `ReportSection.label` or
`ReportSection.body` must pass `check_compliance()` before the `ReportSection` is
constructed. `ComplianceViolationError` is never caught or rewritten inside the builder —
it propagates to the caller. User-authored `JournalEntry` fields (`action_taken`,
`reasoning`, `hypothesis`, `tags`) are not passed through `check_compliance()` and are
not placed inside any `ReportSection.body`. This is consistent with D-046.
**Rationale:** Compliance is a non-negotiable chokepoint (ARCHITECTURE.md §4).
Hard failure on a violation ensures that non-compliant generated text cannot reach
the user in any form.

---

## D-055 — Alert inclusion policy in reports

**Date:** 2026-06-23 (Phase 7A)
**Decision:** Reports include all evaluated `AlertResult` objects, both fired and
non-fired. The alert summary section shows the status, severity, measured value,
threshold, and explanation for every result passed in.
**Rationale:** Consistent with D-038 (evaluate_alerts returns all results). A non-firing
alert is informative — its absence would be ambiguous. Showing "within threshold" for
non-fired rules gives the user a complete picture of the evaluation.

---

## D-056 — Report date / timestamp policy

**Date:** 2026-06-23 (Phase 7A)
**Decision:** `report_date` (and `week_start` for weekly reports) are caller-provided
ISO-8601 date strings. The report builder does not call `datetime.now()`, `date.today()`,
or any system clock. Both dates are validated with `validate_iso_date()`. For weekly
reports, `week_start` must be on or before `report_date`; violation raises
`InvalidDateError`.
**Rationale:** Consistent with D-031 (valuation date policy). System-clock independence
makes tests deterministic, avoids date-sensitive fragility, and keeps the builder pure.

---

## D-057 — v0.1 closeout boundary

**Date:** 2026-06-23 (Phase 7A)
**Decision:** v0.1 is not complete at the end of Phase 7A. v0.1 is complete only after
Phase 7B (minimal FastAPI routes) is separately approved, implemented, audited, and
accepted. The definition of done for v0.1: all six metrics computed, all four alert rules
evaluated, compliance guard active on all system-generated output, decision journal
operational, daily/weekly report builder complete, minimal read-only API routes functional,
all tests green, architecture invariant green, and all docs updated. Phase 8 is the Tier 3
gate review (paper trading research boundary) — a conscious deliberate decision, not
automatic.
**Rationale:** The API layer is the surface through which the frontend will consume
reports; shipping v0.1 without any API surface would leave the product unusable. Phase 7B
must be completed before v0.1 can be declared done.

---

## D-058 — Phase 7B API boundary

**Date:** 2026-06-23 (Phase 7B)
**Decision:** Phase 7B implements read-only report routes only:
  GET /health, GET /reports/daily, GET /reports/weekly.
No write routes, no execution endpoints, no broker access, no scheduled jobs,
no notifications, no external HTTP calls from application code.
**Rationale:** Consistent with the automation ceiling defined in RISK_POLICY.md §7
(read → compute → notify). All routes are GET-only. The API describes computed facts;
it never prescribes action.

---

## D-059 — FastAPI dependency declaration

**Date:** 2026-06-23 (Phase 7B)
**Decision:** Add `fastapi>=0.100.0` as the only new runtime dependency in Phase 7B.
Add `httpx2` under `[project.optional-dependencies] dev` for TestClient support.
Do not add uvicorn as a project dependency — users install it manually to run the server.
Do not add requests, aiohttp, or any external HTTP client as a runtime dependency.
**Options considered:** `fastapi[standard]` which bundles uvicorn (rejected — keeps
dependencies minimal; uvicorn is a runtime concern, not a test concern).
**Rationale:** D-013 already decided FastAPI as the framework. Phase 7B is the
implementation point. httpx2 is required by starlette 1.2.1+ for TestClient.

---

## D-060 — API date parameters

**Date:** 2026-06-23 (Phase 7B)
**Decision:** `report_date` and `week_start` are required, caller-provided ISO-8601
date strings. No optional date with system-clock fallback. Invalid dates return
HTTP 422 with a structured error body: {error, field, value, message}.
**Rationale:** Consistent with D-056 (report builder date policy) and D-031 (metrics
engine valuation date). System-clock independence makes the API deterministic and testable.

---

## D-061 — API DB path and connection lifecycle

**Date:** 2026-06-23 (Phase 7B)
**Decision:** Use existing D-023 policy: OTOMASYON_DB_PATH env var, default
`./data/otomasyon.db`. One connection opened per request via `deps.get_conn()`.
`init_schema(conn)` called per request (idempotent). Connection closed via try/finally.
No global persistent connection. No connection pool. `check_same_thread=False` set on
all connections to allow sync handlers to run in FastAPI's thread pool.
**Rationale:** Per-request connection keeps the lifecycle simple for a local single-user
tool. `check_same_thread=False` is safe because each connection is owned by exactly one
request at a time; it also makes test injection across threads possible.

---

## D-062 — API orchestration sequence

**Date:** 2026-06-23 (Phase 7B)
**Decision:** Route handlers follow this sequence:
  1. Validate date parameters → HTTP 422 on failure.
  2. Open connection via `deps.get_conn()` (init_schema already called).
  3. `adapter = SQLiteDataAdapter(conn)`.
  4. `holdings = adapter.get_holdings()`.
  5. `prices = adapter.get_prices()`.
  6. `journal_entries = adapter.get_journal_entries(date_from, date_to)`.
  7. `snapshot = compute_portfolio_snapshot(holdings, prices)`.
  8. `drawdown = compute_drawdown(holdings, prices)`.
  9. `volatility = compute_volatility_proxy(holdings, prices)`.
  10. `alert_results = evaluate_alerts(snapshot, drawdown, volatility, AlertConfig())`.
  11. `report = build_daily_report(...)` or `build_weekly_report(...)`.
  12. `return dataclasses.asdict(report)`.
Note: drawdown and volatility are computed for daily routes even though
build_daily_report does not consume them — evaluate_alerts requires them for DD-001/VOL-001.
**Rationale:** Complete alert evaluation is required by D-038 and D-055.

---

## D-063 — API serialization policy

**Date:** 2026-06-23 (Phase 7B)
**Decision:** Use `dataclasses.asdict(report)` to convert frozen report dataclasses
to plain JSON-serializable dicts. No Pydantic response model in v0.1. FastAPI serializes
the returned dict to JSON. Journal text in journal_entries fields is carried verbatim
through asdict() without rewriting or compliance scanning. No new text is injected.
**Rationale:** dataclasses.asdict() handles nested frozen dataclasses recursively.
All field types (str, int, list, None) are JSON-serializable. Consistent with D-053.

---

## D-064 — Alert inclusion in API response

**Date:** 2026-06-23 (Phase 7B)
**Decision:** The API response matches the report builder output exactly. All evaluated
alerts (fired and non-fired) are embedded in the Alert Summary section text. No separate
top-level alerts array is added to the response.
**Rationale:** Consistent with D-055 (alert inclusion in reports) and D-038 (all results
returned). The report builder already formats alert text; the API does not duplicate it.

---

## D-065 — v0.1 completion criteria

**Date:** 2026-06-23 (Phase 7B)
**Decision:** v0.1 is complete only after Phase 7B implementation, acceptance audit,
all tests green, architecture invariant green, and all docs updated with no forbidden
scope introduced. After Phase 7B acceptance: Phase 8 begins with the Tier 3 gate review
(paper trading research boundary) — a conscious, deliberate decision requiring its own
DECISIONS.md entry and explicit human approval before any code is written.
**Rationale:** Consistent with D-057. v0.1 implementation is now done; acceptance audit
determines whether v0.1 is officially closed.

---

## D-066 — DataAdapter journal extension

**Date:** 2026-06-23 (Phase 7B)
**Decision:** DataAdapter ABC gains `get_journal_entries(date_from: str, date_to: str)
-> list[JournalEntry]` as an abstract method. SQLiteDataAdapter implements it by
delegating to `JournalRepo.get_by_date_range(date_from, date_to)`. JournalRepo gains
`get_by_date_range()` which validates both dates and returns entries ordered by
entry_date DESC, created_at DESC. API routes use only `SQLiteDataAdapter` for all data
access — no direct persistence repo imports in route modules.
**Rationale:** Maintains the "all data through adapters" invariant from ARCHITECTURE.md.
Avoids direct persistence repo imports from api/routes/, consistent with the approved
Phase 7B implementation constraints.

---

## D-067 — Phase 8A boundary: Option B approved, Tier 2 only

**Date:** 2026-06-23 (Phase 8A)
**Decision:** Phase 8A implements richer local analytics within Tier 2 only, per Option B
from `docs/PHASE8_GATE_PLAN.md`. The selected narrow scope for Phase 8A is data quality
analytics: per-ticker price history depth (`TickerQuality`), portfolio coverage summary
(`DataQualitySummary`), a "Data Quality Summary" `ReportSection` in daily and weekly
reports, and a top-level `data_quality` key in the API response via `dataclasses.asdict()`.
No Tier 3 (paper trading), Tier 4 (live trading), or any execution-adjacent feature is
included.
**Options considered:** Option A (stay read-only, no change), Option C (Tier 3 research),
Option D (reject/defer).
**Rationale:** Option B extends analytical depth without crossing any safety boundary.
Data quality analytics are the lowest-risk, highest-value improvement available within
the existing architecture: they surface whether computed metrics are well-supported by
local price data, using only data already stored in the local SQLite database.

---

## D-068 — Phase 8A purity constraint: compute_data_quality is a pure function

**Date:** 2026-06-23 (Phase 8A)
**Decision:** `compute_data_quality(holdings, price_records, report_date)` is a pure
function: no I/O, no system clock, no environment variables, no persistence imports, no
network access. All data arrives as function arguments. `report_date` is always
caller-provided (consistent with D-031 and D-056). Enforced by boundary import tests in
`test_data_quality.py` and the architecture invariant.
**Rationale:** Consistency with the purity invariant established for the metrics engine
(D-030). Pure functions are testable without fixtures and composable with any future
orchestration layer.

---

## D-069 — Phase 8A compliance constraint: Data Quality Summary text is checked

**Date:** 2026-06-23 (Phase 8A)
**Decision:** All system-generated strings placed in the "Data Quality Summary"
`ReportSection` label and body pass `check_compliance()` before construction, consistent
with D-054. No compliance guard wordlist extensions are required for data quality language
(coverage counts, date strings, ticker names, day counts). No advisory language is used
or required.
**Rationale:** Consistent with D-039 and D-054. The compliance guard is not bypassed or
narrowed for new features.

---

## D-070 — Phase 8A architecture invariant: extended to cover metrics/quality.py

**Date:** 2026-06-23 (Phase 8A)
**Decision:** `backend/tests/architecture/test_no_broker_no_execution.py` is extended
with three targeted tests for `metrics/quality.py`: no broker imports, no execution
definitions, no advisory language. These run alongside the existing three invariant tests.
**Rationale:** The invariant test grows with the codebase. New modules must be covered
before they are accepted, not after.

---

## D-071 — Phase 8A data quality result format

**Date:** 2026-06-23 (Phase 8A)
**Decision:** Data quality results are two frozen dataclasses in
`backend/app/metrics/quality.py`:
- `TickerQuality`: ticker, price_record_count, earliest_price_date, latest_price_date,
  days_since_last_price (relative to caller-provided report_date; None if no price on or
  before report_date), has_price_on_or_before_report_date.
- `DataQualitySummary`: report_date, total_holding_count, priced_holding_count,
  unpriced_holding_count, coverage_ratio, unpriced_tickers, ticker_quality.
Both are added as `data_quality: DataQualitySummary | None = None` on `DailyReport` and
`WeeklyReport` (optional field with default None for backward compatibility).
**Rationale:** Consistent with the frozen-dataclass result pattern established in Phases
4–7A. Optional field preserves backward compatibility with existing tests and call sites.

---

## D-072 — Phase 8A API: data_quality exposed via dataclasses.asdict()

**Date:** 2026-06-23 (Phase 8A)
**Decision:** `compute_data_quality` is called in the API orchestration sequence (D-062)
immediately after metrics computation. The result is passed to both `build_daily_report`
and `build_weekly_report` and stored on the returned report dataclass. `dataclasses.asdict()`
recursively serialises `DataQualitySummary` and `TickerQuality` to nested dicts, exposing
`data_quality` as a top-level key in the JSON response. All routes remain GET-only.
No persistence repo imports added to route modules. No new abstract method added to
`DataAdapter` — the existing `get_holdings()` and `get_prices()` supply all required data.
**Rationale:** Consistent with D-058, D-062, D-063, and D-066. No write endpoints. No
adapter boundary change required for this scope.

---

## D-073 — Phase 8A dependencies: no new runtime dependencies

**Date:** 2026-06-23 (Phase 8A)
**Decision:** Phase 8A introduces no new runtime dependencies. `pyproject.toml`
`dependencies` remains `["fastapi>=0.100.0"]`. All new computation uses Python stdlib
only (`datetime`, `dataclasses`). No third-party library is required.
**Rationale:** Consistent with D-024 (stdlib-only policy) and the zero-additional-
dependency posture maintained through Phases 2–7B.

---

## D-074 — Phase 8A test gate: 585 tests passed, 0 skipped

**Date:** 2026-06-23 (Phase 8A)
**Decision:** Phase 8A implementation is accepted when `python -m pytest backend/tests/`
returns 585 passed, 0 skipped. The 85 new tests cover: `compute_data_quality` pure
function (unit), report builder integration (unit), API response shape and content
(integration), route boundary (no repo imports, no raw SQL), purity (no system clock),
compliance (no forbidden language in generated text), and architecture invariant extension.
**Rationale:** Consistent with the per-phase test gate established across Phases 2–7B.
Each new module and integration path must have dedicated tests before acceptance.

---

## D-075 — Phase 8B boundary: Report Explainability + Hardening, Tier 2 only

**Date:** 2026-06-23 (Phase 8B)
**Decision:** Phase 8B implements report explainability improvements and architecture/test
hardening only, within Tier 2. Specifically: a "Metric Definitions" `ReportSection`
describing M-001 through M-006 in fact-stating language; an "Alert Rule Definitions"
`ReportSection` describing CONC-001, DD-001, VOL-001, and COV-001 threshold conditions;
a conditional "Data Quality Caveat" `ReportSection` added when `unpriced_holding_count > 0`
explaining which computed facts are affected by incomplete local price data; and companion
architecture hardening tests (broader forbidden-import scan, compliance regression tests,
conditional behavior tests, route boundary tests, builder purity tests).
**Options considered:** Candidate B (API contract clarity — deferred), Candidate C-gap
(gap detection — deferred to Phase 8C), Candidate D hardening only — adopted as companion.
**Rationale:** Candidate A is the lowest-risk, highest-clarity improvement within the
existing architecture. Pure builder extension; no new API routes, no schema changes, no
new repositories, no new runtime dependencies.

---

## D-076 — Phase 8B purity constraint: new section builders are pure functions

**Date:** 2026-06-23 (Phase 8B)
**Decision:** All new functions added to `backend/app/reports/builder.py` in Phase 8B
(`_metric_definitions_section`, `_alert_rule_definitions_section`,
`_data_quality_caveat_section`) satisfy the same purity invariant as existing section
builders: no I/O, no system clock, no environment variables, no persistence imports,
no network access. Data arrives as function arguments. `report_date` is always
caller-provided (consistent with D-031 and D-056).
**Rationale:** Consistent with D-030, D-052, and D-068.

---

## D-077 — Phase 8B compliance constraint: all new section text passes check_compliance()

**Date:** 2026-06-23 (Phase 8B)
**Decision:** All strings placed in new Phase 8B `ReportSection` labels and bodies pass
`check_compliance()` through `_make_section()` before `ReportSection` construction,
consistent with D-054. No new compliance guard wordlist extensions were required for
metric definition or alert rule description language. `ComplianceViolationError` is not
caught or suppressed in any new builder function.
**Rationale:** Consistent with D-039 and D-054. Compliance is a non-optional chokepoint.

---

## D-078 — Phase 8B architecture invariant: broader forbidden-import scan added

**Date:** 2026-06-23 (Phase 8B)
**Decision:** `backend/tests/architecture/test_no_broker_no_execution.py` is extended
with two new invariant tests: `test_no_system_shell_or_socket_in_app` (no `os.system()`,
`subprocess`, or raw `socket` usage in `backend/app/`) and
`test_no_external_http_client_imports_in_app` (no `requests`, `httpx`, `aiohttp`, or
`urllib.request` imports in `backend/app/`). These run alongside the existing eight tests.
**Rationale:** Consistent with D-070. The invariant test grows with the codebase.
Phase 8B adds no new modules but the broader scan future-proofs the boundary.

---

## D-079 — Phase 8B report section placement policy

**Date:** 2026-06-23 (Phase 8B)
**Decision:** The final section ordering in daily and weekly reports is:
  Daily: Report → Data Coverage → [Data Quality Summary] → [Data Quality Caveat] →
    Metric Definitions → Alert Rule Definitions → Portfolio Snapshot → Position Weights →
    Alert Summary → Journal Entries → Method Note → Disclaimer.
  Weekly: Report → Week Range → Data Coverage → [Data Quality Summary] →
    [Data Quality Caveat] → Metric Definitions → Alert Rule Definitions →
    Portfolio Snapshot → Drawdown Summary → Volatility Proxy Summary → Position Weights →
    Alert Summary → Journal Entries → Method Note → Disclaimer.
  Sections in brackets are conditional. Metric Definitions and Alert Rule Definitions
  are unconditional — always present.
**Rationale:** Explainability sections placed before data sections so the user reads
definitions before computed values. Conditional caveat placed immediately after the
Data Quality Summary it contextualises. Placement determined by builder; not
configurable by callers.

---

## D-080 — Phase 8B test gate: 647 tests passed, 0 skipped

**Date:** 2026-06-23 (Phase 8B)
**Decision:** Phase 8B implementation is complete when `python -m pytest backend/tests/`
returns 647 passed, 0 skipped. The 62 new tests cover: Metric Definitions section
presence, label, body, and compliance (daily and weekly); Alert Rule Definitions section
presence, label, body, and compliance (daily and weekly); Data Quality Caveat conditional
behavior (present/absent/compliance); section ordering invariants; parametrised compliance
regression tests for all sections across data quality scenarios; API integration tests for
new sections in both routes; route purity (no new write routes, no system clock in
builder); and two new architecture invariant tests. Architecture invariant total: 8 tests
(3 original + 3 Phase 8A + 2 Phase 8B).
**Rationale:** Consistent with the per-phase test gate established across Phases 2–8A.

---

## D-081 — Phase 8C boundary: Local Price Gap Diagnostics + Repository Hardening, Tier 2 only

**Date:** 2026-06-23 (Phase 8C)
**Decision:** Phase 8C implements local price-date gap diagnostics and repository/architecture
hardening only, within Tier 2. Specifically: a pure helper `_compute_largest_gap` and four
new fields on `TickerQuality` (`local_price_date_count_on_or_before_report_date`,
`largest_price_date_gap_days`, `largest_price_date_gap_start`, `largest_price_date_gap_end`);
updated "Data Quality Summary" `ReportSection` text including per-ticker gap facts and a
general gap methodology note; API response enriched via the existing `data_quality.ticker_quality`
serialization path; and companion hardening tests (adapter boundary, route purity, quality
module layer isolation, system-clock purity). No new API routes, no new persistence tables,
no new adapter abstract methods, no new runtime dependencies.
**Options considered:** Candidate B (CSV import diagnostics — deferred), Candidate C
(API contract documentation — deferred to frontend build phase), Candidate D hardening
only — adopted as companion.
**Rationale:** Candidate A is the natural continuation of Phase 8A data quality analytics,
was explicitly deferred to Phase 8C in Phase 8B planning, and requires only a pure
function extension within the existing metrics module. Lowest boundary risk of all
candidates. Highest diagnostic value relative to scope.

---

## D-082 — Phase 8C purity constraint: gap computation is a pure function

**Date:** 2026-06-23 (Phase 8C)
**Decision:** All new functions added in Phase 8C for gap computation (`_compute_largest_gap`,
and the extended `compute_data_quality`) satisfy the same purity invariant as the existing
analytics functions (D-030, D-068): no I/O, no system clock, no environment variables,
no persistence imports, no network access. All data arrives as function arguments already
fetched by the caller. `report_date` is always caller-provided, consistent with D-031
and D-056. Duplicate price dates are collapsed before gap computation to prevent false
zero-day gaps.
**Rationale:** Consistent with the purity invariant maintained across Phases 4–8B.
Pure functions are testable without fixtures and composable with any future orchestration.

---

## D-083 — Phase 8C compliance constraint: gap text passes check_compliance()

**Date:** 2026-06-23 (Phase 8C)
**Decision:** All system-generated strings describing gap facts placed in the "Data Quality
Summary" `ReportSection` body pass `check_compliance()` through `_make_section()` before
`ReportSection` construction, consistent with D-054 and D-077. No compliance guard
wordlist extensions are required for gap description language (calendar day counts, ISO
date strings, ticker names). Gap text is factual and descriptive only: it states the
observed gap size and dates, not significance or implication. No advisory language is
used or required. Wording uses "local price-date gap" and "calendar day(s)" consistently
and does not reference exchange calendars, trading sessions, or market days.
**Rationale:** Consistent with D-039, D-054, D-069, and D-077. Compliance is a
non-optional chokepoint for all system-generated text.

---

## D-084 — Phase 8C data model: TickerQuality extension

**Date:** 2026-06-23 (Phase 8C)
**Decision:** `TickerQuality` frozen dataclass in `backend/app/metrics/quality.py` gains
four new fields appended after the existing six:
  `local_price_date_count_on_or_before_report_date: int` — count of unique local price
    dates on or before report_date (duplicates collapsed).
  `largest_price_date_gap_days: int | None` — calendar days of the largest consecutive
    gap between unique local price dates on or before report_date.
  `largest_price_date_gap_start: str | None` — ISO-8601 date string for the start of
    the largest gap.
  `largest_price_date_gap_end: str | None` — ISO-8601 date string for the end of the
    largest gap.
All three gap fields are None when fewer than two unique local price dates exist on or
before report_date. Tie behavior: when multiple consecutive gaps share the same length,
the earliest (first in ascending date order) is reported. The existing `data_quality`
API key surfaces the new fields automatically via `dataclasses.asdict()`. No new top-level
API key is added. No new API routes.
**Rationale:** Consistent with D-071 (data quality result format). Additive field
additions to frozen dataclasses are backward-compatible with existing tests and call sites
that use `compute_data_quality()` rather than direct `TickerQuality(...)` construction.
`dataclasses.asdict()` recurses into nested frozen dataclasses without route-layer changes
(D-072).

---

## D-085 — Phase 8C architecture invariant: extended for Phase 8C modules

**Date:** 2026-06-23 (Phase 8C)
**Decision:** `backend/tests/architecture/test_no_broker_no_execution.py` is extended
with four new invariant tests:
  `test_no_raw_sql_in_api_routes` — no raw SQL statements in `api/routes/`.
  `test_no_direct_repo_imports_in_api_routes` — no direct `app.data.persistence.*`
    imports in `api/routes/`.
  `test_quality_module_has_no_layer_imports` — `metrics/quality.py` imports nothing
    from `app.data.persistence`, `app.api`, `app.reports`, `app.alerts`, or
    `app.compliance`.
  `test_quality_module_has_no_system_clock` — belt-and-suspenders purity check that
    `.now(`, `.today(`, and `time.time(` do not appear in `metrics/quality.py`.
Architecture invariant total: 12 tests (3 original + 3 Phase 8A + 2 Phase 8B + 4 Phase 8C).
**Rationale:** Consistent with D-070 and D-078. The invariant test grows with the codebase.
New functions and integration paths must be covered before acceptance.

---

## D-086 — Phase 8C test gate: 701 tests passed, 0 skipped

**Date:** 2026-06-23 (Phase 8C)
**Decision:** Phase 8C implementation is accepted when `python -m pytest backend/tests/`
returns 701 passed, 0 skipped. The 54 new tests cover: gap fields None for no records;
gap fields None for single local date; gap fields None for only-future dates; two-date
gap computation (days, start, end); multiple gaps — largest selected; tie behavior —
earliest gap returned; duplicate dates — collapsed, no false gap; future dates — excluded
from gap and local count; non-held tickers — ignored; frozen dataclass with new fields;
daily report Data Quality Summary includes gap text, calendar-day language,
local-price-date-gap phrase, gap methodology note, no-exchange-session note, no gap
phrase for single-date ticker; section body and label pass compliance; no market-session
language; weekly report includes gap info; local price date count in section body;
daily and weekly API responses include all four Phase 8C fields in ticker_quality;
gap field values correct; gap null for single price date; no new API routes or write
routes; gap text passes compliance in API response; architecture invariant extended
(four new tests); route raw-SQL check; route direct-repo-import check; quality module
layer isolation; quality module system-clock purity.
**Rationale:** Consistent with the per-phase test gate established across Phases 2–8B.
Each new module, integration path, and boundary extension must have dedicated tests
before acceptance.

---

## D-087 — Phase 8D boundary: API Contract Documentation + API Error Taxonomy, Tier 2 only

**Date:** 2026-06-23 (Phase 8D)
**Decision:** Phase 8D implements API contract documentation only, within Tier 2.
Specifically: `docs/API_CONTRACT.md` documenting the JSON response shape for
`GET /health`, `GET /reports/daily`, and `GET /reports/weekly`, including all Phase 7B
base fields, all Phase 8A `data_quality` and `ticker_quality` fields, all Phase 8C
gap diagnostic fields, and an API error taxonomy covering all current HTTP 422 failure
modes per route. Example JSON payloads for four representative scenarios are included.
No new API routes. No application code changed. No new dependencies. No optional
contract tests in Phase 8D (deferred; see D-090).
**Options considered:** Candidate B (CSV import diagnostics — deferred), Candidate C
(local data flow documentation — deferred as follow-on after D-087 is accepted),
Candidate D (API error taxonomy — adopted as documentation companion within this same
artefact rather than a separate phase).
**Rationale:** Candidate A was explicitly deferred from both Phase 8B and Phase 8C
pending response shape stabilisation. Phase 8C acceptance closes that deferral: all
planned Phase 8 analytical fields are now accepted and the response shape is stable.
Documenting the shape now locks it in before any future phase adds more fields.
Documentation-only variant has zero implementation risk. Candidate D's error taxonomy
is bundled into the same artefact as planned in the Phase 8D candidate planning document.

---

## D-088 — Phase 8D documentation scope: all Phase 7B–8C response fields covered

**Date:** 2026-06-23 (Phase 8D)
**Decision:** `docs/API_CONTRACT.md` covers all three routes. For the report routes
it documents all top-level keys (`report_date`, `report_type`, `sections`,
`journal_entries`, `data_quality`; plus `week_start` for the weekly route); all
`DataQualitySummary` fields; all `TickerQuality` fields including all four Phase 8C gap
fields (`local_price_date_count_on_or_before_report_date`, `largest_price_date_gap_days`,
`largest_price_date_gap_start`, `largest_price_date_gap_end`); `ReportSection` fields
(`label`, `body`); and all `JournalEntry` fields. Each field entry states its key name,
JSON type, nullable status, and the phase that introduced it. The document does not
describe planned or future fields.
**Rationale:** Complete field coverage makes the document authoritative for any future
consumer. Partial coverage would require revision whenever an undocumented field is
encountered. Scoping strictly to accepted fields keeps the document accurate.

---

## D-089 — Phase 8D example payloads: four representative scenarios

**Date:** 2026-06-23 (Phase 8D)
**Decision:** `docs/API_CONTRACT.md` includes four representative JSON response examples:
Scenario A — `GET /health` success; Scenario B — daily report with complete price support
and no "Data Quality Caveat" section; Scenario C — daily report with incomplete price
support, "Data Quality Caveat" present, and gap fields populated (including a `null`-gap
ticker with zero price records); Scenario D — weekly report with one journal entry,
`data_quality` present, and gap fields populated. All examples use neutral ticker names
(`"AAAA"`, `"BBBB"`). No advisory, directional, or trading language is used. Journal
entry text in Scenario D is explicitly marked as sample text; user-authored content is
not rewritten or compliance-scanned.
**Rationale:** Concrete examples make abstract field descriptions unambiguous. The four
scenarios cover the conditional branches in the system (priced/unpriced, alert
fired/not-fired, journal present/absent) so a consumer can reason about which fields are
always present and which are conditional.

---

## D-090 — Phase 8D optional contract tests: deferred from Phase 8D

**Date:** 2026-06-23 (Phase 8D)
**Decision:** The optional structural integration tests described in
`docs/PHASE8D_CANDIDATE_PLAN.md` §3 (Candidate A, optional API contract tests) and
proposed in Phase 8D planning are **deferred** from Phase 8D implementation. Phase 8D
is documentation-only. The optional test set (parametrised assertions for top-level key
presence, `ticker_quality` gap fields, and error status codes / body structure) may be
adopted in a future phase when a consumer is actively being built against the documented
contract. The decision to defer does not remove the option; it requires a separate
explicit approval at that time.
**Rationale:** The implementation instructions for Phase 8D state "Do not add tests
unless strictly needed for documentation consistency." The documentation artefact is
self-contained and accurate without accompanying contract tests. Deferring keeps Phase
8D scope minimal and eliminates any risk of introducing test infrastructure changes
without a dedicated review.

---

## D-091 — Phase 8D architecture invariant: unchanged

**Date:** 2026-06-23 (Phase 8D)
**Decision:** Phase 8D introduces no new application modules and no new inter-layer
dependencies. The architecture invariant test count remains at 12 (3 original + 3
Phase 8A + 2 Phase 8B + 4 Phase 8C). No new invariant tests are added in Phase 8D.
No test files are created or modified.
**Rationale:** Phase 8D adds only documentation. No new import patterns or module-level
rules are introduced. Extending the invariant count without a corresponding new rule
would create false coverage. Consistent with D-091 as proposed in
`docs/PHASE8D_CANDIDATE_PLAN.md`.

---

## D-092 — Phase 8D test gate: 701 tests passed, 0 skipped (unchanged)

**Date:** 2026-06-23 (Phase 8D)
**Decision:** Phase 8D implementation is accepted when `python -m pytest backend/tests/`
returns 701 passed, 0 skipped — the same count as Phase 8C. No new tests are added in
Phase 8D (D-090 deferred; D-091 unchanged). The test count is unchanged because the
entire Phase 8D scope is a documentation artefact. Architecture invariant total remains
at 12 tests.
**Rationale:** Consistent with the per-phase test gate established across Phases 2–8C.
A documentation-only phase with no application code changes requires no new tests and
must not reduce the existing test count.
