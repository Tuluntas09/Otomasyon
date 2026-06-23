# PHASE8C_CANDIDATE_PLAN.md

> **This is a planning document only.**
> It does not approve Phase 8C implementation. No application code may be written,
> no dependencies added, and no modules changed until a separate, explicit human
> approval is recorded in `DECISIONS.md`.
>
> This document records candidate options for Phase 8C within Option B / Tier 2 and
> recommends a narrow implementation scope for human review.

---

## 1. Purpose

Phase 8C is the candidate-selection planning step that follows Phase 8B acceptance.

It evaluates possible next improvements within **Option B — richer local analytics,
Tier 2 only**. It does not constitute implementation approval.

Phase 8C requires all of the following before any code is written:

1. Human review and explicit approval of the selected candidate.
2. Proposed decisions (§6) directed to be appended to `DECISIONS.md` with dates filled in.
3. An explicit implementation prompt issued by the human owner.

Otomasyon remains a local-first personal finance research and decision-support instrument.
Phase 8C does not change that identity. The automation ceiling is unchanged:
**read → compute → notify**. Nothing acts on a market.

---

## 2. Current Baseline

The following capabilities are accepted as of commit `8681ce2`:

| Capability | Module / Layer | Status |
|---|---|---|
| CSV ingestion | `backend/app/data/adapters/csv_importer.py` | ✅ accepted (Phase 3) |
| SQLite persistence | `backend/app/data/persistence/` | ✅ accepted (Phase 2) |
| Metrics engine | `backend/app/metrics/engine.py` | ✅ accepted (Phase 4) |
| Alert rules | `backend/app/alerts/rules.py` | ✅ accepted (Phase 5) |
| Compliance guard | `backend/app/compliance/guard.py` | ✅ accepted (Phase 5) |
| Decision journal | `backend/app/journal/` | ✅ accepted (Phase 6) |
| Report builder | `backend/app/reports/builder.py` | ✅ accepted (Phase 7A) |
| Read-only API | `backend/app/api/routes/reports.py` | ✅ accepted (Phase 7B) |
| Data quality analytics | `backend/app/metrics/quality.py` | ✅ accepted (Phase 8A) |
| Report explainability | `backend/app/reports/builder.py` (extended) | ✅ accepted (Phase 8B) |
| Architecture hardening | `backend/tests/architecture/` (extended) | ✅ accepted (Phase 8B) |

**Test baseline:** 647 passed, 0 skipped.
**Runtime dependencies:** `fastapi>=0.100.0` only.
**Dev dependencies:** `httpx2` only.

### What Phase 8B added

Phase 8B extended `build_daily_report()` and `build_weekly_report()` in
`backend/app/reports/builder.py` with three new system-generated `ReportSection` types:

- **Metric Definitions** — fact-stating descriptions of M-001 through M-006, always present.
- **Alert Rule Definitions** — threshold comparisons for CONC-001, DD-001, VOL-001, and
  COV-001, always present.
- **Data Quality Caveat** — conditional section explaining which time-series metrics
  (M-005, M-006) are affected when `unpriced_holding_count > 0`.

Phase 8B also extended the architecture invariant with two new forbidden-import scans
(`test_no_system_shell_or_socket_in_app`, `test_no_external_http_client_imports_in_app`).

No new API routes, no new persistence tables, no new adapter methods, and no new runtime
dependencies were introduced.

### Items deferred from Phase 8B to Phase 8C

The following were evaluated in `docs/PHASE8B_CANDIDATE_PLAN.md` and explicitly deferred:

- **Price gap detection** (Candidate C-gap in Phase 8B) — extend `compute_data_quality`
  or a companion function to surface the largest consecutive-date gap per ticker.
- **Import error history** (Candidate C-import in Phase 8B) — persist row-level import
  errors to a queryable table; deferred due to new schema surface area.
- **API contract documentation** (Candidate B in Phase 8B) — schema document and example
  JSON payloads; deferred until a frontend consumer is being built.

---

## 3. Candidate Options

Four candidates are evaluated below. All are within Tier 2 (read → compute → notify).
None crosses into paper trading, execution, external data, or advisory output.

---

### Candidate A — Local Price Gap Diagnostics

#### Description

Extend the data quality analytics layer to detect and surface missing local price dates
per held ticker. Specifically:

- For each ticker with at least two price records in the local SQLite database, compute
  the consecutive date gaps: for every pair of chronologically adjacent price records, the
  gap in calendar days between them.
