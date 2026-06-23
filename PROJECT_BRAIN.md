# PROJECT_BRAIN.md

> **The single source of orientation for this project.** Read this first — whether you
> are a human contributor or an AI agent. It is the map and the constitution. It does
> not replace the detailed docs in `docs/`; it points to them and encodes the rules that
> must never be broken. When this file and a detailed doc disagree on a *rule*,
> `RISK_POLICY.md` wins; on a *detail*, the specific doc wins. Keep this file in sync
> when decisions change.

---

## 0. One-line truth

**This is a personal finance research and decision-support instrument — NOT a trading
bot.** It measures, records, and notifies. It never advises, never trades, never claims
profit.

If anything you are about to do conflicts with that sentence, stop.

---

## 1. What it is / what it is not

**Is:** a local-first tool for one user to (a) see the real risk shape of one portfolio,
(b) record the reasoning behind their own decisions, and (c) receive explainable,
rule-based alerts when measurable thresholds are crossed.

**Is not:** a trading bot, a signal service, an advisor, a broker client, a backtester,
a news engine, or an arbitrage scanner. Profit is treated as an **unproven hypothesis the
system helps test**, never as a promised outcome.

---

## 2. Non-negotiable rules (the invariants)

These hold in every phase. They are enforced by `RISK_POLICY.md`, `ALERT_POLICY.md`, and
the architectural-invariant test.

1. **No order placement** — real or simulated. No broker integration. No trading credentials.
2. **No buy / sell / hold / target-price language** anywhere in system-generated copy.
3. **Alerts describe, never prescribe** — they state which rule/threshold fired, never an action.
4. **No profit / "guaranteed" / "opportunity-to-profit" claims.**
5. **Automation ceiling = read → compute → notify.** Nothing acts on a market.
6. **All system-generated user-facing text passes through the compliance guard.**
7. **The metrics engine is pure** — no I/O, no side effects, deterministic.
8. **All data access goes through the DataAdapter boundary.**
9. **USD only (v0.1).** Non-USD inputs are flagged and excluded, never silently summed.
10. **Single portfolio (v0.1).** Negative quantities and duplicate tickers are rejected on input.
11. **Tier promotions are deliberate** — moving up the four-tier ladder requires a logged
    `DECISIONS.md` entry, never a default or a convenience.

> Not investment advice. The user is solely responsible for their own decisions.

---

## 3. The four-tier boundary

| Tier | Capability | In v0.1? |
|---|---|---|
| 1. Analysis | Compute & display metrics | ✅ |
| 2. Alerting | Notify on explainable threshold rules | ✅ |
| 3. Paper trading | Simulate positions/P&L to test hypotheses | ❌ research only (Phase 8) |
| 4. Live trading | Place real orders | ❌ off-roadmap |

**v0.1 = Tiers 1 + 2 only.** Information flows up one tier at a time, by conscious decision.

---

## 4. v0.1 scope at a glance

**In:** watchlist · single-portfolio input · EOD price ingestion (CSV first) ·
risk/exposure metrics · decision journal · explainable threshold alerts · daily/weekly reports.

**Out (postponed or off-roadmap):** live trading · paper trading · broker APIs · ML trade
decisions · news scraping · arbitrage · hybrid systems · complex backtesting · technical
indicators · BIST/crypto/FX adapters · multi-portfolio · multi-currency aggregation ·
auth/cloud/deployment.

Full detail: `docs/MVP_SCOPE.md`.

---

## 5. Current status

- **Phase 0 (docs):** ✅ accepted. All `docs/` files present.
- **Phase 1 (empty skeleton):** ✅ complete. Git repo initialised. Repo boundaries, README,
  pytest harness, and the one substantive test (no-broker/no-execution invariant) exist and
  pass.
- **Phase 2 (data model + local storage):** ✅ **complete.** Domain models (`Holding`,
  `WatchlistEntry`, `PriceRecord`), typed exceptions, validation helpers, SQLite schema,
  and three repositories (`HoldingsRepo`, `WatchlistRepo`, `PricesRepo`) implemented.
  `DataAdapter` ABC defined. Decisions D-020 through D-023 recorded.
- **Phase 3 (CSV data adapter):** ✅ **complete.** `SQLiteDataAdapter` (concrete DataAdapter),
  `import_holdings_csv`, `import_watchlist_csv`, `import_prices_csv` implemented.
  All-or-nothing for holdings/watchlist with DB duplicate pre-check. Row-level error
  collection for prices. `178 passed, 0 skipped` — architecture invariant green.
  Decisions D-024 through D-029 recorded.
