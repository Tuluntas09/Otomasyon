# Otomasyon

**Personal finance research and decision-support instrument.**

> **Disclaimer:** This tool is not investment advice. It measures, records, and notifies.
> It never advises, never trades, and never claims profit. The user is solely responsible
> for their own financial decisions.

---

## What it is

Otomasyon is a local-first tool that helps a single user:

- See the real risk shape of one portfolio.
- Record the reasoning behind their own decisions.
- Receive explainable, rule-based alerts when measurable thresholds are crossed.

It is a **research and decision-support instrument** — not a signal service, not an
execution engine, and not a recommendation system.

## What it is not

It is **not** a trading bot, signal service, advisor, broker client, backtester, news engine,
or arbitrage scanner.

It does **not**:

- Place, simulate, or record orders of any kind.
- Connect to any broker or trading API.
- Fetch external market data.
- Compute technical indicators.
- Run backtests or strategy simulations.
- Produce buy, sell, or hold recommendations.
- Automate any action on a market.

---

## Current status

| Milestone | Status |
|---|---|
| v0.1 — core backend | ✅ accepted |
| Phase 7B — read-only API | ✅ accepted |
| Phase 8 Gate Plan — Option B selected | ✅ accepted |
| Phase 8A — Data Quality Analytics | ✅ accepted |
| Phase 8B — Report Explainability + Architecture Hardening | ✅ accepted |
| Phase 8C — Local Price-Date Gap Diagnostics + Repository Hardening | ✅ accepted |
| Phase 8D — API Contract Documentation + API Error Taxonomy | ✅ accepted |
| Phase 8E | ⛔ not started — requires explicit approval |

**Milestone tag:** `v0.1-phase8-option-b`

**Latest verified test result:** 701 passed, 0 skipped

---

## Stack

- **Backend:** Python 3.11+ / FastAPI / SQLite (zero external runtime dependencies beyond FastAPI)
- **Tests:** pytest
- **Frontend:** React / Vite placeholder — no UI implemented

---

## Local setup

### 1. Clone and enter the repository

```bash
git clone https://github.com/Tuluntas09/Otomasyon.git
cd Otomasyon
```

### 2. Create and activate a virtual environment (recommended)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install backend dependencies

```bash
pip install -e "backend/[dev]"
```

### 4. Run the test suite

```bash
python -m pytest backend/tests/ -q
```

Expected result: `701 passed, 0 skipped`

### 5. Start the API server

```bash
cd backend
python -m uvicorn main:app --reload
```

The server starts on `http://127.0.0.1:8000` by default.

**Database path:** controlled by the `OTOMASYON_DB_PATH` environment variable.
Default: `./data/otomasyon.db` (relative to the `backend/` directory).

```bash
# Optional: set a custom database path
export OTOMASYON_DB_PATH=/path/to/your/otomasyon.db
```

---

## API surface

All routes are read-only. No write, delete, or mutation routes exist.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check — no data access |
| `GET` | `/reports/daily` | Daily report for a caller-supplied date |
| `GET` | `/reports/weekly` | Weekly report for a caller-supplied date range |

### Parameters

**`GET /reports/daily`**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `report_date` | `YYYY-MM-DD` | Yes | The date for which to compute the report |

**`GET /reports/weekly`**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `week_start` | `YYYY-MM-DD` | Yes | First day of the week window |
| `report_date` | `YYYY-MM-DD` | Yes | Effective report date (must be >= week_start) |

Interactive documentation is available at `http://127.0.0.1:8000/docs` when the server is running.

Full API contract, field definitions, section ordering rules, example payloads, and error
taxonomy are documented in [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md).

---

## Capabilities

| Capability | Description |
|---|---|
| CSV ingestion | Holdings, watchlist, and EOD price data imported from local CSV files |
| SQLite persistence | Local database; schema initialised idempotently on first request |
| Metrics engine | Six portfolio metrics (M-001 through M-006): market value, position weights, unrealised change, coverage ratio, drawdown from peak, 30-day return volatility proxy |
| Alert rules | Four threshold rules (CONC-001, DD-001, VOL-001, COV-001); all results returned whether fired or not |
| Compliance guard | All system-generated text is checked for forbidden advisory language before inclusion in any report |
| Decision journal | Append-only; user-authored entries stored and returned verbatim |
| Report builder | Daily and weekly frozen reports; metric definitions, alert rule definitions, data quality summary, and journal entries embedded |
| Data quality analytics | Per-ticker coverage, price record count, staleness, and largest price-date gap |
| Read-only API | Three GET endpoints; no write routes in any form |

---

## Boundaries in force

The following are **not implemented and will not be added** without an explicit decision entry:

- Order placement (real or simulated)
- Broker integration of any kind
- Trading credentials storage
- External market-data API calls
- Web scraping
- Technical indicators
- Backtesting or strategy simulation
- Paper trading or live trading
- Simulated orders
- Strategy engine or signal generation
- Scheduler or background tasks
- Push notifications or email
- Frontend UI (beyond the empty placeholder)
- Multi-portfolio support
- Multi-currency aggregation
- Write API routes

---

## Documentation

| Document | Purpose |
|---|---|
| [`PROJECT_BRAIN.md`](PROJECT_BRAIN.md) | Project constitution — identity, invariants, four-tier boundary |
| [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) | Full API contract: fields, shapes, section ordering, example payloads, error taxonomy |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Phase-by-phase status, acceptance criteria, and delivered capabilities |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Append-only decision log (D-013 through D-092) |
| [`docs/METRICS_SPEC.md`](docs/METRICS_SPEC.md) | Specification for M-001 through M-006 |
| [`docs/ALERT_POLICY.md`](docs/ALERT_POLICY.md) | Alert rule definitions and threshold policy |
| [`docs/RISK_POLICY.md`](docs/RISK_POLICY.md) | Four-tier boundary and risk posture |
| [`docs/reports/PHASE8_OPTION_B_CLOSEOUT.md`](docs/reports/PHASE8_OPTION_B_CLOSEOUT.md) | Phase 8 Option B formal closeout record |
