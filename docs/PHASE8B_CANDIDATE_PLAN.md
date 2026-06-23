# PHASE8B_CANDIDATE_PLAN.md

> **This is a planning document only.**
> It does not approve Phase 8B implementation. No application code may be written,
> no dependencies added, and no modules changed until a separate, explicit human
> approval is recorded in `DECISIONS.md`.
>
> This document records candidate options for Phase 8B within Option B / Tier 2 and
> recommends a narrow implementation scope for human review.

---

## 1. Purpose

Phase 8B is the candidate-selection planning step that follows Phase 8A acceptance.

It evaluates possible next improvements within **Option B — richer local analytics,
Tier 2 only**. It does not constitute implementation approval.

Phase 8B requires all of the following before any code is written:

1. Human review and explicit approval of the selected candidate.
2. Proposed decisions (§6) directed to be appended to `DECISIONS.md` with dates filled in.
3. An explicit implementation prompt issued by the human owner.

Otomasyon remains a local-first personal finance research and decision-support instrument.
Phase 8B does not change that identity. The automation ceiling is unchanged:
**read → compute → notify**. Nothing acts on a market.

---

## 2. Current Baseline

The following capabilities are accepted as of commit `717c21b`:

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

**Test baseline:** 585 passed, 0 skipped.
**Runtime dependencies:** `fastapi>=0.100.0` only.
**Dev dependencies:** `httpx2` only.

### What the API currently exposes

`GET /reports/daily?report_date=YYYY-MM-DD` and
`GET /reports/weekly?week_start=YYYY-MM-DD&report_date=YYYY-MM-DD` each return a
serialised `DailyReport` / `WeeklyReport` containing:

- `sections` — list of compliance-checked `ReportSection` objects (label + body text).
- `journal_entries` — user-authored entries carried verbatim.
- `data_quality` — structured `DataQualitySummary` with per-ticker `TickerQuality`.
- `report_date`, `report_type`, and (for weekly) `week_start`.

All computed values are produced from data already in the local SQLite database.
No external calls. No system clock. No advisory language.

---

## 3. Candidate Options

Four candidates are evaluated below. All are within Tier 2 (read → compute → notify).
None crosses into paper trading, execution, external data, or advisory output.

---

### Candidate A — Report Explainability Improvements

#### Description

Add one or more `ReportSection` blocks that define the metrics and alert rules used
in the report, drawn from language in `METRICS_SPEC.md` and `ALERT_POLICY.md`. The
goal is to make each report self-contained and interpretable without requiring the user
to consult external documentation.

Example additions:

- A "Metric Definitions" section naming and describing M-001 through M-006 using
  plain, fact-stating language (e.g., "M-005 measures the percentage decline in
  portfolio value from its peak within the prior 30 days.").
- A "Alert Rule Definitions" section describing what each rule measures and the
  threshold comparison used (e.g., "CONC-001 fires when a single position's weight
  exceeds the configured concentration ceiling.").
- A structured "Data Quality Caveat" section — when `unpriced_tickers` is non-empty
  or coverage ratios are low — explaining which metrics are affected and why (e.g.,
  "M-005 and M-006 are computed using only positions with available price data.
  Positions without price data are excluded from time-series calculations.").

All text would be compliance-checked through `check_compliance()` via `_make_section()`
before construction, consistent with D-054. No advisory or predictive language required.

#### Value

- Removes the need to read `METRICS_SPEC.md` or `ALERT_POLICY.md` to understand a
  report. Each report becomes a standalone artefact.
- The data quality caveat variant directly improves interpretability of Phase 8A output
  by surfacing which analytics are undermined by missing data.
- Pure report-builder extension: the builder already has the data to produce these
  sections without any new I/O or persistence changes.

#### Implementation risk

**Low.** All new content is static or derived from already-computed result objects
(`DrawdownResult`, `VolatilityResult`, `AlertResult`, `DataQualitySummary`). The
pattern is identical to existing section builders in `builder.py`. No new data sources,
no new metrics, no new persistence methods.

#### Compliance risk

**Low.** The language pool (metric names, formula descriptions, threshold comparisons)
is already cleared in `METRICS_SPEC.md` and `ALERT_POLICY.md`. The compliance guard
will catch any inadvertent forbidden term before it reaches a `ReportSection`.
No `buy`, `sell`, `hold`, `profit`, or `opportunity` language is needed or appropriate
for definitions.

#### Boundary risk

**Very low.** Pure builder extension within the existing `backend/app/reports/` module.
No new imports outside `app.metrics`, `app.alerts`, `app.compliance`, and `app.reports`.
No new API routes. No new persistence methods. No schema change.

#### Recommendation

**Recommended.** Candidate A is the lowest-risk, highest-clarity improvement available.
It directly addresses a known usability gap (reports reference metrics by ID without
defining them) and builds on the Phase 8A foundation by adding a compliance-ready
"Data Quality Caveat" path for low-coverage portfolios.

---

### Candidate B — API Contract Clarity

#### Description

Produce documentation artefacts that formally specify the JSON response shape for
`GET /reports/daily` and `GET /reports/weekly`. This may include:

- A machine-readable schema document (`docs/API_RESPONSE_SCHEMA.md` or a JSON Schema
  file under `docs/`) describing every top-level key, its type, and whether it may be
  `null`.
- Example JSON payloads illustrating an empty-portfolio response, a fully-priced
  portfolio response, and an unpriced-ticker response.
- Optionally, explicit API contract tests in the integration test suite asserting
  required key presence, types, and structural invariants — ensuring regressions are
  caught at test time rather than discovered by callers.

No new routes are added. The API implementation itself is not changed.

#### Value

- Makes the API consumable without inspecting source code. Any future frontend, script,
  or analysis tool can be written against a stable documented shape.
- API contract tests would catch structural regressions (e.g., a field removed or
  renamed) before they escape to callers.
- Pure documentation and test work: no application code changes.

#### Implementation risk

**Very low** for the documentation variant. **Low** for the test-only variant.
If contract tests are added, they follow the same pattern as existing integration tests
in `test_api_reports.py` — no new infrastructure needed.

#### Compliance risk

**None.** Documentation artefacts and tests contain no system-generated user-facing
text. The compliance guard is not relevant to schema documents or test assertions.

#### Boundary risk

**None** for the documentation-only variant. **Very low** for added contract tests —
tests run inside the existing `backend/tests/` harness against an in-memory database
with no external calls.

#### Recommendation

**Recommended as a companion to Candidate A, not as the primary Phase 8B scope.**
The documentation variant (schema doc + example payloads) adds real value for future
consumers and is essentially zero-risk, but it does not extend Otomasyon's analytical
capability. As a standalone Phase 8B it may not justify a full phase gate. Better
combined with Candidate A or Candidate D, or deferred until a frontend is being built.

---

### Candidate C — Local Data Diagnostics

#### Description

Extend the local data pipeline to surface richer validation and quality information
about what has been imported into the database. Possible variants:

- **Import error history:** Persist row-level `ImportResult.errors` from CSV price
  imports to a dedicated `import_errors` table in SQLite, so the user can later query
  past import failures without re-running the import. Expose via a new read-only API
  route (`GET /import-errors?since=YYYY-MM-DD`).
- **Gap detection:** For each held ticker with price history, compute the largest gap
  (in calendar days) between consecutive price records. Surface this in the data quality
  summary to help the user identify periods of missing price data that could distort
  time-series metrics.
- **Holdings/watchlist coverage gap:** Report tickers present in the watchlist but not
  in holdings, and tickers present in holdings but not in the watchlist, including
  price availability for each. Pure computation from existing local data.

#### Value

- Import error history makes CSV ingestion auditable. Users who re-ingest price files
  can see which rows were previously rejected without reconstructing the import.
- Gap detection complements Phase 8A data quality by surfacing not just "how many records"
  but "where the data is missing" — directly relevant to M-005 (drawdown) and M-006
  (volatility) reliability.
- Holdings/watchlist gap is a zero-cost diagnostic: all data already exists.

#### Implementation risk

**Medium** for the import error history variant — requires a new schema table, a new
persistence repository, a new `DataAdapter` abstract method, and a new API route.
This is more surface area than Candidates A and B and carries more integration risk.

**Low** for gap detection — it extends `compute_data_quality` or adds a companion pure
function in `backend/app/metrics/`. No schema changes needed.

**Low** for holdings/watchlist gap — pure computation from existing adapter methods.

#### Compliance risk

**Low.** Gap and coverage language is purely factual ("largest gap: N days between
YYYY-MM-DD and YYYY-MM-DD"). No forbidden terms required. Import error messages from
CSV rows are user-supplied data, not system-generated advisory text, so compliance
scanning is not applied to stored error strings.

#### Boundary risk

**Medium** for import error history — introduces a new persistence table and repository,
a new `DataAdapter` method, and a new API route. Each of these is a new surface that
requires architecture invariant coverage.

**Very low** for gap detection and holdings/watchlist gap — pure function extensions
within the existing metrics module.

#### Recommendation

**Gap detection is recommended as an addition to Candidate A.** It extends Phase 8A
data quality analytics naturally and requires only a pure function extension.

**Import error history is not recommended for Phase 8B.** The schema change and new
repository/route surface area are disproportionate to the value. It would be better
scoped as a separate Phase 8C candidate after Phase 8B is accepted.

**Holdings/watchlist gap is low-risk and worth considering** but similarly better
bundled with a larger analytical extension than treated as a standalone phase.

---

### Candidate D — Test and Architecture Hardening

#### Description

Strengthen the test suite and architecture invariant without adding product features:

- **Compliance regression tests:** Parametrised tests asserting that every
  system-generated `ReportSection` body in a representative set of scenarios contains
  none of the compliance guard's forbidden terms. Ensures future report text additions
  are compliance-verified before merge.
- **Route boundary extension:** Additional tests asserting that `routes/reports.py`
  imports no forbidden modules beyond those already tested (e.g., explicit check that
  `requests`, `httpx`, `aiohttp` are absent; explicit check that no `open()` or
  `subprocess` call exists).
- **Pure function regression tests:** Additional parametrised tests for
  `compute_data_quality` edge cases: a single holding with exactly one price record on
  the report date, multiple holdings with identical tickers across different `PriceRecord`
  inputs, price records with a very large number of records per ticker.
- **Architecture invariant extension:** Add a broader scan for any file under
  `backend/app/` that imports `os`, `subprocess`, `socket`, `threading`, or standard
  network libraries (`requests`, `httpx`, `aiohttp`, `urllib.request`) — modules not
  appropriate for the pure analytics layer.

#### Value

- Compliance regression tests catch forbidden-language regressions at development time,
  before a human acceptance audit.
- Route boundary and architecture invariant hardening make it harder for future phases
  to accidentally widen the scope boundary without the test suite flagging it.
- Edge-case tests reduce the risk that a future refactor of `compute_data_quality`
  silently changes behavior on boundary inputs.

#### Implementation risk

**Very low.** All work is inside `backend/tests/`. No application code changes.
No new runtime dependencies.

#### Compliance risk

**None.** Tests are not user-facing text.

#### Boundary risk

**None.** Test files are explicitly excluded from the architecture invariant scan.
The scan itself only covers `backend/app/` and `frontend/src/`.

#### Recommendation

**Recommended as a companion to any other candidate, not as a standalone Phase 8B.**
Hardening tests are always valuable but do not advance Otomasyon's analytical capability.
They are best bundled with a feature candidate (A or C-gap) so that new modules arrive
with stronger boundary coverage from the start.

---

## 4. Recommended Phase 8B Direction

**Recommended: Candidate A — Report Explainability Improvements**
with **Candidate D — Test and Architecture Hardening** as a companion.

### Narrow scope

1. **Metric definition section** — a new `ReportSection` ("Metric Definitions") in both
   daily and weekly reports that names and describes each metric used (M-001 through
   M-006, or the subset evaluated in the report), using fact-stating language from
   `METRICS_SPEC.md`. Compliance-checked through `_make_section()`.

2. **Alert rule definition section** — a new `ReportSection` ("Alert Rule Definitions")
   describing what each evaluated alert rule measures and what threshold comparison is
   used. Compliance-checked. No wording implying action.

3. **Data quality caveat section** — a conditional `ReportSection` ("Data Quality
   Caveat") added when `data_quality.unpriced_holding_count > 0` or
   `data_quality.coverage_ratio < 1.0`, explaining which time-series metrics
   (M-005, M-006) are affected by missing price data. Compliance-checked. No advisory
   language.

4. **Companion hardening tests** — compliance regression tests (parametrised) for all
   system-generated section text; route boundary tests extended; architecture invariant
   extended to scan for `os.system`, `subprocess`, `requests`, `httpx`, and `socket`
   imports in `backend/app/`.

### Rationale

- Lowest boundary risk of all candidates.
- Pure builder extension: identical pattern to existing section builders.
- No new imports outside the existing report module dependencies.
- No new API routes, no schema changes, no new repositories.
- Directly increases report value by making each report self-contained and interpretable.
- Data quality caveat builds on Phase 8A analytics without introducing new computation.
- Companion hardening tests future-proof the boundary against scope drift in Phase 8C+.

### What this does NOT include

Gap detection (Candidate C-gap) and import error history are deferred to Phase 8C.
API schema documentation (Candidate B) is deferred to when a frontend is being built.
No new routes, no new persistence methods, no new schema tables.

---

## 5. Explicit Out-of-Scope List

The following are explicitly excluded from Phase 8B and from Option B generally.
They may not be introduced without a new gate review and explicit human approval.

| Category | Excluded items |
|---|---|
| Simulation | Paper trading, simulated orders, fill simulation, position open/close lifecycle |
| Execution | Broker abstraction, trading credentials, order placement (real or simulated) |
| Signals | Trading signals, buy/sell recommendations, target prices, opportunity identification |
| Indicators | Moving averages, RSI, MACD, Bollinger bands, any technical indicator |
| Backtesting | Historical strategy evaluation, strategy performance metrics, P&L reconstruction |
| External data | Market data APIs, web scraping, news feeds, earnings calendars, external HTTP calls |
| Automation | Scheduler, cron trigger, push notifications, email, webhooks |
| Scope expansion | Multi-currency aggregation, multi-portfolio (each requires its own gate) |
| Frontend | React/Vite UI development (deferred; the empty shell remains unchanged) |
| Advisory output | Any system-generated text implying action, recommendation, or predicted outcome |
| Authentication | User accounts, session management, access control |

---

## 6. Proposed Decisions

The following decision IDs are drafted for review. They are **not appended to
`DECISIONS.md`** and will not be until explicit human instruction is given.
They are proposed only.

---

### Proposed D-075 — Phase 8B boundary: Candidate A selected, Tier 2 only

**Proposed date:** (to be filled on acceptance)
**Decision:** Phase 8B implements report explainability improvements only, within Tier 2.
Specifically: a "Metric Definitions" section, an "Alert Rule Definitions" section, and a
conditional "Data Quality Caveat" section added to daily and weekly reports via
`backend/app/reports/builder.py`. All new text is system-generated, compliance-checked,
and fact-stating only. No new API routes, no new persistence methods, no schema changes.
**Options considered:** Candidate B (API contract clarity — deferred), Candidate C
(local data diagnostics — gap detection deferred to Phase 8C), Candidate D (hardening
only — adopted as companion, not primary scope).
**Rationale:** Candidate A is the lowest-risk, highest-clarity improvement within the
existing architecture. It directly extends the Phase 8A data quality foundation without
widening the boundary.

---

### Proposed D-076 — Phase 8B purity constraint: new section builders are pure functions

**Proposed date:** (to be filled on acceptance)
**Decision:** All new functions added to `backend/app/reports/builder.py` in Phase 8B
must satisfy the same purity invariant as the existing section builders: no I/O, no
system clock, no environment variables, no persistence imports, no network access.
Data arrives as function arguments (already-computed result objects). Report date
is always caller-provided.
**Rationale:** Consistent with D-030, D-052, and D-068. Pure functions are testable
without fixtures and composable with any future orchestration layer.

---

### Proposed D-077 — Phase 8B compliance constraint: all new section text is checked

**Proposed date:** (to be filled on acceptance)
**Decision:** All strings placed in new `ReportSection` labels and bodies pass
`check_compliance()` through `_make_section()` before `ReportSection` construction,
consistent with D-054. No new compliance guard wordlist extensions are anticipated for
metric definition or alert rule description language. If any proposed wording triggers
the guard, it must be revised; the guard is not bypassed or narrowed.
**Rationale:** Consistent with D-039 and D-054. Compliance is a non-optional chokepoint.

---

### Proposed D-078 — Phase 8B architecture invariant: extended for Phase 8B modules

**Proposed date:** (to be filled on acceptance)
**Decision:** `backend/tests/architecture/test_no_broker_no_execution.py` is extended
with tests confirming that `backend/app/reports/builder.py` (as extended in Phase 8B)
imports no forbidden modules and that no advisory signal language is introduced. A
broader scan for `os.system`, `subprocess`, `socket`, `requests`, `httpx`, and
`aiohttp` imports across all files in `backend/app/` is added as a new invariant test.
**Rationale:** Consistent with D-070. The invariant test grows with the codebase.
New modules and extensions must be covered before they are accepted.

---

### Proposed D-079 — Phase 8B report section placement policy

**Proposed date:** (to be filled on acceptance)
**Decision:** New explainability sections are placed at the end of the report, after
the existing "Method Note" and before or replacing the "Disclaimer" section. The
"Data Quality Caveat" section (when present) is placed immediately after the
"Data Quality Summary" section established in Phase 8A. Placement is determined by
the `build_daily_report` and `build_weekly_report` functions; callers do not control
section order.
**Rationale:** Existing report consumers (tests and any future frontend) depend on
section order. Appending at the end minimises the risk of breaking existing integration
tests that check specific section presence.

---

### Proposed D-080 — Phase 8B test gate

**Proposed date:** (to be filled on acceptance)
**Decision:** Phase 8B implementation is accepted when `python -m pytest backend/tests/`
returns a passing count strictly greater than 585, with 0 skipped. New tests must cover:
(a) new section presence in daily and weekly report output; (b) compliance of all new
section text (parametrised across representative scenarios); (c) absence of forbidden
language in new section bodies; (d) conditional "Data Quality Caveat" section present
only when coverage is incomplete; (e) extended architecture invariant.
**Rationale:** Consistent with the per-phase test gate established across Phases 2–8A.
Each new module and integration path must have dedicated tests before acceptance.

---

## 7. Acceptance Criteria for This Planning Step

This document is accepted as a planning artefact when all of the following hold:

- [x] `docs/PHASE8B_CANDIDATE_PLAN.md` is written and committed.
- [x] No application code has been written or modified.
- [x] No dependencies have been added to `pyproject.toml`.
- [x] No modules under `backend/app/` have been changed.
- [x] No test files have been modified.
- [x] `DECISIONS.md` has not been modified (proposed D-075 through D-080 are not yet appended).
- [x] 585 tests pass with 0 skipped.
- [x] Architecture invariant is green.
- [x] Phase 8B implementation remains not approved.

Phase 8B implementation is approved only when:

1. The human owner reviews and accepts the recommended scope (§4) or selects an
   alternative from §3.
2. Proposed decisions D-075 through D-080 (or a subset) are explicitly directed to be
   appended to `DECISIONS.md` with dates filled in.
3. An explicit implementation prompt is issued.

---

*This document is a planning artefact. It does not approve Phase 8B implementation.
It does not modify any application module. It does not introduce any dependency.
It records the approved boundary, candidate options, recommended narrow scope, and
proposed decision text so the human owner can issue a precise implementation approval
when ready.*
