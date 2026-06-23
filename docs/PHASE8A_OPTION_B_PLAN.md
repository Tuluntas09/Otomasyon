# PHASE8A_OPTION_B_PLAN.md

> **This is a planning document only.**
> Phase 8A is not implementation approval. No application code may be written,
> no dependencies added, and no modules changed until a separate, explicit human
> approval is recorded in `DECISIONS.md`.
>
> This document records the human decision to approve **Option B** from
> `docs/PHASE8_GATE_PLAN.md` and defines the planning scope for richer local
> analytics within Tier 2.

---

## 1. Purpose

Phase 8A is the planning phase for **Option B — richer local analytics within Tier 2**.

It does not involve:
- Paper trading (Tier 3 — not approved).
- Simulated orders or execution models (off-roadmap).
- Broker integration or trading credentials (permanently excluded).
- Technical indicators, backtesting, or strategy engines (out of scope).
- External market data APIs (excluded until a ToS gate is separately approved).
- Frontend UI implementation (deferred to a separate phase).

It is a scoping exercise. The output of Phase 8A planning is a locked implementation
scope (one narrow candidate), a set of accepted decision entries, and an explicit
implementation prompt that can be separately approved before any code is written.

Otomasyon remains what it has always been: a local-first personal finance research and
decision-support instrument. Phase 8A does not change that identity.

---

## 2. Approved Boundary

### What Option B allows

- New pure metric functions using data already in the local SQLite database.
- New or extended `ReportSection` content in daily/weekly reports.
- New read-only API routes (GET-only) for additional computed facts.
- New test coverage for any new metrics or routes.
- Documentation updates reflecting new capabilities.
- All system-generated text continues to pass `check_compliance` before use.
- All new computation functions must be pure: no I/O, no system clock, no side effects.
- All new API routes must be read-only (GET-only). No write endpoints.
- All data access must go through the `DataAdapter` boundary.

### What Option B forbids

- Any execution-adjacent abstraction (order, fill, trade, signal, position open/close).
- Any broker abstraction, credential, or API client.
- Any paper trading or simulated P&L tracking.
- Any technical indicator (moving average, RSI, MACD, Bollinger, etc.).
- Any backtesting or historical strategy evaluation.
- Any external market-data fetch or web scraping.
- Any scheduler, cron trigger, or push notification.
- Any multi-currency aggregation (unless separately approved with a new decision).
- Any multi-portfolio support (unless separately approved with a new decision).
- Any new runtime dependencies without a dedicated decision entry.
- Any language in system-generated output that implies advice, recommendation,
  or predicted outcomes (`buy`, `sell`, `hold`, `profit`, `opportunity`, `target`).
- Any frontend UI work (deferred).

### Project posture confirmation

Otomasyon remains:
- **Read-only** — the system computes and displays; it does not act.
- **Local-first** — all data resides in the local SQLite database; no external calls.
- **Advisory-free** — no system-generated output implies a course of action.
- **Execution-free** — no code path leads to placing, simulating, or recording an order.

---

## 3. Candidate Analytics Improvements

The following candidates are descriptive only. None is approved for implementation here.
Each requires a decision entry before coding begins.

### 3.1 Data Quality Analytics

| Candidate | Description |
|---|---|
| Coverage depth report | For each held ticker, report how many days of price history exist in the local DB, the earliest and latest price dates, and any gaps larger than N calendar days. |
| Unpriced ticker summary | Extend the existing `unpriced_tickers` field into a structured section: which tickers are held but lack any price, and how long they have been unpriced based on when they were first added. |
| Price freshness indicator | Report the staleness of the most recent price per ticker (days since last recorded close) so the user knows which positions may be operating on outdated data. |
| CSV import error history | Persist row-level import errors from `ImportResult.errors` to a dedicated table so the user can review past import failures without re-running the import. |

### 3.2 Portfolio Composition Analytics

