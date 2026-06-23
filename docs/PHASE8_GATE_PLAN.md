# PHASE8_GATE_PLAN.md

> **This is a planning and risk-review document only.**
> Phase 8 is a decision gate, not an implementation approval.
> No application code may be written, no dependencies added, and no modules changed until
> a separate, explicit human approval is recorded in `DECISIONS.md`.

---

## 1. Purpose of Phase 8 Gate

v0.1 is complete and accepted (commit `8e69506`). All six metrics, four alert rules, the
compliance guard, the decision journal, the report builder, and the read-only API are
implemented, tested (500 passed / 0 skipped), and documented.

Phase 8 is not an automatic continuation. It is a deliberate review gate that asks a
single question:

> **Should Otomasyon cross the Tier 2 → Tier 3 boundary, and if so, under what
> constraints?**

The four-tier boundary is defined in `RISK_POLICY.md` and `PROJECT_BRAIN.md §3`:

| Tier | Capability | v0.1 status |
|---|---|---|
| 1 | Compute and display metrics | ✅ implemented |
| 2 | Notify on explainable threshold rules | ✅ implemented |
| 3 | Simulate positions / test hypotheses (non-execution) | ❌ not approved |
| 4 | Place real orders | ❌ off-roadmap |

No work at Tier 3 or above begins until this gate is reviewed and a dated `DECISIONS.md`
entry is written and accepted by the human owner.

---

## 2. Current v0.1 Baseline

The following capabilities exist and are accepted. This is the foundation from which any
Phase 8 work would extend.

| Capability | Detail |
|---|---|
| Data ingestion | CSV import — holdings, watchlist, EOD prices; all-or-nothing for portfolio data, row-level for prices |
| Persistence | SQLite via `OTOMASYON_DB_PATH`; idempotent schema init; repositories for holdings, watchlist, prices, journal entries |
| Metrics | M-001 market value, M-002 position weights, M-003 unrealised change, M-004 coverage ratio, M-005 drawdown from peak, M-006 30-day return volatility proxy |
| Alerts | CONC-001 concentration, DD-001 drawdown, VOL-001 volatility, COV-001 coverage; strict `>` threshold; all results (fired + non-fired) returned |
| Compliance guard | Hard chokepoint on all system-generated text; raises on any forbidden term; never rewrites; user-authored text is exempt |
| Decision journal | Append-only; user text stored and returned verbatim; UTC timestamps; no compliance scan on user fields |
| Reports | Daily and weekly frozen-dataclass reports; all alert results embedded; journal entries carried separately |
| Read-only API | `GET /health`, `GET /reports/daily`, `GET /reports/weekly`; HTTP 422 on invalid dates; no write routes |

**Explicit v0.1 exclusions (remain in force unless overturned by a new decision):**

- No broker integration
- No order placement (real or simulated)
- No write API routes
- No external market data providers
- No scheduler or cron trigger
- No push notifications or email
- No data export
- No multi-currency aggregation
- No multi-portfolio
- No backtesting
- No technical indicators
- No paper trading
- No live trading
- No frontend beyond the React/Vite empty shell

---

## 3. Risk Review

Before any Phase 8 scope is approved, the following risks must be evaluated and mitigated.

### 3.1 Advisory-Language Risk

Any feature that simulates positions, hypothetical outcomes, or projected values carries the
risk of producing text that reads like investment advice. Even a "paper" result such as
"simulated gain of X%" uses language the compliance guard forbids (`profit`, `opportunity`,
implied recommendation). Every new system-generated string would need to pass `check_compliance`
— and the current wordlist may need extension before Tier 3 text can be expressed safely.

**Mitigation required:** Extend the compliance guard wordlist under a new decision entry
before any Tier 3 text is generated. All Tier 3 output must describe measured simulation
facts, never prescribe action.

### 3.2 Execution-Boundary Risk

The architecture invariant test (`test_no_broker_no_execution.py`) blocks broker integration
and execution logic at the import-graph and source-text level. Any paper-trading layer that
introduces execution-shaped abstractions — even named "simulated order", "fill", "position
open" — risks eroding the invariant and making the boundary harder to defend as the
codebase grows.