- Identify the **largest gap** (in calendar days) for each ticker and the start/end dates
  that bound it.
- Expose this per-ticker gap information either:
  - (a) as new fields on `TickerQuality` (`largest_gap_days: int | None`,
    `largest_gap_start: str | None`, `largest_gap_end: str | None`), surfaced
    through the existing `DataQualitySummary` and the existing `data_quality` API key; or
  - (b) as a standalone pure function `compute_price_gaps(holdings, price_records)` that
    returns a `list[PriceGapResult]`, callable separately from `compute_data_quality`.
- No external data fetched. No comparison against exchange calendars. No assessment of
  whether a gap is "expected" or "unexpected". Pure factual reporting: gap exists, these
  dates, this size.

Variant (a) is the minimal path: it adds nullable fields to `TickerQuality` with no
schema changes and no new API routes. Variant (b) is a slightly larger surface but
provides a composable building block for future diagnostic views without coupling gap
logic into `DataQualitySummary`.

All text generated for any new `ReportSection` is compliance-checked through
`_make_section()`, consistent with D-054 and D-077.

#### Expected value

- Directly complements Phase 8A data quality output. Phase 8A reports how many price
  records exist per ticker; Candidate A reveals **where** the data is missing.
- M-005 (drawdown) and M-006 (volatility proxy) are time-series metrics: a large gap
  in local price data between two dates means those periods are missing from the
  computation. Surface the gap so the user can assess whether the metric result is
  well-supported.
- Zero external dependencies. All computation uses `datetime.date` arithmetic on data
  already stored in the local SQLite database.
- Pure function extension: identical pattern to `compute_data_quality` in
  `backend/app/metrics/quality.py`.

#### Implementation risk

**Low.** Candidate A is a pure function extension within `backend/app/metrics/`. All
required data (`holdings`, `price_records`) is already fetched by the API orchestration
sequence (D-062). No new I/O, no new persistence methods, no new abstract methods on
`DataAdapter`, no new API routes, no schema changes. The only surface area is the new
function(s) and optional new fields on `TickerQuality`.

The gap computation itself is a simple sort-and-compare over a list of date strings
(`PriceRecord.date`). No numeric library or calendar dependency is needed.

#### Compliance risk

**Low.** Gap descriptions use purely factual language: day counts, date strings, ticker
names. No forbidden terms are required. Example: "Largest gap: 14 days (2024-03-01 to
2024-03-15)." The compliance guard will catch any inadvertent forbidden term before it
reaches a `ReportSection`.

#### Boundary risk

**Very low.** Pure function addition within `backend/app/metrics/`. No new imports outside
`datetime` and `dataclasses`. If variant (a) is chosen, `TickerQuality` gains nullable
fields — no downstream persistence or API changes required, as `dataclasses.asdict()`
recursively serialises all fields automatically. No new adapter methods. No new routes.

#### Recommendation

**Recommended as the primary Phase 8C candidate.**