- **Phase 4 (metrics engine):** ✅ **complete.** Pure metrics engine implemented under
  `backend/app/metrics/`. `compute_portfolio_snapshot` (M-001 through M-004),
  `compute_drawdown` (M-005), `compute_volatility_proxy` (M-006). All window calculations
  use latest input price date (not system date). Coverage ratios reported. No forbidden
  imports. `222 passed, 0 skipped` — architecture invariant green.
  Decisions D-030 through D-035 recorded.
- **Phase 5 (alerts + compliance guard):** ✅ **complete.** Compliance guard
  (`check_compliance`, `ComplianceViolation`, `ComplianceViolationError`) implemented
  under `backend/app/compliance/`. Alert engine (`evaluate_alerts`, `AlertConfig`,
  `AlertResult`) implemented under `backend/app/alerts/`. Four rules: CONC-001, DD-001,
  VOL-001, COV-001. Strict greater-than threshold comparison throughout. Every explanation
  passes compliance before `AlertResult` construction. `313 passed, 0 skipped` —
  architecture invariant green. Decisions D-036 through D-043 recorded.
- **Phase 6 (decision journal):** ✅ **complete.** `JournalEntry` frozen dataclass and
  `validate_new_entry()` implemented under `backend/app/journal/`. `JournalRepo`
  (`add_entry`, `get_all`, `get_by_ticker`) implemented under
  `backend/app/data/persistence/journal_repo.py`. `journal_entries` DDL added to `db.py`
  (idempotent). `JournalValidationError` added to `exceptions.py`. Compliance guard is
  NOT applied to user-authored journal text — fields stored verbatim. `created_at` uses
  UTC: `datetime.now(timezone.utc).isoformat()`. `358 passed, 0 skipped` — architecture
  invariant green. Decisions D-044 through D-050 recorded.

- **Phase 7A (report builder):** ✅ **complete.** Pure report builder implemented under
  `backend/app/reports/`. `ReportSection`, `DailyReport`, `WeeklyReport` frozen dataclasses.
  `build_daily_report`, `build_weekly_report` builder functions. No I/O, no DB, no system
  clock. Every system-generated `ReportSection` label/body passes `check_compliance()`.
  Journal entries carried verbatim in `journal_entries`; compliance guard NOT applied to
  user-authored fields. All evaluated alerts (fired and non-fired) included. `week_start`
  must be ≤ `report_date`; invalid dates raise `InvalidDateError`. `451 passed, 0 skipped`
  — architecture invariant green. Decisions D-051 through D-057 recorded.

- **Phase 7B (API layer):** ✅ **accepted.** Minimal read-only FastAPI routes implemented
  under `backend/app/api/`. Three routes: `GET /health`, `GET /reports/daily`,
  `GET /reports/weekly`. Per-request SQLite connection via `deps.get_conn()` using D-023
  path policy. Full orchestration: SQLiteDataAdapter → metrics → alerts → report builder →
  `dataclasses.asdict()` → JSON. `DataAdapter` ABC extended with `get_journal_entries
  (date_from, date_to)`; `SQLiteDataAdapter` delegates to `JournalRepo.get_by_date_range()`
  (D-066). No persistence repo imports in route modules. `500 passed, 0 skipped` —
  architecture invariant green. Decisions D-058 through D-066 recorded.

- **Phase 8A (data quality analytics — Option B, Tier 2):** ✅ **accepted.** Pure data
  quality function `compute_data_quality(holdings, price_records, report_date)` implemented
  under `backend/app/metrics/quality.py`. Returns `DataQualitySummary` (portfolio-level
  coverage counts, coverage ratio, unpriced tickers list) and per-ticker `TickerQuality`
  (price record count, earliest/latest dates, days since last price relative to
  caller-provided report_date, has_price_on_or_before_report_date). "Data Quality Summary"
  `ReportSection` added to both daily and weekly reports; all section text compliance-checked.
  `data_quality` exposed as a top-level key in both API responses via `dataclasses.asdict()`.
  Architecture invariant extended with three targeted tests for `metrics/quality.py`.
  `585 passed, 0 skipped` — all invariants green. Decisions D-067 through D-074 recorded.
  No paper trading, no simulated orders, no broker abstraction, no technical indicators,
  no backtesting, no external market data, no scheduler, no notifications introduced.