| Candidate | Description |
|---|---|
| Position contribution to drawdown | For each held ticker with price history, compute how much of the portfolio-level drawdown (M-005) is attributable to that position based on its weight and individual price decline from peak. |
| Position contribution to volatility | Similar to above for M-006: report each position's proportional contribution to the overall volatility proxy. |
| Concentration history | Track how the top-N concentration ratio (currently CONC-001's single-ticker measure) has changed over time using stored price history. |
| Watchlist vs. held gap | Report tickers present in the watchlist but not in holdings (and vice versa), with coverage status if prices exist for watchlist-only tickers. |

### 3.3 Historical Local-Price Analytics

| Candidate | Description |
|---|---|
| Extended drawdown windows | Compute drawdown (M-005) over 60-day and 90-day windows in addition to the current 30-day window, using the price history already in the local DB. |
| Multi-period metric comparison | Compare key metrics (concentration, drawdown, volatility) across two user-supplied date ranges using locally stored prices (e.g., last 30 days vs. prior 30 days). |
| Price history depth summary | Report the total number of daily price records per ticker and the full date range covered, so the user knows which analytics are well-supported by data. |
| Rolling volatility series | Compute M-006 (volatility proxy) over a rolling window and return the series as structured data, showing how volatility has evolved over time rather than a single current value. |

### 3.4 Report Explainability Improvements

| Candidate | Description |
|---|---|
| Alert context section | For each fired alert, include a brief description of what the threshold measures and why the rule exists, drawn from `ALERT_POLICY.md` language. All text compliance-checked. |
| Metric definition footnotes | Add a `ReportSection` that defines each metric used in the report (using language from `METRICS_SPEC.md`) so the report is self-contained and interpretable without external docs. |
| Data quality caveat section | When `unpriced_tickers` is non-empty or coverage ratios are low, include a structured caveat section explaining which metrics are affected and why. |
| Week-over-week delta summary | In the weekly report, include a structured comparison of this week's key metric values against the prior week's, expressed as measured changes (not predictions). |

### 3.5 API Response Clarity

| Candidate | Description |
|---|---|
| Structured metric envelope | Add a top-level `metrics` object to the API response with key metric values in a flat, easily parseable structure, separate from the narrative `sections` array. |
| Data quality metadata | Include a top-level `data_quality` object in the API response reporting coverage ratios, unpriced ticker count, and price freshness per ticker. |
| Alert summary array | Add a top-level `alerts` array (separate from the embedded report section) for programmatic consumption — each entry with `rule_id`, `fired`, `severity`, `metric_value`, `threshold`. |
| Error detail schema | Standardise the 422 error response body across all routes into a consistent schema: `{error, field, value, message}`. |

### 3.6 Test and Documentation Hardening

| Candidate | Description |
|---|---|
| Architecture invariant extension | Add assertions to `test_no_broker_no_execution.py` covering new modules added in Phase 8A, to ensure the boundary holds as the codebase grows. |
| Boundary test for new metrics | Verify that any new metrics module imports no forbidden dependencies (same pattern as Phase 4's boundary tests). |
| API contract tests | Add explicit tests for response shape (required keys, types) so that API structure regressions are caught at the test level, not discovered by callers. |
| ROADMAP.md and PROJECT_BRAIN.md updates | Keep documentation current with any new capabilities approved in Phase 8A. |

---

## 4. Recommended Phase 8A Scope

**Recommendation: Data Quality Analytics — Coverage Depth and Price Freshness Reporting**

Specifically:

1. **Price history depth summary** — per-ticker count of daily price records, earliest date,
   latest date, and days-since-last-price, computed from locally stored data.
2. **Data quality metadata in API response** — a top-level `data_quality` object in
   `GET /reports/daily` and `GET /reports/weekly` responses with per-ticker coverage and
   freshness, plus portfolio-level coverage ratio.
3. **Data quality caveat section in reports** — a `ReportSection` (compliance-checked)
   describing which tickers are unpriced or have stale data, and which metrics are affected.

**Rationale for this selection:**

- **Lowest boundary risk.** This extends the existing metrics output format without
  introducing any new analytical domain. It uses only data already stored in the local DB.
- **Pure functions.** All new computation takes holdings and price records as arguments;
  no I/O, no system clock, no external calls. Consistent with D-030.
- **Immediate practical value.** Users currently cannot easily tell whether their computed
  metrics are well-supported by data. A coverage and freshness summary directly improves
  the interpretability of existing outputs.
- **No compliance-guard risk.** Coverage and freshness language is purely descriptive:
  "N days of price history available", "last recorded price: YYYY-MM-DD". No forbidden
  terms are required.
- **Completes naturally with the existing test pattern.** New pure functions follow the
  same test structure as Phase 4 (44 unit tests, no DB fixtures). New API fields follow
  the same test structure as Phase 7B.
- **Does not prejudge any future scope.** It extends what exists without opening a door
  toward execution, simulation, or advisory content.

---

## 5. Out-of-Scope List

The following are explicitly excluded from Phase 8A and from Option B generally.
They may not be introduced without a new gate review and explicit human approval.

| Category | Excluded items |
|---|---|
| Simulation | Paper trading, simulated orders, fill simulation, position open/close lifecycle |
| Execution | Broker abstraction, trading credentials, order placement (real or simulated) |
| Signals | Trading signals, buy/sell recommendations, target prices, opportunity identification |
| Indicators | Moving averages, RSI, MACD, Bollinger bands, any technical indicator |
| Backtesting | Historical strategy evaluation, strategy performance metrics, P&L reconstruction |
| External data | Market data APIs, web scraping, news feeds, earnings calendars |
| Automation | Scheduler, cron trigger, push notifications, email, webhooks |
| Scope expansion | Multi-currency aggregation, multi-portfolio (each requires its own gate) |
| Frontend | React/Vite UI development (deferred; the empty shell remains unchanged) |
| Advisory output | Any system-generated text implying action, recommendation, or predicted outcome |

---

## 6. Proposed Decisions

The following decision IDs are drafted for review. They are **not appended to `DECISIONS.md`**
and will not be until explicit human instruction is given. They are proposed only.

---

### Proposed D-067 — Phase 8A boundary: Option B approved, Tier 2 only

**Proposed date:** (to be filled on acceptance)
**Decision:** Phase 8A implements richer local analytics within Tier 2 only, per Option B
from `docs/PHASE8_GATE_PLAN.md`. No Tier 3 (paper trading), Tier 4 (live trading), or any
execution-adjacent feature is approved. The selected narrow scope for Phase 8A
implementation is: data quality analytics — coverage depth summary, price freshness
reporting, data quality metadata in API responses, and data quality caveat sections in
reports.
**Options considered:** Option A (stay read-only, no change), Option C (Tier 3 research),
Option D (reject/defer).
**Rationale:** Option B extends analytical depth without crossing any safety boundary.
Data quality analytics are the lowest-risk, highest-value improvement available within
the existing architecture.

---

### Proposed D-068 — Phase 8A purity constraint: new metric functions are pure

**Proposed date:** (to be filled on acceptance)
**Decision:** All new computation functions added in Phase 8A must satisfy the same purity
invariant as the metrics engine (D-030): no I/O, no system clock, no environment variables,
no persistence imports, no network access. All data arrives as function arguments.
Enforced by boundary import tests in the Phase 8A test file.
**Rationale:** Consistency with the established purity invariant. Pure functions are
testable without fixtures and composable with any future orchestration layer.

---

### Proposed D-069 — Phase 8A compliance constraint: all new generated text is checked

**Proposed date:** (to be filled on acceptance)
**Decision:** All system-generated strings placed in new `ReportSection` labels or bodies
must pass `check_compliance()` before construction, consistent with D-054. No new
compliance guard wordlist extensions are required for data quality language (coverage
counts, date strings, ticker names). If any candidate requires new wording that may trigger
the current guard, that wording must be reviewed and the guard extended before the section
is constructed.
**Rationale:** Consistent with D-039 and D-054. The compliance guard must not be bypassed
or silently narrowed for new features.

---

### Proposed D-070 — Phase 8A architecture invariant: extended to cover new modules

**Proposed date:** (to be filled on acceptance)
**Decision:** `backend/tests/architecture/test_no_broker_no_execution.py` must be extended
to assert that any new modules added in Phase 8A (e.g., `backend/app/metrics/quality.py`
or similar) do not import forbidden modules and do not contain forbidden source terms.
The invariant test must be updated before or alongside any new module being created, not after.
**Rationale:** Consistent with the architecture-first principle established in Phase 1.
The invariant test must grow with the codebase.

---

### Proposed D-071 — Phase 8A API: new fields are GET-only, DataAdapter-routed

**Proposed date:** (to be filled on acceptance)
**Decision:** Any new API fields or routes added in Phase 8A are GET-only. All data access
goes through `SQLiteDataAdapter` (or a new `DataAdapter` abstract method if required).
No direct persistence repository imports in route modules, consistent with D-066.
No write endpoints are introduced.
**Rationale:** Consistent with D-058 (Phase 7B API boundary). The read-only, adapter-routed
pattern is an established invariant.

---

### Proposed D-072 — Phase 8A test gate: unit tests required before merge

**Proposed date:** (to be filled on acceptance)
**Decision:** Phase 8A implementation is not accepted until:
- All new pure metric functions have unit tests with no DB fixtures.
- All new API fields have integration tests asserting their presence, type, and shape.
- Architecture invariant test is updated to cover new modules.
- Total test count exceeds the Phase 7B baseline of 500 passed, 0 skipped.
**Rationale:** Consistent with the per-phase test gate established across Phases 2–7B.

---

### Proposed D-073 — Phase 8A dependencies: no new runtime dependencies

**Proposed date:** (to be filled on acceptance)
**Decision:** Phase 8A introduces no new runtime dependencies. `pyproject.toml`
`dependencies` remains `["fastapi>=0.100.0"]`. All new computation uses Python stdlib only
(`statistics`, `datetime`, `collections`). If a future candidate requires a third-party
library, a dedicated decision entry is required before it is added.
**Rationale:** Consistent with D-024 (stdlib-only CSV) and the zero-dependency policy
maintained through Phases 2–7B.

---

### Proposed D-074 — Phase 8A data quality result format

**Proposed date:** (to be filled on acceptance)
**Decision:** Data quality results are expressed as a new frozen dataclass
(`DataQualitySummary` or similar) under `backend/app/metrics/`. Fields include:
per-ticker price record count, earliest price date, latest price date, days since last
price (computed from `report_date`, not system clock), and portfolio-level coverage ratio.
`DataQualitySummary` is returned by a new pure function and included in the
`DailyReport` / `WeeklyReport` dataclasses as an additional field, or surfaced via the
API as a top-level `data_quality` key via `dataclasses.asdict()`.
**Rationale:** Consistent with the frozen-dataclass result pattern established in Phases
4–7A. Caller-provided date (not system clock) maintains D-031 and D-056.

---

## 7. Acceptance Criteria for Phase 8A Planning (This Document)

This document is accepted as a planning artifact when all of the following hold:

- [ ] `docs/PHASE8A_OPTION_B_PLAN.md` is written and committed.
- [ ] No application code has been written or modified.
- [ ] No dependencies have been added to `pyproject.toml`.
- [ ] No modules under `backend/app/` have been changed.
- [ ] No test files have been modified.
- [ ] `DECISIONS.md` has not been modified (proposed D-067 through D-074 are not yet appended).
- [ ] All 500 tests pass with 0 skipped.
- [ ] Architecture invariant is green.
- [ ] Phase 8A implementation remains not approved.

Phase 8A implementation is approved only when:

1. The human owner reviews and accepts the recommended narrow scope (§4) or selects an
   alternative from §3.
2. Proposed decisions D-067 through D-074 (or a subset) are explicitly directed to be
   appended to `DECISIONS.md` with dates filled in.
3. An explicit implementation prompt is issued.

---

## 8. Next Implementation Prompt Preview

When Phase 8A implementation is approved, the implementation prompt would cover
approximately the following (subject to final scope approval):

**New module:** `backend/app/metrics/quality.py`
- Pure function: `compute_data_quality(holdings, price_records, report_date)` → `DataQualitySummary`
- Frozen dataclass: `DataQualitySummary` with per-ticker `TickerQuality` entries and
  portfolio-level `coverage_ratio`.
- No I/O, no system clock (report_date is caller-provided), no forbidden imports.
- Boundary import test added to architecture invariant.

**Updated report models:** `backend/app/reports/models.py`
- `DailyReport` and `WeeklyReport` gain a `data_quality` field of type `DataQualitySummary`.

**Updated report builder:** `backend/app/reports/builder.py`
- `build_daily_report` and `build_weekly_report` accept `data_quality: DataQualitySummary`
  as an argument.
- New `ReportSection` — "Data Quality Summary" — generated from `DataQualitySummary`,
  compliance-checked before construction.

**Updated API orchestration:** `backend/app/api/routes/reports.py`
- Call `compute_data_quality(holdings, prices, report_date)` in the orchestration sequence.
- Pass result to builder.
- `dataclasses.asdict()` propagates it to the JSON response as `data_quality`.

**New tests:**
- `backend/tests/unit/test_data_quality.py` — unit tests for `compute_data_quality`; no
  DB fixtures; covers zero-holding, all-unpriced, partial-coverage, and full-coverage cases.
- Extended `backend/tests/integration/test_api_reports.py` — assert `data_quality` key
  present, correct type, and reflects seeded data.
- Extended architecture invariant — assert `metrics.quality` imports no forbidden modules.

**Documentation updates:**
- `ROADMAP.md` Phase 8A entry added.
- `PROJECT_BRAIN.md` §5 updated.
- `DECISIONS.md` D-067 through D-074 appended with dates.
- `docs/reports/PHASE8A_CLOSEOUT.md` created on acceptance.

*This preview is illustrative only. It becomes the implementation directive only after
explicit human approval of Phase 8A implementation.*

---

*This document is a planning artifact. It does not approve Phase 8A implementation.
It does not modify any application module. It does not introduce any dependency.
It records the approved boundary, candidate analytics, recommended narrow scope,
and proposed decision text so the human owner can issue a precise implementation
approval when ready.*