Candidate A is the lowest-risk, highest-diagnostic-value improvement available. It was
explicitly deferred from Phase 8B in `docs/PHASE8B_CANDIDATE_PLAN.md` (§3, Candidate C-gap
and §4, "Gap detection is recommended as an addition to Candidate A [Phase 8B] [but is]
better bundled with a larger analytical extension"). Phase 8B is now accepted; deferred
items are eligible.

The narrow implementation path (variant a — new nullable fields on `TickerQuality`) adds
useful gap information to existing data quality output without adding any new module,
route, or persistence surface.

---

### Candidate B — CSV Import Diagnostics

#### Description

Improve the visibility of import errors, skipped rows, and validation summaries that occur
during CSV price ingestion via `backend/app/data/adapters/csv_importer.py`. Possible
variants:

- **Summary-only (no new persistence):** Expose `ImportResult.errors` and related row-level
  failure counts in a richer structured form — for example, a `CsvImportSummary` dataclass
  returned from the importer that includes `rows_processed`, `rows_accepted`,
  `rows_rejected`, `error_messages: list[str]`. The importer already returns an
  `ImportResult`; this variant structures it more explicitly. No new persistence table.
  No new API route. The summary is available to any caller that invokes the importer.

- **Persisted error history (requires separate approval):** Persist row-level
  `ImportResult.errors` to a new `import_errors` table in SQLite, queryable via a new
  read-only route (`GET /import-errors?since=YYYY-MM-DD`). This variant requires a new
  schema table, a new persistence repository, a new abstract method on `DataAdapter`, and
  a new API route. Evaluated here but not recommended without separate approval.

#### Expected value

- The summary-only variant makes CSV import errors visible to the caller without requiring
  log inspection or re-running the import.
- Import validation is already implemented; this candidate makes the existing output
  easier to consume and verify.
- The persisted-history variant makes past import failures queryable without re-running
  the import — useful when a user ingests multiple price files over time and wants to
  audit which rows were previously rejected.

#### Implementation risk

**Low** for the summary-only variant. `ImportResult` already carries `errors`; the change
is structural (new dataclass fields, no new logic). No persistence, no new routes.

**Medium** for the persisted-history variant. A new SQLite table, a new `ImportRepo`, a
new abstract method on `DataAdapter`, and a new route each represent additional surface
area. The phase boundary widens more than any other candidate.

#### Compliance risk

**Low.** Import error messages are derived from CSV row validation failures — user-supplied
data, not system-generated advisory text. Error strings are stored verbatim and do not
pass through `check_compliance()` (consistent with D-046 — user-authored content is not
scanned). No advisory language is generated by this candidate.

#### Boundary risk

**Low** for the summary-only variant — structural change to an existing return type,
no new persistence or API surface.

**Medium** for the persisted-history variant — new table, new repo, new adapter method,
and new route each represent a boundary extension requiring architecture invariant coverage.

#### Recommendation

**Deferred.** The summary-only variant is low-risk but provides lower diagnostic value
than Candidate A: import errors are already visible to the caller today; this candidate
improves ergonomics rather than adding new analytical capability.

The persisted-history variant is useful but carries boundary risk disproportionate to the
value it adds within Phase 8C. It should be proposed as a standalone gate item after the
simpler diagnostic features are established.

Neither variant is recommended as the primary Phase 8C scope. Either could be bundled with
Candidate A if the human owner chooses to extend Phase 8C scope.

---

### Candidate C — API Contract Documentation

#### Description

Produce documentation artefacts that formally specify the JSON response shape for
`GET /reports/daily` and `GET /reports/weekly`:

- **Schema document:** A Markdown or JSON Schema file under `docs/` describing every
  top-level key in the response, its type, and whether it may be `null`. Includes the
  `data_quality` key added in Phase 8A and the Phase 8B report sections.
- **Example JSON payloads:** Illustrative responses for representative scenarios:
  (1) zero holdings; (2) all holdings priced, no alerts fired; (3) one or more holdings
  unpriced (triggering the Data Quality Caveat section); (4) one or more alerts fired.
- **Optional API contract tests:** Parametrised integration tests asserting required key
  presence, types, and structural invariants on the route responses. These follow the
  existing pattern in `backend/tests/integration/test_api_reports.py` and require no new
  infrastructure.

No new routes are added. No application code is changed for the documentation-only variant.

#### Expected value

- Makes the API response consumable without inspecting source code. Any future frontend,
  script, or analysis tool can be written against a stable, documented shape.
- API contract tests would catch structural regressions (renamed or removed fields) before
  they escape to callers.
- Pure documentation and optional test work: zero application code changes for the
  documentation-only variant.

#### Implementation risk

**Very low** for the documentation-only variant — no code changes.
**Low** for the test-only variant — follows existing integration test patterns exactly.

#### Compliance risk

**None.** Documentation artefacts and test assertions contain no system-generated
user-facing text. The compliance guard is not relevant to schema documents or test
assertion strings.

#### Boundary risk

**None** for the documentation-only variant.
**Very low** for added contract tests — tests run inside the existing
`backend/tests/` harness against an in-memory database.

#### Recommendation

**Deferred as a standalone Phase 8C candidate.** Candidate C is essentially zero-risk and
adds genuine value for future consumers, but it does not extend Otomasyon's analytical
capability and does not justify a full phase gate on its own.

The optional contract test component could be bundled as a companion to Candidate A
(similar to how Phase 8B bundled Candidate D hardening tests as a companion to Candidate A).
As a standalone phase it is better deferred until a frontend consumer is actively being
built.

---

### Candidate D — Repository/Architecture Hardening

#### Description

Strengthen the adapter/repository boundary tests and add documentation for data flow and
layer ownership, without adding any product features:

- **Adapter boundary tests:** Parametrised tests asserting that `SQLiteDataAdapter`
  methods (`get_holdings`, `get_prices`, `get_journal_entries`) are the only entry points
  through which route handlers access data. Explicit tests verifying that no route module
  imports directly from `backend/app/data/persistence/` (already partially covered by
  existing boundary tests; this extends to all persistence modules, not only broker imports).
- **Repository contract tests:** Tests asserting that each persistence repository
  (`HoldingsRepo`, `PricesRepo`, `JournalRepo`) satisfies its implicit contract under
  boundary conditions: empty tables, single-row tables, maximum-boundary date strings.
- **Data flow documentation:** A short prose section added to `docs/ARCHITECTURE.md`
  documenting the canonical data flow through the system (CSV → SQLite → DataAdapter →
  metrics/reports/alerts → API → caller), the layer ownership policy (which layer may
  call which), and which invariants are enforced by architecture tests.
- **Layer ownership annotation:** Inline docstrings (one line each) on each adapter
  abstract method in `DataAdapter` naming the layer contract. No multi-paragraph comment
  blocks.

No product feature changes. No new routes. No new persistence tables.

#### Expected value

- Adapter boundary tests make it harder for future phases to accidentally bypass the
  adapter abstraction and import directly from persistence repositories.
- Repository contract tests reduce the risk that a future schema migration silently
  changes behavior on boundary inputs.
- Architecture documentation reduces onboarding friction and makes layer ownership
  explicit for future contributors or reviewers.

#### Implementation risk

**Very low.** All test work is inside `backend/tests/`. Documentation changes are in
`docs/ARCHITECTURE.md`. No application code changes. No new runtime dependencies.

#### Compliance risk

**None.** Test assertions and architecture documentation are not user-facing text.

#### Boundary risk

**None.** Test files are excluded from the architecture invariant scan. Documentation
changes do not affect runtime behavior.

#### Recommendation

**Recommended as a companion to Candidate A, not as a standalone Phase 8C candidate.**

The adapter boundary and repository contract tests directly protect the architectural
boundary that Candidate A extends (gap computation accesses the same adapter methods
as Phase 8A). Adding them alongside Candidate A ensures the new gap diagnostic function
arrives with full boundary coverage.

The data flow documentation component is always-valuable but insufficient as a standalone
phase gate.

---

## 4. Recommended Phase 8C Direction

**Recommended: Candidate A — Local Price Gap Diagnostics**
with **Candidate D — Repository/Architecture Hardening** as a companion.

### Narrow scope

1. **Price gap computation function** — a pure function
   `compute_price_gaps(holdings, price_records)` in `backend/app/metrics/quality.py`
   (or as a companion function in the same module) that, for each ticker with at least two
   price records, computes consecutive date gaps, identifies the largest gap, and returns
   a list of `PriceGapResult` frozen dataclasses
   (`ticker`, `largest_gap_days`, `largest_gap_start`, `largest_gap_end`).
   If a ticker has zero or one price record, the result is returned with `largest_gap_days`
   of 0 (or `None`) and no gap dates.

2. **TickerQuality extension** (variant a) — add three nullable fields to `TickerQuality`:
   `largest_gap_days: int | None`, `largest_gap_start: str | None`,
   `largest_gap_end: str | None`. Populated by the updated `compute_data_quality` function
   from the gap computation results. Surfaced automatically through the existing
   `data_quality` key in the API response via `dataclasses.asdict()`. No new API routes.
   No schema changes. No new adapter methods.

3. **Data Quality Caveat extension** (optional) — if `largest_gap_days` for any held ticker
   exceeds a caller-configurable threshold (or a conservative default, e.g., 7 days), add
   a gap-specific fact to the "Data Quality Caveat" `ReportSection` body:
   e.g., "AAPL: largest price gap is 14 days (2024-03-01 to 2024-03-15)." All text
   compliance-checked. No advisory or predictive language.

4. **Companion hardening tests** — adapter boundary tests asserting that no route module
   imports directly from `backend/app/data/persistence/`; repository contract tests for
   boundary conditions on `HoldingsRepo`, `PricesRepo`, and `JournalRepo`; architecture
   invariant count confirmed stable.

### Rationale

- Natural continuation of Phase 8A analytics: Phase 8A surfaces how many price records
  exist; Candidate A surfaces where they are missing.
- Explicitly deferred to Phase 8C in `docs/PHASE8B_CANDIDATE_PLAN.md` (§3 and §4).
- Pure function extension within an existing module: identical pattern to `compute_data_quality`.
- No new API routes, no new persistence tables, no new adapter abstract methods, no new
  runtime dependencies.
- Companion hardening tests protect the boundary extended by the new gap computation.
- All gap description text is factual and passes compliance checking without wordlist changes.

### What this does NOT include

API contract documentation (Candidate C) is deferred to when a frontend consumer is
being built. CSV import diagnostics with persistence (Candidate B-persisted) are deferred
as a separate gate item. No new write routes. No new schema tables. No external data.

---

## 5. Explicit Out-of-Scope List

The following are explicitly excluded from Phase 8C and from Option B generally.
They may not be introduced without a new gate review and explicit human approval.

| Category | Excluded items |
|---|---|
| Simulation | Paper trading, simulated orders, fill simulation, position open/close lifecycle |
| Execution | Broker abstraction, trading credentials, order placement (real or simulated) |
| Signals | Buy/sell recommendations, target prices, opportunity identification, trading signals |
| Indicators | Moving averages, RSI, MACD, Bollinger bands, any technical indicator |
| Backtesting | Historical strategy evaluation, strategy performance metrics, P&L reconstruction |
| External data | Market data APIs, web scraping, news feeds, earnings calendars, external HTTP calls |
| Automation | Scheduler, cron trigger, push notifications, email, webhooks |
| Scope expansion | Multi-currency aggregation, multi-portfolio (each requires its own gate) |
| Frontend | React/Vite UI development (deferred; the empty shell remains unchanged) |
| Advisory output | Any system-generated text implying action, recommendation, or predicted outcome |
| Authentication | User accounts, session management, access control |
| New write routes | No POST, PUT, PATCH, or DELETE API routes of any kind |

In addition, the following specific items are out-of-scope for Phase 8C even though they
are within Tier 2:

- Exchange calendar comparison or "expected trading day" gap assessment — purely local
  date arithmetic only; no external calendar data is consulted.
- Gap severity scoring or classification — reporting the gap size is factual; labeling a
  gap as "significant" or "material" would be advisory language.
- Automatic import error persistence — CSV import diagnostics without separate approval
  of the new persistence table and route.
- New abstract methods on `DataAdapter` beyond those strictly needed for gap computation
  (which requires none, as `get_prices()` is already abstract and available).

---

## 6. Proposed Decisions

The following decision IDs are drafted for review. They are **not appended to
`DECISIONS.md`** and will not be until explicit human instruction is given.
They are proposed only.

---

### Proposed D-081 — Phase 8C boundary: Local Price Gap Diagnostics selected, Tier 2 only

**Proposed date:** (to be filled on acceptance)
**Decision:** Phase 8C implements local price gap diagnostics only, within Tier 2.
Specifically: a pure function `compute_price_gaps(holdings, price_records)` (or equivalent
inline extension of `compute_data_quality`) that computes the largest consecutive date gap
per ticker from local SQLite price records; three nullable fields added to `TickerQuality`
(`largest_gap_days`, `largest_gap_start`, `largest_gap_end`); and optional extension of
the "Data Quality Caveat" `ReportSection` to include gap facts when gaps exceed a
configurable threshold. All text compliance-checked. No new API routes. No new persistence
tables. No new adapter abstract methods. No new runtime dependencies.
**Options considered:** Candidate B (CSV import diagnostics — deferred), Candidate C
(API contract documentation — deferred to frontend build phase), Candidate D (hardening
only — adopted as companion, not primary scope).
**Rationale:** Candidate A is the natural continuation of Phase 8A data quality analytics,
was explicitly deferred to Phase 8C in Phase 8B planning, and requires only a pure
function extension within the existing metrics module. Lowest boundary risk of all
candidates. Highest diagnostic value relative to scope.

---

### Proposed D-082 — Phase 8C purity constraint: gap computation is a pure function

**Proposed date:** (to be filled on acceptance)
**Decision:** All new functions added in Phase 8C for gap computation must satisfy the
same purity invariant as `compute_data_quality` and the metrics engine (D-030, D-068):
no I/O, no system clock, no environment variables, no persistence imports, no network
access. All data arrives as function arguments already fetched by the caller. The
`report_date` (if used for gap context) is always caller-provided, consistent with D-031
and D-056.
**Rationale:** Consistent with the purity invariant maintained across Phases 4–8B.
Pure functions are testable without fixtures and composable with any future orchestration
layer.

---

### Proposed D-083 — Phase 8C compliance constraint: gap text is compliance-checked

**Proposed date:** (to be filled on acceptance)
**Decision:** All system-generated strings describing gap facts placed in any
`ReportSection` label or body pass `check_compliance()` through `_make_section()` before
`ReportSection` construction, consistent with D-054 and D-077. No compliance guard
wordlist extensions are anticipated for gap description language (day counts, date strings,
ticker names). If any proposed wording triggers the guard, it must be revised; the guard
is not bypassed or narrowed. No advisory language is used or required: gap text describes
facts only ("largest price gap: N days, START to END"), not significance or implication.
**Rationale:** Consistent with D-039, D-054, D-069, and D-077. Compliance is a
non-optional chokepoint for all system-generated text.

---

### Proposed D-084 — Phase 8C data model: PriceGapResult and TickerQuality extension

**Proposed date:** (to be filled on acceptance)
**Decision:** Gap computation results are represented as a frozen dataclass `PriceGapResult`
(ticker, largest_gap_days, largest_gap_start, largest_gap_end) in
`backend/app/metrics/quality.py`. `TickerQuality` gains three nullable fields:
`largest_gap_days: int | None`, `largest_gap_start: str | None`,
`largest_gap_end: str | None`. Tickers with zero or one price record receive `None` for
all three gap fields. `DataQualitySummary` is not extended at the summary level — per-ticker
gap data is accessible via `ticker_quality`. The existing `data_quality` API key surfaces
the new fields automatically via `dataclasses.asdict()`. No new top-level API key is added.
**Rationale:** Consistent with D-071 (data quality result format). Optional fields with
`None` defaults preserve backward compatibility with existing tests and call sites.
`dataclasses.asdict()` recurses into nested frozen dataclasses without code changes in the
route layer (D-072).

---

### Proposed D-085 — Phase 8C architecture invariant: extended for Phase 8C modules

**Proposed date:** (to be filled on acceptance)
**Decision:** `backend/tests/architecture/test_no_broker_no_execution.py` is extended
with a targeted test for any new Phase 8C function in `backend/app/metrics/quality.py`:
confirming no broker imports, no execution definitions, no advisory language. Adapter
boundary tests are added confirming that no route module imports directly from
`backend/app/data/persistence/`. Repository contract tests are added for boundary
conditions on `HoldingsRepo`, `PricesRepo`, and `JournalRepo`.
**Rationale:** Consistent with D-070 and D-078. The invariant test grows with the codebase.
New functions and integration paths must be covered before acceptance.

---

### Proposed D-086 — Phase 8C test gate

**Proposed date:** (to be filled on acceptance)
**Decision:** Phase 8C implementation is accepted when `python -m pytest backend/tests/`
returns a passing count strictly greater than 647, with 0 skipped. New tests must cover:
(a) `compute_price_gaps` (or equivalent) pure function — unit tests for zero-record,
single-record, two-record, and multi-record cases; (b) largest-gap identification — correct
start/end dates, correct day count; (c) `TickerQuality` gap fields populated correctly
in `DataQualitySummary`; (d) Data Quality Caveat section — gap facts appear only when gap
exceeds threshold, not otherwise; (e) compliance of all new section text; (f) API
integration — `data_quality.ticker_quality[].largest_gap_days` present in response;
(g) purity — no system clock, no persistence imports in gap function; (h) adapter boundary
— no persistence repo imports in route modules; (i) repository contract boundary conditions;
(j) architecture invariant stable.
**Rationale:** Consistent with the per-phase test gate established across Phases 2–8B.
Each new module and integration path must have dedicated tests before acceptance.

---

## 7. Acceptance Criteria for This Planning Step

This document is accepted as a planning artefact when all of the following hold:

- [x] `docs/PHASE8C_CANDIDATE_PLAN.md` is written and committed.
- [x] No application code has been written or modified.
- [x] No dependencies have been added to `pyproject.toml`.
- [x] No modules under `backend/app/` have been changed.
- [x] No test files have been modified.
- [x] `DECISIONS.md` has not been modified (proposed D-081 through D-086 are not yet appended).
- [x] 647 tests pass with 0 skipped.
- [x] Architecture invariant is green.
- [x] Phase 8C implementation remains not approved.

Phase 8C implementation is approved only when:

1. The human owner reviews and accepts the recommended scope (§4) or selects an
   alternative from §3.
2. Proposed decisions D-081 through D-086 (or a subset) are explicitly directed to be
   appended to `DECISIONS.md` with dates filled in.
3. An explicit implementation prompt is issued.

---

*This document is a planning artefact. It does not approve Phase 8C implementation.
It does not modify any application module. It does not introduce any dependency.
It records the approved boundary, candidate options, recommended narrow scope, and
proposed decision text so the human owner can issue a precise implementation approval
when ready.*