**Mitigation required:** The invariant test must be extended before any Tier 3 module is
created, not after. The naming convention for Tier 3 concepts must be explicitly constrained
(e.g., "scenario", "hypothesis position") and documented in a decision entry.

### 3.3 Scope Creep Risk

Paper trading research is a broad phrase. Without a locked, narrow scope defined before
implementation begins, Tier 3 work tends to expand: scenario analysis → P&L tracking →
trade history → broker adapter → live trading. Each step can feel like a small incremental
extension.

**Mitigation required:** The Phase 8 implementation scope must be explicitly bounded before
a single line of code is written. The decision entry must enumerate what is in scope, what
is explicitly out of scope, and which future features would require another gate.

### 3.4 Dependency Risk

Tier 3 features may create pressure to introduce numeric or financial libraries (`numpy`,
`pandas`, `scipy`, `pyfolio`, `zipline`, or any market-data client). v0.1 dependencies are
intentionally zero (`dependencies = []` in `pyproject.toml`). Any new dependency must be
justified by a decision entry and assessed for ToS implications if it fetches external data.

**Mitigation required:** `pyproject.toml` changes require a dedicated decision entry naming
the library, its purpose, and the alternatives considered.

### 3.5 Testing Risk

Simulation logic is harder to test deterministically than pure metrics because it involves
sequences of hypothetical events over time. Without a strict test boundary defined upfront,
simulation tests may depend on system time, mutable state, or ordering assumptions.

**Mitigation required:** Any Tier 3 module must be pure (no I/O, no system clock) by
design, following the same purity invariant as the metrics engine (D-030). Test gates
and minimum test counts must be established before implementation is approved.

### 3.6 User-Safety Risk

The tool's identity — stated in `PROJECT_BRAIN.md §0` — is a "personal finance research
and decision-support instrument, NOT a trading bot." Adding simulation outputs risks users
treating hypothetical results as performance signals or trading guidance, even if no such
advice is intended or generated.

**Mitigation required:** Any Tier 3 feature must carry an explicit disclaimer in every
output path. The disclaimer text must itself pass `check_compliance`. The `RISK_POLICY.md`
must be updated with Tier 3-specific safety language before implementation begins.

---

## 4. Boundary Options

The following options are presented for human review. No option is selected here; selection
requires an explicit decision entry.

### Option A — Stay at Tiers 1 + 2 (no Phase 8 implementation)

Extend v0.1 capabilities within the existing tier: richer metrics, additional alert rules,
improved report formatting, data quality reporting, or watchlist analytics. No Tier 3
boundary crossing.

**What stays the same:** All current invariants. No new execution-adjacent abstractions.
No new dependencies. Architecture invariant unchanged.

