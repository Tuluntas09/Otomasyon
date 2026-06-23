# DECISIONS.md

Append-only decision log. Each entry records a locked decision, the date it was made, the
options considered, and the rationale. Entries are never deleted or overwritten — add a
superseding entry instead.

---

## D-013 — Stack selection

**Date:** 2025-06 (Phase 0)
**Decision:** Python / FastAPI (backend) + React / Vite (frontend) + SQLite (local DB) +
pytest (test runner). Manual refresh first; no real-time data infrastructure in v0.1.
**Options considered:** Node/Fastify backend (rejected — Python ecosystem better suited for
numeric/data work; team familiarity).
**Rationale:** Mature, well-documented stack; SQLite keeps local-first promise with zero
infrastructure overhead.

---

## D-014 — Base currency

**Date:** 2025-06 (Phase 0)
**Decision:** USD-only in v0.1. Non-USD inputs are flagged and excluded — never silently
converted or summed.
**Rationale:** Multi-currency aggregation introduces FX risk and conversion complexity out of
scope for v0.1. Explicit exclusion prevents silent errors.

---

## D-015 — First data path

**Date:** 2025-06 (Phase 0)
**Decision:** CSV / file import is the first and only data path in v0.1. No external market
data API provider is chosen in Phase 0.
**Rationale:** CSV-first keeps the tool offline-capable and avoids binding to any provider's
Terms of Service before a ToS review checklist is completed.

---

## D-016 — Negative quantities

**Date:** 2025-06 (Phase 0)
**Decision:** Negative quantities are rejected on input. No short positions in v0.1.
**Rationale:** Short selling introduces margin, leverage, and loss-beyond-principal risk that
are out of scope for this instrument's v0.1 safety posture.

---

## D-017 — Duplicate tickers

**Date:** 2025-06 (Phase 0)
**Decision:** Duplicate tickers are rejected on input. No silent merging of lots.
**Rationale:** Silent lot-merging could mask cost-basis errors. Explicit rejection forces the
user to resolve ambiguity before it enters the system.

---

## D-018 — Single portfolio

**Date:** 2025-06 (Phase 0)
**Decision:** Single portfolio only in v0.1. No `portfolio_id` foreign key required.
**Rationale:** Multi-portfolio support adds schema and UI complexity that is out of scope for
v0.1. The single-portfolio constraint is a hard boundary, not an oversight.

---

## D-019 — Phase 0 acceptance

**Date:** 2025-06 (Phase 0)
**Decision:** Phase 0 documents are accepted for planning purposes only — not as
implementation approval. Each subsequent phase requires its own human review gate.
**Rationale:** Separating doc acceptance from implementation approval prevents scope creep
and ensures each phase is consciously authorized.

---

## D-020 — SQLite driver: synchronous stdlib sqlite3

**Date:** 2026-06-23 (Phase 2)
**Decision:** Use synchronous `stdlib sqlite3` for all database access in Phase 2. Do not
add `aiosqlite` or any async DB driver.
**Options considered:** `aiosqlite` (rejected — FastAPI async endpoints are not implemented
until Phase 7; adding async I/O now would add complexity with no benefit).
**Rationale:** The persistence layer is accessed from synchronous code in Phases 2–6.
Switching to async can be deferred to Phase 7 when the API layer is introduced, and only if
benchmarks justify it.

---

## D-021 — Watchlist duplicate ticker behaviour

**Date:** 2026-06-23 (Phase 2)
**Decision:** Inserting a ticker that already exists in the watchlist raises
`DuplicateTickerError`. No silent update or merge.
**Rationale:** Consistent with D-017 (holdings duplicate policy). Explicit rejection forces
the caller to be intentional; silent merging could mask data entry errors.

---

## D-022 — Price duplicate behaviour on (ticker, price_date)

**Date:** 2026-06-23 (Phase 2)
**Decision:** Inserting a price record where (ticker, price_date) already exists performs
an upsert — the newer value wins. No error is raised.
**Rationale:** End-of-day price CSV files may be re-ingested (e.g., after a correction).
Upsert makes re-ingestion idempotent. Unlike holdings or watchlist entries, a price
correction for the same date is a legitimate and expected operation.

---

