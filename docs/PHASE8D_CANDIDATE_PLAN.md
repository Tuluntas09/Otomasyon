# PHASE8D_CANDIDATE_PLAN.md

> **This is a planning document only.**
> It does not approve Phase 8D implementation. No application code may be written,
> no dependencies added, and no modules changed until a separate, explicit human
> approval is recorded in `DECISIONS.md`.
>
> This document records candidate options for Phase 8D within Option B / Tier 2 and
> recommends a narrow implementation scope for human review.

---

## 1. Purpose

Phase 8D is the candidate-selection planning step that follows Phase 8C acceptance.

It evaluates possible next improvements within **Option B — richer local analytics,
Tier 2 only**. It does not constitute implementation approval.

Phase 8D requires all of the following before any code is written:

1. Human review and explicit approval of the selected candidate.
2. Proposed decisions (§6) directed to be appended to `DECISIONS.md` with dates filled in.
3. An explicit implementation prompt issued by the human owner.

Otomasyon remains a local-first personal finance research and decision-support instrument.
Phase 8D does not change that identity. The automation ceiling is unchanged:
**read → compute → notify**. Nothing acts on a market.

---

## 2. Current Baseline

The following capabilities are accepted as of commit `e7e8d63`:

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
| Local price-date gap diagnostics | `backend/app/metrics/quality.py` (extended) | ✅ accepted (Phase 8C) |
| Repository/adapter hardening | `backend/tests/architecture/` (extended) | ✅ accepted (Phase 8C) |

**Test baseline:** 701 passed, 0 skipped.
**Runtime dependencies:** `fastapi>=0.100.0` only.
**Dev dependencies:** `httpx2` only.

### What Phase 8C added

Phase 8C extended `compute_data_quality()` and `TickerQuality` in
`backend/app/metrics/quality.py` with four new fields:

- `local_price_date_count_on_or_before_report_date` — unique local price dates on or
  before the report date (duplicates collapsed).
- `largest_price_date_gap_days: int | None` — calendar days of the largest consecutive
  gap between unique local price dates on or before the report date.
- `largest_price_date_gap_start: str | None` — ISO-8601 start date of the largest gap.
- `largest_price_date_gap_end: str | None` — ISO-8601 end date of the largest gap.

Phase 8C also extended the "Data Quality Summary" `ReportSection` body with per-ticker
gap facts and a gap methodology note, and added four new architecture invariant tests:
no raw SQL in API routes, no direct persistence repo imports in API routes, quality
module layer isolation, and quality module system-clock purity.

No new API routes, no new persistence tables, no new adapter abstract methods, and no
new runtime dependencies were introduced.

### Items deferred from earlier phases to Phase 8D

The following were evaluated in earlier planning documents and explicitly deferred:

- **API contract documentation** (Candidate C in Phase 8B, Candidate C in Phase 8C) —
  schema document and example JSON payloads; deferred until response shape stabilised.
  The response shape is now stable: all Phase 8A–8C fields are accepted.
- **CSV import diagnostics — summary-only** (Candidate B in Phase 8C) — structural
  enrichment of `ImportResult`; deferred as lower diagnostic value than gap diagnostics.
- **Local data flow documentation** — data flow prose in `docs/ARCHITECTURE.md` was
  identified in Phase 8C but not adopted as the primary scope.
- **API error taxonomy** — error response shapes are implemented but not formally
  documented or structurally tested.

---

## 3. Candidate Options

Four candidates are evaluated below. All are within Tier 2 (read → compute → notify).
None crosses into paper trading, execution, external data, or advisory output.

---

### Candidate A — API Contract Documentation

#### Description

Produce documentation artefacts that formally specify the JSON response shape for the
three existing read-only routes: `GET /health`, `GET /reports/daily`, and
`GET /reports/weekly`. The response shape now includes Phase 8A data quality fields and
Phase 8C gap diagnostic fields; it is stable and complete for documentation.

Scope:

- **Schema document:** A Markdown file under `docs/` (e.g., `docs/API_CONTRACT.md`)
  describing every key in each route response — its type, whether it may be `null`,
  and which phase introduced it. Covers `data_quality`, `ticker_quality`,
  `largest_price_date_gap_*` fields, report sections, journal entries, and
  the `GET /health` shape.
