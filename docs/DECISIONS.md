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
