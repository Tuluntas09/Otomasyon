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
