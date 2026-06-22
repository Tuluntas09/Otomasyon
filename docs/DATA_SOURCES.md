# DATA_SOURCES.md

## Data philosophy

Otomasyon is CSV-first and offline-capable. No external API is called in v0.1. Any future
API integration must pass a Terms of Service (ToS) review checklist before it is connected.

---

## v0.1 data path: CSV import

### Holdings CSV

User provides a CSV file with their current portfolio positions.

**Expected columns:**

| Column | Type | Notes |
|---|---|---|
| `ticker` | TEXT | Exchange ticker symbol (uppercase) |
| `quantity` | FLOAT | Number of units held. Must be > 0. |
| `cost_basis` | FLOAT | Per-unit cost in USD |
| `currency` | TEXT | Must be `USD` in v0.1 |

**Validation on import:**
- `quantity` must be positive — negative values are rejected (`NegativeQuantityError`).
- `currency` must be `USD` — other values are rejected (`CurrencyError`).
- Duplicate tickers within the file are rejected (`DuplicateTickerError`).

---

### Prices CSV

User provides a CSV file of end-of-day price data.

**Expected columns:**

| Column | Type | Notes |
|---|---|---|
| `ticker` | TEXT | Must match a known ticker |
| `date` | TEXT | ISO-8601 date (YYYY-MM-DD) |
| `close` | FLOAT | Closing price in USD. Must be > 0. |
| `currency` | TEXT | Must be `USD` in v0.1 |

**Validation on import:**
- `close` must be positive.
- `currency` must be `USD`.
- Duplicate `(ticker, date)` rows: resolved by upsert (later import wins for same date).

---

## Data not accepted in v0.1

| Data type | Status |
|---|---|
| Real-time / intraday prices | ❌ deferred |
| BIST, crypto, or FX instruments | ❌ deferred (non-USD) |
| Options, futures, or derivatives | ❌ off-roadmap |
| News / sentiment feeds | ❌ off-roadmap |
| Broker account exports | ❌ off-roadmap |

---

## Future API data path (deferred)

Before any external API is connected, the following checklist must be completed and logged
in `DECISIONS.md`:

- [ ] Provider ToS reviewed and found compatible with this use case.
- [ ] Data usage restricted to personal, non-commercial use confirmed.
- [ ] Attribution requirements identified.
- [ ] API key storage approach reviewed (no plaintext in repo).
- [ ] Rate-limit and cost impact assessed.
- [ ] Decision entry added to `DECISIONS.md` naming the provider and confirming the above.

*No provider is chosen or committed in Phase 0.*
