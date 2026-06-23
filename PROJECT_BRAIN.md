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
- **Phase 4 (metrics engine):** ⛔ **not started.**

**Next gate:** human review before any Phase 4 work begins.

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
