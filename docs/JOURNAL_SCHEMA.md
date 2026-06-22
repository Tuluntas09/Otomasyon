# JOURNAL_SCHEMA.md

## Purpose

The decision journal is an append-only log of the user's own reasoning. It records why the
user made a decision — not what the system recommends. Entries are written by the user;
the system stores and retrieves them.

*Implementation: Phase 6.*

---

## Entry fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | INTEGER (auto) | system | Primary key |
| `entry_date` | TEXT (ISO-8601) | ✅ | Date the decision was made |
| `ticker` | TEXT or NULL | — | Associated ticker, if any |
| `action_taken` | TEXT | ✅ | Free text: what the user did (their words) |
| `reasoning` | TEXT | ✅ | Free text: why they did it |
| `hypothesis` | TEXT | — | Optional: what they expect to observe (testable) |
| `review_date` | TEXT (ISO-8601) | — | Optional: when user wants to revisit |
| `tags` | TEXT (comma-separated) | — | Optional: user-defined tags |
| `created_at` | TEXT (ISO-8601) | system | Insertion timestamp |

---

## Validation rules

- `entry_date` must be a valid ISO-8601 date.
- `action_taken` and `reasoning` must be non-empty strings.
- `ticker`, if provided, must pass the same ticker validation as holdings.
- Entries are append-only — no deletion or update of past entries.
- `review_date`, if provided, must be a valid ISO-8601 date after `entry_date`.

---

## Language rules

- The system never auto-generates journal entries.
- The system never suggests what the user should write.
- The `action_taken` and `reasoning` fields are the user's own words — they are not scanned
  by the compliance guard (they record past facts, not system advice).
- The system may display journal entries verbatim — it does not paraphrase or summarise them
  in v0.1.

---

## Journal vs alert log

The journal records the user's reasoning about their own decisions. The alert log (Phase 5)
records which system rules fired. These are separate systems and must not be merged.

---

## Future fields (deferred)

- `hypothesis_outcome` — user records what actually happened against their hypothesis.
- Attachments / file links — out of scope v0.1.
- Tags search / filter — Phase 6 UX, not schema.