**Tradeoff:** No simulation capability. Hypothetical scenario testing (e.g., "what would
my concentration look like if I reduced position X?") is not possible.

### Option B — Richer local analytics without simulation

Add deeper read-only analytics within Tier 2: rolling performance attribution, longer
drawdown windows, multi-period comparisons, position contribution analysis, data quality
dashboards, or watchlist vs. held position gap analysis. No hypothetical position simulation.

**What changes:** New metrics functions, new report sections, new API routes (read-only).
All system-generated text continues through the compliance guard unchanged.

**Tradeoff:** Provides more analytical depth without crossing the Tier 3 boundary. Does not
answer the question of whether hypothetical scenarios can be tested.

### Option C — Tier 3 research layer (non-execution, non-broker, non-advisory simulation)

Add a narrow, bounded "scenario" or "hypothesis" module that allows the user to supply a
hypothetical set of position changes (not orders) and see how computed metrics would differ.
No broker, no execution, no signals, no external data. The module computes the same metrics
(M-001–M-006) against a user-supplied alternate position set.

**Constraints that must hold if this option is chosen:**

- No execution model, no order abstraction, no fill simulation.
- No external market data; user supplies prices via existing CSV path.
- No buy/sell/hold/profit language in any system-generated output.
- All generated text passes `check_compliance` (wordlist extension required first).
- Architecture invariant test must be extended to cover Tier 3 naming conventions.
- `RISK_POLICY.md` and `PROJECT_BRAIN.md` must be updated before code is written.
- Scenarios are described as "hypothesis positions", never "trades" or "orders".
- Results are described as "computed metrics for the supplied hypothesis", never
  "expected returns" or "simulated gains".

**Tradeoff:** Expands research capability meaningfully. Requires careful naming discipline
and invariant extension. Risk of scope creep is real and must be actively managed.

### Option D — Reject Phase 8 for now; revisit after v0.2 planning

Defer the Tier 3 question entirely. Close Phase 8 as "not applicable to current scope."
Start v0.2 planning from the v0.1 baseline with a fresh scope review.

**What changes:** Nothing. v0.1 remains the active baseline.

**Tradeoff:** No simulation capability. Preserves the cleanest possible safety posture.
Avoids any risk of Tier 3 boundary erosion. May be revisited when the user has a specific,
bounded research need that Tiers 1 + 2 cannot satisfy.

---

## 5. Recommended Safe Next Step

**Recommendation: Option B — richer local analytics within Tier 2.**

The v0.1 metrics engine and report builder have headroom for meaningful analytical depth
that does not require crossing the Tier 3 boundary. Concrete examples within the current
safety posture:

- Longer drawdown windows (60-day, 90-day) using existing price history.
- Position contribution analysis: which holdings drive portfolio-level drawdown or volatility.
- Watchlist gap analysis: tickers watched but not held, with metric stubs if prices exist.
- Data quality summary: coverage ratios, unpriced ticker counts, price history depth.
- Multi-period report comparison: daily vs. prior period summary (computed from stored data).

These extend analytical value without any new execution-adjacent abstraction, any new
dependency, or any Tier 3 boundary crossing. They are expressible entirely within the
existing architecture and comply with all current invariants.

If and when a specific hypothesis-testing need arises that Option B cannot satisfy, Option C
can be revisited with a concrete, narrow scope defined at that time.

This recommendation does not constitute investment advice, trading guidance, or a suggestion
to take any action with respect to any financial instrument.

---

## 6. Acceptance Criteria for Phase 8 Planning (This Document)

This document is accepted as a planning artifact when all of the following hold:

- [ ] `docs/PHASE8_GATE_PLAN.md` is written and committed.
- [ ] No application code has been written or modified.
- [ ] No dependencies have been added to `pyproject.toml`.
- [ ] No modules under `backend/app/` have been changed.
- [ ] `DECISIONS.md` has not been modified (proposed decision IDs below are not yet appended).
- [ ] All 500 tests pass with 0 skipped.
- [ ] Architecture invariant is green.
- [ ] Phase 8 implementation remains not approved.

Phase 8 implementation is approved only when:

1. The human owner selects one of the four boundary options above.
2. A dated `DECISIONS.md` entry (D-067 or later) is written and accepted, naming the
   selected option, its explicit scope, its explicit exclusions, and its acceptance criteria.
3. Any required prerequisite steps (compliance wordlist extension, invariant test extension,
   `RISK_POLICY.md` update) are completed and accepted before code is written.

---

## 7. Required Decisions

The following decision IDs are reserved for Phase 8. They are **not yet appended to
`DECISIONS.md`** and will not be until the human owner explicitly approves Phase 8 and
directs their addition.

| Proposed ID | Question to resolve before Phase 8 can be approved |
|---|---|
| D-067 | Which boundary option (A / B / C / D) is selected? What is the explicit in/out scope? |
| D-068 | If Option C: what naming conventions govern Tier 3 concepts? What terms are prohibited? |
| D-069 | If Option C: what extensions to the compliance guard wordlist are required before Tier 3 text can be generated? |
| D-070 | If Option C: what extensions to the architecture invariant test are required before any Tier 3 module is created? |
| D-071 | If Option B or C: which new metrics or analytics are in scope? What are their purity constraints? |
| D-072 | If Option B or C: what new API routes (if any) are required, and are they all GET-only read operations? |
| D-073 | If any option adds dependencies: which library, for what purpose, and what alternatives were considered? |
| D-074 | What is the minimum test count gate and test structure requirement for the Phase 8 implementation? |

**These are open questions, not decisions.** They become decisions only when answered,
dated, and appended to `DECISIONS.md` by explicit human instruction.

---

*This document is a planning artifact. It does not approve Phase 8 implementation.
It does not modify any application module. It does not introduce any dependency.
It records the gate conditions and risk landscape so the human owner can make a deliberate,
informed choice about the next phase of the project.*