- **Phase 8B (report explainability + hardening — Option B, Tier 2):** ✅ **accepted.**
  Three new compliance-checked `ReportSection` builders added to
  `backend/app/reports/builder.py`: "Metric Definitions" (M-001 through M-006 in
  fact-stating language), "Alert Rule Definitions" (CONC-001, DD-001, VOL-001, COV-001
  threshold conditions), and "Data Quality Caveat" (conditional on
  `unpriced_holding_count > 0`; explains which computed facts are affected by incomplete
  local price data). Section ordering updated (D-079). Architecture invariant extended
  with broader forbidden-import scan (D-078). `647 passed, 0 skipped` — all invariants
  green. Decisions D-075 through D-080 recorded.

- **Phase 8C (local price-date gap diagnostics + repository hardening — Option B, Tier 2):**
  ✅ **accepted.** Pure helper `_compute_largest_gap` and four
  new fields added to `TickerQuality` in `backend/app/metrics/quality.py`:
  `local_price_date_count_on_or_before_report_date`, `largest_price_date_gap_days`,
  `largest_price_date_gap_start`, `largest_price_date_gap_end`. "Data Quality Summary"
  `ReportSection` updated with per-ticker gap facts and gap methodology note (local
  calendar-day language only; no exchange-session or trading-day claims). Gap fields
  exposed automatically via existing `data_quality.ticker_quality` serialization path.
  Architecture invariant extended with four new tests (raw SQL in routes, direct repo
  imports in routes, quality module layer isolation, system-clock purity). `701 passed,
  0 skipped` — all invariants green. Decisions D-081 through D-086 recorded. No paper
  trading, no simulated orders, no broker abstraction, no technical indicators, no
  backtesting, no external market data, no scheduler, no notifications, no new API routes,
  no new persistence tables, no new runtime dependencies introduced.

**v0.1 implementation accepted. Phase 8A, 8B, 8C accepted.**
Phase 8 further work requires its own dated DECISIONS.md entry and explicit
human approval before any code is written.

---

## 6. Locked decisions (index)

The authoritative log is `docs/DECISIONS.md`. Key locks:

- **D-013** Stack: Python/FastAPI + React/Vite + SQLite; manual refresh first; pytest. (Node/Fastify rejected.)
- **D-014** USD-only base currency; non-USD flagged & excluded.
- **D-015** CSV/file import is the first data path; no API provider chosen in Phase 0.
- **D-016** Negative quantities rejected on input (no shorts).
- **D-017** Duplicate tickers rejected on input (no merge).
- **D-018** Single portfolio only; no `portfolio_id` required.
- **D-019** Phase 0 docs accepted for planning, not implementation.
- **D-020** Synchronous `stdlib sqlite3` for Phase 2; no `aiosqlite`.
- **D-021** Watchlist duplicate ticker → `DuplicateTickerError`.
- **D-022** Price duplicate (ticker, price_date) → upsert (idempotent re-ingestion).
- **D-023** DB path from `OTOMASYON_DB_PATH` env var; default `./data/otomasyon.db`.
- **D-024** CSV parser: stdlib `csv.DictReader` only; no third-party dependencies.
- **D-025** Holdings/watchlist imports: all-or-nothing with DB duplicate pre-check. Prices: row-level error collection.
- **D-026** Supported CSV types: holdings, watchlist, prices.
- **D-027** Required columns: holdings (ticker, quantity, cost_basis, currency); watchlist (ticker); prices (ticker, date, close, currency).
- **D-028** Unknown extra CSV columns: silently ignored.
- **D-029** CSV delimiter: comma only; no `csv.Sniffer`.
- **D-030** Metrics engine purity: no I/O, no DB, no network, no system clock; data arrives as arguments.
- **D-031** Valuation date: latest price_date in supplied input; no system date used.
- **D-032** Missing price: excluded from valuation (not zero); unpriced tickers and coverage ratios reported.
- **D-033** Numeric precision: Python float; no Decimal; no engine-side rounding.
- **D-034** M-006 return basis: daily percentage returns; `statistics.pstdev`; not annualised.
- **D-035** Phase 4 scope: all six metrics M-001 through M-006, including time-series M-005 and M-006.
- **D-036** Alert engine boundary: receives metric result objects, no I/O, returns AlertResult list.
- **D-037** AlertConfig: frozen, caller-provided thresholds; conservative defaults.
- **D-038** AlertResult schema: frozen dataclass; evaluate_alerts returns all results, not only fired.
- **D-039** Compliance guard: raises ComplianceViolationError with all violations; never rewrites text.
- **D-040** Compliance chokepoint: every explanation passes check_compliance inside evaluate_alerts.
- **D-041** Severity labels: informational, watch, elevated only. No urgent/critical.
- **D-042** Compliance matching: whole-word \b for single terms, bounded phrase for multi-word; false-positive protections verified.
- **D-043** Alert threshold equality: strict greater-than only; exact equality does not fire.
- **D-044** Journal persistence: `journal_entries` in existing SQLite DB; repo under `data/persistence/journal_repo.py`.
- **D-045** Journal append-only: `add_entry`, `get_all`, `get_by_ticker` only; no update/delete.
- **D-046** User-authored journal text: compliance guard NOT applied; stored verbatim.
- **D-047** `action_taken` field name retained as user-authored past-tense record text.
- **D-048** `review_date` must be strictly after `entry_date` if provided.
- **D-049** Journal ordering: `entry_date DESC, created_at DESC`.
- **D-050** `created_at` uses UTC: `datetime.now(timezone.utc).isoformat()`.
- **D-051** Phase 7A boundary: pure report builder only; Phase 7B API routes require separate approval.
- **D-052** Report builder inputs: already-computed result objects as arguments; no DataAdapter/DB/I/O.
- **D-053** Report builder outputs: frozen `DailyReport`/`WeeklyReport`/`ReportSection` dataclasses.
- **D-054** Report compliance: all system-generated `ReportSection` text checked; journal fields verbatim.
- **D-055** Alert inclusion: all evaluated alerts (fired and non-fired) in every report.
- **D-056** Report date policy: `report_date` and `week_start` caller-provided; no system clock.
- **D-057** v0.1 closeout: complete only after Phase 7B acceptance; Phase 8 = Tier 3 gate review.
- **D-058** Phase 7B API boundary: read-only routes only; no write endpoints, no broker access.
- **D-059** FastAPI dependency: `fastapi>=0.100.0` runtime; `httpx2` dev optional; no uvicorn.
- **D-060** API date params: `report_date` and `week_start` are required caller-provided ISO dates.
- **D-061** API DB path: D-023 policy; per-request connection; `check_same_thread=False`.
- **D-062** API orchestration: connection → DataAdapter → metrics → alerts → builder → asdict → JSON.
- **D-063** Serialization: `dataclasses.asdict()`; no Pydantic model; journal text verbatim.
- **D-064** Alert inclusion in API: embedded in report sections; no separate top-level alerts array.
- **D-065** v0.1 completion: Phase 7B accepted + all tests green + docs updated + no forbidden scope.
- **D-066** DataAdapter journal extension: `get_journal_entries(date_from, date_to)` on ABC and adapter.

- **D-075** Phase 8B boundary: report explainability + hardening, Tier 2 only.
- **D-076** Phase 8B purity: new section builders are pure functions.
- **D-077** Phase 8B compliance: all new section text passes `check_compliance()`.
- **D-078** Phase 8B architecture invariant: broader forbidden-import scan added.
- **D-079** Phase 8B section placement: final section ordering documented.
- **D-080** Phase 8B test gate: 647 passed, 0 skipped.
- **D-081** Phase 8C boundary: local price-date gap diagnostics + hardening, Tier 2 only.
- **D-082** Phase 8C purity: gap computation is a pure function; report_date caller-provided.
- **D-083** Phase 8C compliance: gap text passes check_compliance(); local-calendar-day language.
- **D-084** Phase 8C data model: four new fields on TickerQuality; no new API routes.
- **D-085** Phase 8C architecture invariant: four new tests; total 12 invariant tests.
- **D-086** Phase 8C test gate: 701 passed, 0 skipped.

Any change to these requires a new dated entry in `DECISIONS.md` (append-only in spirit).

---

## 7. Document map (where to look)

