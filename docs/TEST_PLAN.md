# TEST_PLAN.md

## Test philosophy

- Tests verify behaviour, not implementation.
- The metrics engine is pure — its tests are pure unit tests with no fixtures.
- Integration tests use in-memory SQLite only — never the production DB file.
- The architectural invariant test runs on every commit and is the hardest gate.
- Placeholder tests are explicitly skipped with a phase-gate reason; they are not deleted.

---

## Test categories

### A — Architecture invariant (Phase 1+)

| File | What it checks |
|---|---|
| `tests/architecture/test_no_broker_no_execution.py` | No broker imports, no execution functions, no advisory function names in source |

These tests must pass on every phase. They are never skipped.

---

### B — Unit tests (Phase 2+)

| Module | What to test |
|---|---|
| `core/models.py` | Valid construction, invalid inputs raise correct typed exceptions |
| `core/validation.py` | Each validation rule in isolation |
| `metrics/` | Each metric formula with known inputs and expected outputs |
| `compliance/` | Forbidden words trigger ComplianceViolationError; clean text passes |
| `alerts/` | Each alert rule fires at threshold; does not fire below threshold |

---

### C — Integration tests (Phase 2+)

| Module | What to test |
|---|---|
| `data/persistence/holdings_repo.py` | Insert, read, duplicate, negative qty, non-USD |
| `data/persistence/watchlist_repo.py` | Add, remove, duplicate handling |
| `data/persistence/prices_repo.py` | Insert, upsert, date-range filter |
| `data/adapters/` | Adapter satisfies DataAdapter ABC contract |

All integration tests use `":memory:"` SQLite.

---

### D — CSV adapter tests (Phase 3+)

- Valid holdings CSV round-trips correctly.
- Malformed rows are rejected with correct error types.
- Non-USD rows trigger `CurrencyError`.
- Negative quantity rows trigger `NegativeQuantityError`.
- Duplicate ticker rows trigger `DuplicateTickerError`.

---

### E — End-to-end tests (Phase 7+)

- API endpoint returns correct metrics for a known portfolio.
- Alert fires when threshold is crossed.
- Alert does not fire when threshold is not crossed.
- Report contains no forbidden advisory language.

---

## Edge cases (must be covered across phases)

| Edge case | Phase |
|---|---|
| Empty portfolio (zero holdings) | 2 |
| Single holding portfolio | 2 |
| Portfolio with 100 holdings | 2 |
| Price history with gaps | 3 |
| Price of zero — must be rejected | 2 |
| Non-USD currency in CSV | 3 |
| Negative quantity in CSV | 3 |
| Duplicate ticker in CSV | 3 |
| Metrics with zero price history | 4 |
| Alert rule at exactly the threshold boundary | 5 |
| Compliance guard: clean text passes | 5 |
| Compliance guard: forbidden word fails | 5 |
| Journal entry with no ticker | 6 |

---

## Phase gates

A phase is not complete until:
1. All tests introduced in that phase pass.
2. The architecture invariant test still passes.
3. No tests from a prior phase have been deleted or weakened.
4. Human review is complete.