- **Example JSON payloads:** Four representative scenarios documented inline in the
  schema file or as companion `.json` files under `docs/examples/`:
  1. Zero holdings — empty portfolio, empty price history.
  2. All holdings priced, no alerts fired.
  3. One or more holdings unpriced — triggers "Data Quality Caveat" section.
  4. One or more alerts fired — alert section shows fired status and values.
  Each example includes `data_quality.ticker_quality` with the Phase 8C gap fields.
- **Optional API contract tests:** Parametrised integration tests in
  `backend/tests/integration/` asserting required key presence, types, and structural
  invariants on route responses. Follow the existing pattern in
  `backend/tests/integration/test_api_reports.py`. No new infrastructure required.

No new API routes. No application code changed for the documentation-only variant.

#### Expected value

- Makes the API response consumable without inspecting source code. Any future consumer
  (script, analysis tool, or a future frontend build) can be written against a stable,
  documented shape.
- Example payloads make the Phase 8A and Phase 8C diagnostic fields immediately
  understandable — their context (priced vs. unpriced, gap present vs. absent) is shown
  concretely rather than described abstractly.
- Optional contract tests would catch structural regressions (renamed or removed fields,
  changed null/non-null status) before they escape to callers. Each Phase 8A–8C
  acceptance added fields; a contract test suite locks them in.
- Documentation-only variant requires zero application code changes — lowest possible
  implementation risk.

#### Implementation risk

**Very low** for the documentation-only variant — no code changes of any kind.
**Low** for the optional test variant — follows existing integration test patterns exactly;
no new fixtures, no new infrastructure.

#### Compliance risk

**None.** Documentation artefacts and test assertion strings are not system-generated
user-facing text. The compliance guard is not relevant to schema documents or structural
test assertions.

#### Boundary risk

**None** for the documentation-only variant.
**Very low** for added contract tests — tests run inside the existing
`backend/tests/` harness against an in-memory database. No new persistence tables,
no new adapter methods, no new routes.

#### Recommendation

**Recommended as the primary Phase 8D candidate.**