| Doc | Use it for |
|---|---|
| `PRODUCT_PLAN.md` | What the product is, who it's for, positioning |
| `MVP_SCOPE.md` | The locked v0.1 in/out boundary |
| `RISK_POLICY.md` | Safety constitution; four-tier model; AI usage limits |
| `ALERT_POLICY.md` | Exact allowed/forbidden alert language + examples |
| `METRICS_SPEC.md` | Precise metric definitions, formulas, limitations |
| `JOURNAL_SCHEMA.md` | Decision-journal fields and validation rules |
| `DATA_SOURCES.md` | Data requirements, CSV-first, ToS gate |
| `ARCHITECTURE.md` | Modules, boundaries, stack, invariants |
| `ROADMAP.md` | Phased plan + per-phase acceptance criteria |
| `TEST_PLAN.md` | Test categories, edge cases, gates |
| `DECISIONS.md` | Append-only decision log |
| `PHASE1_SKELETON_PLAN.md` | The Phase 1 skeleton spec |
| `PROJECT_BRAIN.md` | **This file — the entry point** |
| `docs/reports/` | Future phase closeout reports |

---

## 8. Repository map (where things live)

```
README.md                     # public front door + disclaimer
PROJECT_BRAIN.md              # this file — read first
docs/                         # all specs + decisions (+ docs/reports/)
backend/
  pyproject.toml              # minimal; runtime deps empty in v0.1
  app/
    api/                      # FastAPI boundary (no execution endpoints, ever)
    core/                     # shared domain models/types
    data/adapters/            # DataAdapter interface + CSV adapter (Phase 3)
    data/persistence/         # SQLite/repository (Phase 2 — deferred)
    metrics/                  # pure metrics engine (Phase 4)
    alerts/                   # alert engine (Phase 5)
    compliance/               # safety guard — chokepoint for all generated text
    journal/                  # decision journal (Phase 6)
    reports/                  # report module (Phase 7)
  tests/                      # pytest; architecture/ holds the invariant test
frontend/                     # React/Vite empty shell; src/components/safety = disclaimer UI
ci/                           # CI stub concept
```

Today every `backend/app/*` module is an **empty boundary** (docstring only). Logic lands
phase by phase.

---

## 9. Working protocol (how to proceed, for humans and AI)

1. **Respect phase gates.** Do only the current phase. Each phase has acceptance criteria
   in `ROADMAP.md` and ends with human review. Never jump ahead "for convenience."
2. **Never weaken the invariants in §2.** If a task seems to require it, stop and surface
   the conflict instead of working around it.
3. **No broker / execution / paper-trading / live-trading code** enters the tree — the
   architectural-invariant test guards this and must stay green.
4. **Keep the metrics engine pure;** route every piece of generated user-facing text through
   the compliance guard.
5. **Data only via the DataAdapter;** CSV first; no API until its ToS checklist passes.
6. **Record decisions** in `DECISIONS.md`; record phase closeouts in `docs/reports/`.
7. **When unsure, ask or stop** — do not assume scope. The default posture is conservative.

### For AI agents specifically
- Treat this file as your standing context. Re-read §2 before generating anything user-facing.
- Do not implement features beyond the current phase, even if asked to "just scaffold a bit more."
- Do not add dependencies for trading, execution, market data brokers, news scraping, or
  technical indicators.
- AI may summarize/explain computed facts; AI must never be the source of a decision,
  a directional view, or a profit claim — and its output passes the compliance guard too.

---

## 10. Definition of done (project-level reminder)

A change is done when: it stays within the current phase; all invariants hold; the test
harness (including the no-broker/no-execution invariant) is green; generated text is
compliant; and the relevant docs/`DECISIONS.md`/`docs/reports/` are updated. Detailed
per-phase criteria live in `ROADMAP.md`.

---

*This file is the brain: identity, rules, status, and the map. Keep it short, current, and
honest. If it ever drifts from reality, fix it before doing anything else.*

---

## Phase completion summary

- Phase 0 complete
- Phase 1 complete
- Phase 2 complete
- Phase 3 complete
- Phase 4 complete
- Phase 5 complete
- Phase 6 complete
- Phase 7A complete (pure report builder)
- Phase 7B accepted
- v0.1 implementation accepted
- Phase 8 gate plan created; Option B (Tier 2 analytics) selected
- Phase 8A accepted (data quality analytics — Option B, Tier 2)
- Phase 8B accepted (report explainability + architecture hardening)
- Phase 8C accepted (local price-date gap diagnostics + repository hardening)
- Further Phase 8 work requires deliberate human approval
