# METRICS_SPEC.md

## Scope

Metric definitions for v0.1. All metrics are computed by the pure metrics engine
(`backend/app/metrics/`). The engine has no I/O and no side effects — it takes data
structures as input and returns computed values.

*Implementation: Phase 4.*

---

## Metric catalogue (v0.1)

### M-001 — Position weight

**Definition:** The fraction of total portfolio market value represented by a single holding.

```
weight(i) = quantity(i) × price(i) / Σ(quantity(j) × price(j))
```

**Units:** Proportion [0, 1] or percentage.
**Limitation:** Uses end-of-day prices only. Intraday drift is not captured.

---

### M-002 — Portfolio market value

**Definition:** Sum of market values of all holdings at the latest available EOD price.

```
total_mv = Σ(quantity(i) × price(i))
```

**Units:** USD.

---

### M-003 — Cost basis (per position)

**Definition:** Total amount paid for a holding.

```
cost_basis_total(i) = quantity(i) × cost_basis_per_unit(i)
```

**Units:** USD.

---

### M-004 — Unrealised gain / loss (factual, not advisory)

**Definition:** Difference between current market value and total cost basis. Reported as a
fact, not a recommendation.

```
unrealised_gl(i) = (price(i) - cost_basis_per_unit(i)) × quantity(i)
```

**Units:** USD and percentage.
**Language rule:** Must be labelled "unrealised change in value" — not "profit" or "loss".

---

### M-005 — Drawdown from peak

**Definition:** Percentage decline of portfolio market value from its rolling N-day high.

```
drawdown = (peak_value - current_value) / peak_value
```

**Units:** Proportion [0, 1].
**Parameter:** Rolling window N (default 90 days).

---

### M-006 — 30-day return volatility proxy

**Definition:** Standard deviation of daily portfolio value changes over a 30-day window.
Used as a simple volatility proxy — not a risk model.

**Limitation:** Not annualised in v0.1. Does not account for correlation between holdings.
Must be labelled "volatility proxy" — not "risk" or "expected loss".

---

## Engine contract

- The metrics engine is a pure Python module: no database reads, no HTTP calls, no file I/O.
- All inputs are passed as plain data structures (lists, dicts, dataclasses).
- All outputs are plain data structures.
- The engine is fully deterministic given the same inputs.
- Unit tests for the engine may use only in-memory data — no fixtures requiring DB or network.

---

## Future metrics (deferred)

- Sector / asset-class concentration (requires sector data in CSV or user input).
- Beta proxy (requires benchmark price series).
- Sharpe-like ratio (deferred — requires risk-free rate assumption, out of scope v0.1).