## D-023 — DB file location: OTOMASYON_DB_PATH environment variable

**Date:** 2026-06-23 (Phase 2)
**Decision:** The SQLite database file path is read from the `OTOMASYON_DB_PATH` environment
variable, defaulting to `./data/otomasyon.db` relative to the process working directory.
**Options considered:** `DATABASE_URL` (rejected — that convention implies a URL-format
string; `sqlite3` takes a plain file path; using `OTOMASYON_DB_PATH` avoids the mismatch
and is more discoverable for a local-first tool).
**Rationale:** Environment variable override allows tests to use `:memory:` without
patching code. The project-specific name (`OTOMASYON_DB_PATH`) avoids collisions with
other tools in the same environment.

---

## D-024 — CSV parser: stdlib csv only

**Date:** 2026-06-23 (Phase 3)
**Decision:** Use Python stdlib `csv.DictReader` for all CSV parsing. No `pandas`, `polars`,
`numpy`, or any third-party CSV library.
**Rationale:** `pyproject.toml` keeps `dependencies = []`. `csv.DictReader` satisfies all
v0.1 requirements (header-based parsing, comma delimiter, string extraction) with zero
added dependencies.

---

## D-025 — CSV import transaction behavior

**Date:** 2026-06-23 (Phase 3)
**Decision:** Holdings and watchlist imports are all-or-nothing. Pass 1 validates every row
and pre-checks DB duplicates (loading existing tickers from the repo) before any write
begins. Pass 2 writes only when Pass 1 produced zero errors. Any failure raises
`CsvImportError`. Prices imports use row-level error collection: valid rows are upserted
immediately; invalid rows are appended to `ImportResult.errors`; the function always
returns an `ImportResult` and never raises `CsvImportError`.
**Options considered:** all-or-nothing for all three types (simpler, but would make
re-ingesting large price files impractical if one row is malformed).
**Rationale:** A portfolio is only meaningful when complete — partial holdings produce wrong
metrics. Price records are independent; partial ingestion is safe and consistent with the
D-022 upsert policy that already assumes re-imports are normal.

---

## D-026 — Supported CSV import types in v0.1

**Date:** 2026-06-23 (Phase 3)
**Decision:** Three import types are supported: `holdings`, `watchlist`, `prices`. Each has
its own named function (`import_holdings_csv`, `import_watchlist_csv`,
`import_prices_csv`). No generic dispatcher is implemented in Phase 3.
**Rationale:** Three types map directly to the three Phase 2 repositories. Direct function
calls are more Pythonic and remove indirection with no current consumer to justify it.

---

## D-027 — Required CSV columns per import type

**Date:** 2026-06-23 (Phase 3)
**Decision:**

| Import type | Required columns |
|---|---|
| holdings | `ticker`, `quantity`, `cost_basis`, `currency` |
| watchlist | `ticker` |
| prices | `ticker`, `date`, `close`, `currency` |

Absence of any required column raises `MissingColumnError` after reading the header row,
before any data rows are processed.
**Rationale:** Column names match `DATA_SOURCES.md` exactly for holdings and prices.
Watchlist format is new in Phase 3; `ticker` is the only meaningful field.

---

## D-028 — Unknown extra CSV columns: ignore

**Date:** 2026-06-23 (Phase 3)
**Decision:** Extra columns beyond the required set are silently ignored.
**Options considered:** warn (no output mechanism exists yet in Phase 3); reject (breaks
CSV exports from spreadsheets or brokerage tools that include metadata columns).
**Rationale:** Ignoring extra columns reduces friction with zero safety risk — the importer
only reads the named columns it needs. Rejecting them would force users to manually clean
exports.

---

## D-029 — CSV delimiter: comma only

**Date:** 2026-06-23 (Phase 3)
**Decision:** Comma (`,`) is the only supported delimiter in v0.1. `csv.Sniffer` is not
used.
**Options considered:** `csv.Sniffer` for automatic detection (rejected — unreliable on
short files; a wrong sniff silently produces malformed parses).
**Rationale:** Comma is the universal standard and matches any spreadsheet CSV export
default. If the user provides a non-comma-delimited file, the `MissingColumnError` on the
header check surfaces it clearly.