Candidate A has been explicitly deferred from both Phase 8B and Phase 8C. The response
shape was the stated reason for deferral both times ("deferred until a frontend consumer
is being built" in Phase 8B; "deferred to frontend build phase" in Phase 8C).

Phase 8C acceptance changes the calculus: the response shape is now complete and stable.
All planned Phase 8 analytics fields have been accepted. Documenting the shape now
captures the full Phase 8A–8C surface in a single artefact before any future phase adds
more fields or before an external consumer makes a contract assumption the code does not
guarantee.

The optional contract tests component strengthens the argument: they convert the schema
document from a description into an enforced specification. Structural regressions become
test failures rather than silent behavioral changes.

---

### Candidate B — CSV Import Diagnostics Summary

#### Description

Improve local visibility into CSV import outcomes by enriching the structure of the
return value from `backend/app/data/adapters/csv_importer.py`. Two variants:

- **Summary-only (no new persistence):** Return a more explicit structured summary from
  the importer — for example, a dedicated dataclass (e.g., `CsvImportSummary`) exposing
  `rows_processed`, `rows_accepted`, `rows_rejected`, and `error_categories: dict[str, int]`
  (a count per validation error type). The importer already returns an `ImportResult` with
  `errors`; this variant structures the existing output more explicitly. No new persistence
  table. No new API route. The summary is available to any caller that invokes the importer.
- **Persisted import history (requires separate approval):** Persist row-level
  `ImportResult.errors` to a new `import_errors` table. Requires a new schema table, a new
  repository, a new abstract method on `DataAdapter`, and a new read-only API route.
  Not recommended without separate gate approval.

For Phase 8D evaluation, only the summary-only variant is in scope.

#### Expected value

- Makes import validation outcomes visible as structured data rather than a list of
  free-text error strings. A caller can inspect `error_categories` to determine whether
  failures are date-format errors, missing columns, duplicate tickers, negative quantity
  errors, and so on.
- Complements the existing test coverage of `csv_importer.py` — structured error
  categories could be unit-tested deterministically.
- The summary-only variant makes existing behavior more ergonomic without adding surface area.

#### Implementation risk

**Low.** `ImportResult` already carries `errors`; this is a structural change to an
existing return type. No persistence, no new routes, no new adapter methods.

#### Compliance risk

**Low.** Import error messages derive from CSV row validation failures — user-supplied
data. Error category keys (e.g., `"invalid_date"`, `"duplicate_ticker"`) are system-defined
labels, not system-generated advisory sentences passed through `check_compliance()`, and
consistent with D-046 (user-authored data not scanned).

#### Boundary risk

**Low** for the summary-only variant — structural change to an existing return type.
No new persistence or API surface. No new abstract methods on `DataAdapter`.

#### Recommendation

**Deferred.** The summary-only variant is low-risk but provides lower diagnostic value
than Candidate A: import validation errors are already visible to any caller inspecting
`ImportResult.errors` today. This candidate improves ergonomics rather than adding new
observability.

The persisted-history variant requires a new persistence table, repository, adapter
method, and API route — a boundary extension that exceeds the scope appropriate for a
single Phase 8 step. That variant must be evaluated as a standalone gate item.

Candidate B summary-only could be bundled as a minor companion to Candidate A if the
human owner chooses to extend Phase 8D scope, but is not recommended as the primary scope.

---

### Candidate C — Local Data Flow Documentation

#### Description

Produce or extend documentation that formally describes the end-to-end data flow through
the Otomasyon system and establishes clear layer ownership and forbidden dependencies.

Scope:

- **Data flow prose:** A new section in `docs/ARCHITECTURE.md` (or a standalone
  `docs/DATA_FLOW.md`) describing the canonical path:
  `CSV → csv_importer → SQLite (HoldingsRepo, PricesRepo, JournalRepo) →
  SQLiteDataAdapter → metrics engine (compute_portfolio_snapshot, compute_drawdown,
  compute_volatility_proxy, compute_data_quality) → alert evaluator → report builder →
  FastAPI route handler → JSON response`.
  For each layer: what it receives, what it computes or transforms, what it returns,
  and what it must not do.
- **Layer ownership table:** A table naming each module, its owning layer (persistence,
  adapter, metrics, alerts, compliance, reports, api), and the forbidden imports that
  would violate the layering invariant.
- **Forbidden dependency matrix:** A concise cross-layer matrix showing which layers
  may import from which others (e.g., metrics may not import from api or persistence;
  reports may not import from persistence or adapter; api/routes may not import from
  persistence directly).
- **Architecture invariant cross-reference:** For each forbidden dependency listed in
  the matrix, note which architecture test in `backend/tests/architecture/` enforces it.
  Where a forbidden dependency is described but not yet tested, mark it as a gap.
- **Optional test-only hardening:** Fill any documented gaps in the architecture invariant
  coverage identified above. Requires no application code changes.

No product feature changes. No new API routes. No new persistence tables.

#### Expected value

- Reduces onboarding friction and makes layer ownership explicit for future contributors
  or reviewers.
- The forbidden dependency matrix makes it easy to verify that a proposed code change
  does not violate the architecture invariant before implementation.
- Cross-referencing existing invariant tests with documented rules makes the test suite
  self-describing — a reader can see which tests enforce which architectural rules.
- Identifying documented-but-untested forbidden dependencies (gaps) provides a prioritised
  list for future hardening work.

#### Implementation risk

**Very low.** All work is in `docs/` and optionally `backend/tests/architecture/`.
No application code changes. No new runtime dependencies.

#### Compliance risk

**None.** Architecture documentation and test assertions are not user-facing text.

#### Boundary risk

**None** for the documentation-only variant.
**Very low** for optional additional invariant tests — these extend an existing test
module and run in the same harness.

#### Recommendation

**Deferred as a standalone Phase 8D candidate.** Candidate C is low-risk and genuinely
useful, but its scope overlaps partially with documentation already written across Phase
8A–8C planning documents and `docs/ARCHITECTURE.md`. The incremental value as a full
phase scope is modest.

The test-only gap-filling component could be bundled as a companion to Candidate A
(similar to how Phase 8C bundled Candidate D hardening as a companion to price gap
diagnostics). As a standalone phase, the value-to-scope ratio is lower than Candidate A.

Candidate C is the natural follow-on after Candidate A is accepted, when the contract
documentation surface makes the data flow and layer ownership discussion concrete and
directly useful to a consumer reading the API contract.

---

### Candidate D — API Error Taxonomy

#### Description

Standardise and document the current error response shapes returned by the three
existing read-only routes for all known failure modes.

Scope:

- **Error taxonomy document:** A section in `docs/API_CONTRACT.md` (if Candidate A is
  also adopted) or a standalone `docs/API_ERRORS.md` file documenting every distinct
  error response shape currently returned:
  - `HTTP 422` — invalid `report_date` or `week_start` (invalid format, invalid range,
    missing required parameter).
  - `HTTP 422` — `week_start` after `report_date` for weekly route.
  - `HTTP 200` with empty sections — valid date parameters but zero holdings in local
    database.
  - `HTTP 500` — unexpected internal error (current behavior: unhandled exception
    propagates through FastAPI's default error handler).
  For each: HTTP status code, `Content-Type`, body structure, field names, example payload.
- **Error shape invariant:** The existing HTTP 422 error body structure
  (`{error, field, value, message}`) is documented from `D-060`. Confirm whether the
  actual route implementation matches this shape in all error branches.
- **Optional structural tests:** Parametrised integration tests asserting that each
  documented error scenario returns the documented status code and body structure.
  No new behavior introduced. Tests only verify current behavior.

No new behavior. No new routes. No application code changes unless tests reveal a
discrepancy between documented and actual error shapes (which would require separate approval).

#### Expected value

- Makes error handling predictable for any future consumer — a script, analysis tool,
  or frontend can reliably detect and handle each failure mode without guessing.
- Reveals any discrepancy between `D-060`'s documented error shape and the actual
  implementation — a gap that is currently invisible without reading source code.
- Optional structural tests lock in the current error behavior, making it a regression
  failure if a future change alters an error status code or body structure without review.
- Naturally complements Candidate A (API contract documentation) — the two together
  cover the full API surface (success responses + error responses).

#### Implementation risk

**Very low** for the documentation-only variant — no code changes.
**Low** for the optional structural tests — follows existing integration test patterns.
Possible risk: if structural tests reveal a discrepancy in the HTTP 500 path, fixing it
requires application code changes that must be separately approved.

#### Compliance risk

**None.** Error documentation and test assertions are not user-facing text. The
compliance guard is not relevant to HTTP status codes, field names, or error body schemas.

#### Boundary risk

**None** for the documentation-only variant.
**Very low** for structural tests — run in the existing `backend/tests/integration/`
harness, in-memory database, no new infrastructure.

#### Recommendation

**Recommended as a companion to Candidate A, not as a standalone Phase 8D candidate.**

Candidate D has strong synergy with Candidate A: together they produce a complete API
contract covering both success and error shapes. As a standalone phase, Candidate D
covers only a small portion of the API surface and is insufficient to justify a full
phase gate.

If the human owner selects Candidate A as the primary Phase 8D scope, Candidate D's
error taxonomy section should be bundled into the same documentation artefact
(`docs/API_CONTRACT.md`) rather than opened as a separate phase. This mirrors the
pattern of Phase 8C bundling Candidate D hardening as a companion to the primary candidate.

---

## 4. Recommended Phase 8D Direction

**Recommended: Candidate A — API Contract Documentation**
with **Candidate D — API Error Taxonomy** bundled as a documentation companion.

### Narrow scope

1. **Schema documentation** — a `docs/API_CONTRACT.md` file documenting every key in
   the JSON response for `GET /health`, `GET /reports/daily`, and `GET /reports/weekly`.
   Coverage includes:
   - All Phase 7B base fields (sections list, journal entries list).
   - All Phase 8A `data_quality` fields (DataQualitySummary and TickerQuality).
   - All Phase 8C `ticker_quality` gap diagnostic fields
     (`local_price_date_count_on_or_before_report_date`, `largest_price_date_gap_days`,
     `largest_price_date_gap_start`, `largest_price_date_gap_end`).
   - `GET /health` response shape.
   For each field: key name, JSON type, nullable/required status, which phase introduced
   it, and a one-line description.

2. **Error taxonomy** — an "Error Responses" section within `docs/API_CONTRACT.md`
   documenting all current HTTP 422 failure modes per route and the HTTP 200 empty-data
   scenario. References D-060 for the `{error, field, value, message}` shape.

3. **Example JSON payloads** — four representative response examples documented inline
   in `docs/API_CONTRACT.md` or as companion files under `docs/examples/`:
   - Scenario 1: Zero holdings.
   - Scenario 2: All holdings priced, no alerts fired.
   - Scenario 3: One or more holdings unpriced (Data Quality Caveat section present,
     `unpriced_holding_count > 0`, gap fields populated in `ticker_quality`).
   - Scenario 4: One or more alerts fired (alert section shows fired status).

4. **Optional API contract tests** — parametrised integration tests in
   `backend/tests/integration/` (following the existing pattern in
   `test_api_reports.py`) asserting:
   - Required top-level keys present in all route responses.
   - `data_quality` key present and non-null for both routes.
   - `ticker_quality` array present in `data_quality`.
   - All four Phase 8C gap fields present in each `ticker_quality` element.
   - HTTP 422 returned for invalid `report_date` format.
   - HTTP 422 returned for `week_start` after `report_date`.
   - Error body contains `error`, `field`, `value`, `message` keys.
   No new behavior. Tests verify existing response structure only.

### Rationale

- Candidate A was explicitly deferred from Phase 8B ("deferred until a frontend consumer
  is being built") and again from Phase 8C ("deferred to frontend build phase").
- Phase 8C acceptance closes the primary deferral reason: the response shape now includes
  all planned Phase 8 fields and is stable. Documenting it now locks in the full
  Phase 8A–8C analytical surface before any future phase adds more fields.
- Optional contract tests convert the documentation from a description into an enforced
  specification, consistent with the pattern of bundling test hardening as companions to
  each primary Phase 8 candidate (Phase 8B: architecture tests as companion; Phase 8C:
  adapter boundary tests as companion).
- Candidate D error taxonomy is a natural documentation companion, not a separate phase.
  It adds no implementation risk and completes the contract document.
- Zero application code changes for the documentation-only variant. This is the
  lowest-risk path available within Option B / Tier 2.

### What this does NOT include

CSV import diagnostics (Candidate B) are deferred. Local data flow documentation
(Candidate C) is deferred to follow Candidate A when the API contract discussion makes
layer ownership directly useful to a consumer. No new write routes. No new schema tables.
No new abstract adapter methods. No new runtime dependencies.

---

## 5. Explicit Out-of-Scope List

The following are explicitly excluded from Phase 8D and from Option B generally.
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
| New API routes | No new GET routes unless separately approved at a future gate |

In addition, the following specific items are out-of-scope for Phase 8D even though they
are within Tier 2:

- Persisted import error history — CSV import diagnostics with a new persistence table
  and new API route require separate gate approval.
- Exchange calendar annotation — the API contract document must not describe any field
  as referring to trading days, market sessions, or expected price coverage vs. exchange
  calendars. All gap fields are local calendar-day arithmetic only.
- HTTP 500 behavior changes — if contract tests reveal an HTTP 500 discrepancy, fixing
  it requires a separate approved implementation step, not Phase 8D documentation work.
- New application code changes of any kind — Phase 8D is documentation-only (plus
  optional structural tests). Any discovered discrepancy that requires a code fix is
  deferred to a separate approval.

---

## 6. Proposed Decisions

The following decision IDs are drafted for review. They are **not appended to
`DECISIONS.md`** and will not be until explicit human instruction is given.
They are proposed only.

---

### Proposed D-087 — Phase 8D boundary: API Contract Documentation selected, Tier 2 only

**Proposed date:** (to be filled on acceptance)
**Decision:** Phase 8D implements API contract documentation only, within Tier 2.
Specifically: a `docs/API_CONTRACT.md` file documenting the JSON response shape for
`GET /health`, `GET /reports/daily`, and `GET /reports/weekly`, including all Phase 7B
base fields, all Phase 8A `data_quality` and `ticker_quality` fields, all Phase 8C
gap diagnostic fields, the HTTP 422 error response shape (D-060), and the HTTP 200
empty-data scenario. Example JSON payloads for four representative scenarios are included.
An optional companion set of structural integration tests in `backend/tests/integration/`
asserts required key presence, field types, and error status codes. No new API routes.
No application code changed. No new dependencies.
**Options considered:** Candidate B (CSV import diagnostics — deferred), Candidate C
(local data flow documentation — deferred as follow-on), Candidate D (API error taxonomy —
adopted as documentation companion, not standalone phase).
**Rationale:** Candidate A was explicitly deferred from both Phase 8B and Phase 8C pending
response shape stabilisation. Phase 8C acceptance closes that deferral: all planned
Phase 8 analytical fields are now accepted. Documenting the shape now locks it in before
any future phase adds more fields. Documentation-only variant has zero implementation risk.

---

### Proposed D-088 — Phase 8D documentation scope: all Phase 7B–8C response fields covered

**Proposed date:** (to be filled on acceptance)
**Decision:** `docs/API_CONTRACT.md` covers the following for each route:
- `GET /health`: response shape, status codes.
- `GET /reports/daily` and `GET /reports/weekly`: all top-level keys (sections,
  journal_entries, data_quality); nested `DataQualitySummary` fields
  (report_date, total_holding_count, priced_holding_count, unpriced_holding_count,
  coverage_ratio, unpriced_tickers, ticker_quality); nested `TickerQuality` fields
  including all Phase 8C gap fields (local_price_date_count_on_or_before_report_date,
  largest_price_date_gap_days, largest_price_date_gap_start, largest_price_date_gap_end);
  `ReportSection` fields (label, body); `JournalEntry` fields.
Each field entry states: key name, JSON type, nullable/required status, introducing phase.
The document does not prescribe future fields — it describes the accepted schema only.
**Rationale:** Complete field coverage makes the document authoritative. Partial coverage
(e.g., omitting gap fields) would require a revision whenever a consumer encounters an
undocumented field. Scoping to accepted fields only keeps the document honest.

---

### Proposed D-089 — Phase 8D example payloads: four representative scenarios

**Proposed date:** (to be filled on acceptance)
**Decision:** `docs/API_CONTRACT.md` includes four representative JSON response examples
for `GET /reports/daily`:
- Scenario 1: Zero holdings — `total_holding_count: 0`, empty `ticker_quality`,
  `unpriced_holding_count: 0`, no "Data Quality Caveat" section.
- Scenario 2: All holdings priced, no alerts fired — `coverage_ratio: 1.0`, all
  `ticker_quality` entries have `has_price_on_or_before_report_date: true`, gap fields
  populated, no caveat section, no fired alert.
- Scenario 3: One or more holdings unpriced — `unpriced_holding_count > 0`, "Data
  Quality Caveat" section present in the sections list, gap fields null for the unpriced
  ticker (no price records).
- Scenario 4: One or more alerts fired — an alert entry in the "Alert Summary" section
  body shows `FIRED` status, measured value, and threshold.
Examples are illustrative (not generated by the live system) and are clearly marked as
such in the document. They use synthetic ticker names and date values.
**Rationale:** Concrete examples make abstract field descriptions unambiguous. The four
scenarios cover the conditional branches in the system (priced/unpriced, alert fired/not
fired) so that a consumer can reason about which fields are always present and which
are conditional.

---

### Proposed D-090 — Phase 8D optional contract tests: structural invariant assertions

**Proposed date:** (to be filled on acceptance)
**Decision:** If the human owner approves the optional contract test component of
Candidate A, the following integration tests are added under
`backend/tests/integration/test_api_contract.py`:
- Top-level key presence: `sections`, `journal_entries`, `data_quality` present in both
  route responses for a valid request.
- `data_quality` non-null and contains `ticker_quality`, `total_holding_count`,
  `priced_holding_count`, `unpriced_holding_count`, `coverage_ratio`, `unpriced_tickers`.
- Each `ticker_quality` element contains all Phase 8C gap fields:
  `local_price_date_count_on_or_before_report_date`, `largest_price_date_gap_days`,
  `largest_price_date_gap_start`, `largest_price_date_gap_end`.
- HTTP 422 for missing `report_date` parameter.
- HTTP 422 for invalid `report_date` format (non-ISO-8601 string).
- HTTP 422 for `week_start` after `report_date` on weekly route.
- HTTP 422 error body contains keys: `error`, `field`, `value`, `message`.
All tests use the existing in-memory test database and TestClient patterns. No new
infrastructure. These tests verify current behavior and serve as regression guards.
**Rationale:** Contract tests convert documentation from a description into an enforced
specification. Consistent with the companion-hardening pattern established in Phase 8B
(architecture invariant companion) and Phase 8C (adapter boundary tests companion).

---

### Proposed D-091 — Phase 8D architecture invariant: no new invariant tests required

**Proposed date:** (to be filled on acceptance)
**Decision:** Phase 8D introduces no new application modules and no new inter-layer
dependencies. The architecture invariant test count remains at 12 (3 original + 3
Phase 8A + 2 Phase 8B + 4 Phase 8C). No new invariant tests are added in Phase 8D.
Optional contract tests (D-090) are structural integration tests, not architecture
invariant tests, and do not count toward the invariant total.
If the optional contract test file `test_api_contract.py` is added, it is placed under
`backend/tests/integration/` (consistent with existing integration tests) and is
distinct from `backend/tests/architecture/`.
**Rationale:** The architecture invariant tests enforce forbidden import patterns and
module-level constraints. Phase 8D adds only documentation and optional structural
tests — no new import patterns or module-level rules are introduced. Extending the
invariant count without a corresponding new rule would create false coverage.

---

### Proposed D-092 — Phase 8D test gate

**Proposed date:** (to be filled on acceptance)
**Decision:** Phase 8D implementation (documentation-only variant) is accepted when:
(a) `python -m pytest backend/tests/` returns 701 passed, 0 skipped (unchanged — no new
tests for the documentation-only variant); and (b) `docs/API_CONTRACT.md` is present and
covers all fields defined in §3 of D-088.
If the optional contract tests from D-090 are also implemented, the accepted count is
701 + N where N is the number of new contract tests, with 0 skipped. The contract test
count N must be reported in the acceptance commit message.
Architecture invariant total remains at 12 (D-091).
**Rationale:** Consistent with the per-phase test gate established across Phases 2–8C.
The documentation-only path has no new tests and therefore no change to the test count.
The optional test path adds deterministic contract assertions with no infrastructure
requirements, consistent with D-090.

---

## 7. Acceptance Criteria for This Planning Step

This document is accepted as a planning artefact when all of the following hold:

- [x] `docs/PHASE8D_CANDIDATE_PLAN.md` is written and committed.
- [x] No application code has been written or modified.
- [x] No dependencies have been added to `pyproject.toml`.
- [x] No modules under `backend/app/` have been changed.
- [x] No test files have been modified.
- [x] `DECISIONS.md` has not been modified (proposed D-087 through D-092 are not yet appended).
- [x] 701 tests pass with 0 skipped.
- [x] Architecture invariant is green (12 tests).
- [x] Phase 8D implementation remains not approved.

Phase 8D implementation is approved only when:

1. The human owner reviews and accepts the recommended scope (§4) or selects an
   alternative from §3.
2. Proposed decisions D-087 through D-092 (or a subset) are explicitly directed to be
   appended to `DECISIONS.md` with dates filled in.
3. An explicit implementation prompt is issued.

---

*This document is a planning artefact. It does not approve Phase 8D implementation.
It does not modify any application module. It does not introduce any dependency.
It records the approved boundary, candidate options, recommended narrow scope, and
proposed decision text so the human owner can issue a precise implementation approval
when ready.*
