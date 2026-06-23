# Phase 4 Closeout Report

**Date:** 2026-06-23
**Phase:** 4 — Pure metrics engine
**Status:** Complete — awaiting human review

---

## 1. Decisions recorded

| ID | Decision |
|---|---|
| D-030 | Metrics engine purity boundary: no sqlite3, csv, os, pathlib, network, persistence, or adapter imports. |
| D-031 | Valuation date: latest price_date in supplied input. No system clock. Windows measured backwards from that date. |
| D-032 | Missing price: excluded from valuation (not valued at zero). `unpriced_tickers` and coverage ratios reported. |
| D-033 | Numeric precision: Python float; no Decimal; no engine-side rounding. |
| D-034 | M-006 return basis: daily percentage returns; `statistics.pstdev`; not annualised. |
| D-035 | Phase 4 scope: all six metrics M-001 through M-006, snapshot and time-series. |

---

## 2. Files created

| File | Purpose |
|---|---|
| `backend/app/metrics/results.py` | `PositionMetrics`, `PortfolioSnapshot`, `DrawdownResult`, `VolatilityResult` frozen dataclasses |
| `backend/app/metrics/engine.py` | `compute_portfolio_snapshot`, `compute_drawdown`, `compute_volatility_proxy`; internal helpers `_latest_prices`, `_portfolio_daily_values` |
| `backend/tests/unit/test_metrics.py` | 44 unit tests: 14 snapshot, 10 drawdown, 12 volatility, 8 boundary/purity |
| `docs/reports/PHASE4_CLOSEOUT.md` | This file |

---

## 3. Files modified

| File | Change |
|---|---|
| `backend/app/metrics/__init__.py` | Docstring updated; public API re-exported (`compute_portfolio_snapshot`, `compute_drawdown`, `compute_volatility_proxy`, result types) |
| `docs/DECISIONS.md` | Appended D-030 through D-035 |
| `docs/ROADMAP.md` | Phase 4 status updated to complete; key deliverables and acceptance criteria listed |
| `PROJECT_BRAIN.md` | Phase 4 status updated; D-030 through D-035 added to decisions index |

---

## 4. Metrics implemented

### M-001 — Position weight
`weight = position_market_value / total_market_value`  
Computed per-position inside `compute_portfolio_snapshot`. Holdings with no price get `weight=None`. If no holding has a price, all weights are `None`.

### M-002 — Portfolio market value
`total_mv = Σ(quantity × latest_close_price)` for priced holdings only.  
Computed inside `compute_portfolio_snapshot`. Unpriced holdings are excluded (D-032).

### M-003 — Cost basis per position
`total_cost_basis = quantity × cost_basis_per_unit`  
Computed for every position regardless of price availability (no price required).

### M-004 — Unrealised change in value
`unrealised_change_usd = (price - cost_basis_per_unit) × quantity`  
`unrealised_change_pct = (price - cost_basis_per_unit) / cost_basis_per_unit`  
Both are `None` if no price is available. `unrealised_change_pct` is `None` when `cost_basis_per_unit == 0.0` (division by zero guard). Language: "unrealised_change" naming only — no "profit" or "loss" field names.

### M-005 — Drawdown from peak
`drawdown = (peak_value - current_value) / peak_value`  
Window runs backwards from latest input price date (D-031). Returns `None` if no holdings, no usable dates, or `peak_value <= 0`. Exactly one usable date returns `drawdown=0.0`.

### M-006 — 30-day return volatility proxy
`daily_return[t] = (v[t] - v[t-1]) / v[t-1]`  
`volatility_proxy = statistics.pstdev(daily_returns)`  
Population std dev (D-034). Not annualised. Window relative to latest input date (D-031). Returns `None` if fewer than 2 usable dates or all returns have zero denominator.

---

## 5. Missing-data and coverage behavior

Holdings with no price in the supplied `price_records` are excluded from valuation (D-032):
- `PortfolioSnapshot.unpriced_tickers` — list of excluded tickers for snapshot metrics.
- `DrawdownResult.min_coverage_ratio` / `latest_coverage_ratio` — for time-series metrics.
- `VolatilityResult.min_coverage_ratio` / `latest_coverage_ratio` — for time-series metrics.
- `coverage_ratio` per date = holdings with a price on that date / total holdings.

Missing prices are **never** silently valued at zero. Callers receive explicit coverage information to decide whether to surface a data quality warning.

---

## 6. Valuation-date and window behavior

All time windows (M-005, M-006) are calculated as:
- `latest_date = max(pr.price_date for pr in price_records)` — from input data, not system clock.
- `cutoff_date = latest_date - timedelta(days=window_days)`.
- Records where `date >= cutoff_date` are included.

`date.fromisoformat` is used for all date parsing. `date.today()` and `datetime.now()` are not called anywhere in `backend/app/metrics/`.

---

## 7. Test result

```
222 passed, 0 skipped in 0.28s
```

- 178 tests carried forward from Phases 1–3: **all PASSED**
- 44 new Phase 4 tests: **all PASSED**
- Architecture invariant (`test_no_broker_no_execution.py`): **PASSED**
- No tests from prior phases deleted or weakened.
- `pyproject.toml` `dependencies = []` — unchanged.

New test breakdown:
- `TestComputePortfolioSnapshot`: 14 tests (M-001 through M-004)
- `TestComputeDrawdown`: 10 tests (M-005)
- `TestComputeVolatilityProxy`: 12 tests (M-006)
- Boundary/purity tests: 8 tests (imports, field naming)

---

## 8. Confirmation: metrics engine is pure

Verified by both code review and boundary tests:

| Forbidden import | Present in `backend/app/metrics/`? |
|---|---|
| `sqlite3` | ✗ |
| `csv` | ✗ |
| `os` | ✗ |
| `pathlib` | ✗ |
| `requests` / `httpx` / `aiohttp` | ✗ |
| `app.data.persistence.*` | ✗ |
| `app.data.adapters.*` | ✗ |
| `date.today()` / `datetime.now()` | ✗ |

Actual imports in `engine.py`: `statistics`, `datetime.date`, `datetime.timedelta`, `app.core.models`, `app.metrics.results` — all permitted.

No result dataclass field uses "profit" or "loss" naming. `unrealised_change_usd` and `unrealised_change_pct` are used throughout (per M-004 language rule in `METRICS_SPEC.md`).

---

## 9. Confirmation: out-of-scope items not implemented

The following are absent from all new code:

- FastAPI routes or HTTP layer
- Frontend UI
- Alert engine
- Compliance guard
- Decision journal
- Report generation
- CSV parsing
- SQLite repositories
- DataAdapter orchestration
- External market-data API calls
- HTTP clients
- Web scraping
- Technical indicators
- Backtesting, paper trading, live trading
- Broker integration or order placement
- Buy/sell/hold/target-price/profit/opportunity language

---

## 10. Deviations from the Phase 4 implementation prompt

None. All metrics, result types, function signatures, edge-case handling, window behavior, coverage fields, naming rules, and test requirements were implemented as specified.

---

*End of Phase 4 closeout report.*
