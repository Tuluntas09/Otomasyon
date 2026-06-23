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

---

## D-030 — Metrics engine purity boundary

**Date:** 2026-06-23 (Phase 4)
**Decision:** `backend/app/metrics/` must not import `sqlite3`, `csv`, `os`, `pathlib`,
any network library (`requests`, `httpx`, `aiohttp`), `app.data.persistence.*`, or
`app.data.adapters.*`. All data arrives as function arguments (`list[Holding]`,
`list[PriceRecord]`). No environment variables, no file I/O, no network access, no
dependence on the system clock. Enforced by boundary tests in `test_metrics.py`.
**Rationale:** Purity is a non-negotiable invariant per `PROJECT_BRAIN.md` §2 and
`ARCHITECTURE.md` §2. Pure functions are trivially testable, deterministic, and composable
with any future data source without modification.

---

## D-031 — Valuation date policy: latest available input price date

**Date:** 2026-06-23 (Phase 4)
**Decision:** The metrics engine does not accept an explicit "as-of date" parameter.
It always uses the most recent `price_date` in the `price_records` list supplied as input
as its reference point. Time windows (drawdown, volatility) are measured backwards from
that latest input date — never from `date.today()`, `datetime.now()`, or any system clock.
**Options considered:** Explicit `as_of_date` parameter (rejected for Phase 4 — filtering
belongs in the orchestration layer, not the pure engine; callers pass pre-filtered data).
**Rationale:** System-clock dependence would make tests fragile (date-sensitive) and
violate the determinism invariant. Caller-provided data defines the temporal context.

---

## D-032 — Missing price behavior: exclude from valuation and report

**Date:** 2026-06-23 (Phase 4)
**Decision:** A `Holding` with no corresponding `PriceRecord` in the input is excluded
from market value, weight, and unrealised-change calculations. It is never valued at zero
(zero would corrupt weight percentages). `PortfolioSnapshot.unpriced_tickers` lists
every excluded holding. For time-series metrics (M-005, M-006), portfolio value on a given
date is the sum of `quantity × close_price` for holdings that have a price on that date;
dates where a holding has no price are included in the series using the holdings that do
have prices; `min_coverage_ratio` and `latest_coverage_ratio` in `DrawdownResult` and
`VolatilityResult` expose the data quality so callers can surface warnings.
**Rationale:** Silently valuing a missing price at zero corrupts all percentage calculations
downstream. Explicit exclusion with reporting is more transparent and consistent with the
project's policy of surfacing data quality issues rather than hiding them.

---

## D-033 — Numeric precision: Python float, no engine-side rounding

**Date:** 2026-06-23 (Phase 4)
**Decision:** All internal and result values use Python `float` (IEEE 754 double precision).
No `Decimal`. No rounding inside the engine. All result dataclass fields that hold computed
values are `float` (or `float | None`). Callers and formatters apply display rounding.
**Rationale:** EOD portfolio metrics do not require accounting-grade reconciliation.
`Decimal` adds complexity with no v0.1 benefit. Returning raw floats lets the alert engine
(Phase 5) compare thresholds cleanly without double-rounding artifacts.

---

## D-034 — M-006 return basis: percentage returns, population standard deviation

**Date:** 2026-06-23 (Phase 4)
**Decision:** M-006 computes standard deviation of **daily percentage returns**
`(v[t] - v[t-1]) / v[t-1]`, not absolute dollar changes. Standard deviation is computed
using `statistics.pstdev` (population std dev). The result is not annualised (v0.1
constraint per `METRICS_SPEC.md`). If `v[t-1] == 0.0`, that return is skipped.
**Options considered:** Dollar-change std dev (rejected — scale-dependent; grows with
portfolio value, making alert thresholds non-portable across portfolio sizes).
**Rationale:** `ALERT_POLICY.md` example shows "2.8%", implying a dimensionless result.
Percentage returns are scale-independent. Population std dev is appropriate because we
are measuring the actual returns in the window, not estimating an unobserved population
parameter.

---

## D-035 — Phase 4 scope: both snapshot and time-series metrics (M-001 through M-006)

**Date:** 2026-06-23 (Phase 4)
**Decision:** Phase 4 implements all six v0.1 metrics from `METRICS_SPEC.md`. M-001
through M-004 are snapshot metrics (no price history required beyond the latest price
per ticker). M-005 (drawdown from peak) and M-006 (30-day return volatility proxy) are
time-series metrics computed from the supplied price history. Minimum data requirements:
M-005 requires at least 1 date in the window; M-006 requires at least 2 dates (to produce
at least 1 daily return). Both return `None` when minimum data is not met — they never
raise for insufficient data.
**Rationale:** Deferring M-005 and M-006 to a later phase would leave the alert engine
(Phase 5) without the drawdown and volatility inputs it needs. All six metrics are
defined in `METRICS_SPEC.md` for v0.1; implementing them together is the right gate.

---

## D-036 — Alert engine boundary

**Date:** 2026-06-23 (Phase 5)
**Decision:** The alert engine (`backend/app/alerts/`) receives already-computed metric
result objects (`PortfolioSnapshot`, `DrawdownResult | None`, `VolatilityResult | None`)
and an `AlertConfig`. It does not call Phase 4 metric functions, does not access the
database, and performs no file or network I/O. It returns a list of `AlertResult` objects.
**Rationale:** Keeping the alert engine as a pure consumer of metric results (not a
producer) preserves the same purity invariant that governs the metrics engine. It also
makes alert evaluation trivially testable without any database fixtures.

---

## D-037 — AlertConfig: caller-provided thresholds with conservative defaults

**Date:** 2026-06-23 (Phase 5)
**Decision:** Alert thresholds are expressed as a frozen `AlertConfig` dataclass supplied
by the caller. Conservative defaults: concentration 0.25, drawdown 0.15, volatility 0.02,
max_unpriced_holdings 0.
**Rationale:** Frozen dataclasses prevent accidental mutation. Caller-supplied config
decouples threshold policy from engine logic. Conservative defaults ensure the engine
is safe out of the box.

---

## D-038 — AlertResult schema: all evaluations returned, not only fired ones

**Date:** 2026-06-23 (Phase 5)
**Decision:** `AlertResult` is a frozen dataclass with fields: `rule_id`, `fired`,
`severity`, `metric_value`, `threshold`, `explanation`, `ticker`. `evaluate_alerts`
returns a result for every evaluated rule, not only the ones that fired.
**Rationale:** Returning all results (including non-firing ones) lets callers display
a complete picture — showing that a rule was evaluated and did not fire is informative
in itself. It avoids silent absence where a missing result is ambiguous.

---

## D-039 — Compliance guard behavior: raise with all violations, never rewrite

**Date:** 2026-06-23 (Phase 5)
**Decision:** `check_compliance(text)` passes silently for compliant or empty text.
If any forbidden term is found it raises `ComplianceViolationError` listing every matched
term. It never rewrites, sanitizes, or truncates the input text.
**Rationale:** Silently sanitizing text would allow non-compliant strings to reach the
user in a modified form without the developer being alerted. Hard failure forces the
caller to supply compliant text from the outset.

---

## D-040 — Compliance as a hard chokepoint inside evaluate_alerts

**Date:** 2026-06-23 (Phase 5)
**Decision:** Every alert explanation is passed through `check_compliance()` inside
`evaluate_alerts`, before the `AlertResult` is constructed. If `check_compliance` raises,
the error propagates to the caller.
**Rationale:** This makes compliance non-optional — no `AlertResult` can exist with an
explanation that has not been checked. It is consistent with `ARCHITECTURE.md` §4:
"Compliance is a chokepoint."

---

## D-041 — Severity labels: informational, watch, elevated only

**Date:** 2026-06-23 (Phase 5)
**Decision:** Alert severity uses exactly three labels: `"informational"` (not fired),
`"watch"` (fired, value ≤ 2× threshold), `"elevated"` (fired, value > 2× threshold).
Labels `"urgent"`, `"critical"`, and any action-oriented label are prohibited.
**Rationale:** Action-oriented severity labels (urgent, critical) imply the user must act.
This violates the policy that alerts describe facts, not prescribe action.

---

## D-042 — Compliance matching: whole-word for single terms, bounded phrase for multi-word

**Date:** 2026-06-23 (Phase 5)
**Decision:** Single-word forbidden terms use `\b<term>\b` (whole-word, case-insensitive,
Unicode). Multi-word phrases use `\b<phrase>\b` with word boundaries only at the start and
end of the phrase. Explicit false-positive verifications: "threshold" does not trigger
"hold"; "glossy" does not trigger "loss"; "total" and "capital" do not trigger Turkish "al"
— all confirmed by `\b` semantics (the preceding character is a word character, so no
boundary exists before the substring).
**Rationale:** Whole-word matching prevents substring false positives. Unicode flag
ensures Turkish characters (ı, ş, ç, ğ, ö, ü, etc.) are treated as word characters.

---

## D-043 — Alert threshold equality: strict greater-than only

**Date:** 2026-06-23 (Phase 5)
**Decision:** All alert rule comparisons use strict greater-than (`>`). A metric value
exactly equal to the threshold does NOT fire the alert. This applies to all four rules:
CONC-001, DD-001, VOL-001, and COV-001.
**Rationale:** Alert wording uses "above", "exceeds", and "ceiling breach" semantics.
Firing at exact equality would contradict "above the ceiling of X%" when the value IS X%.
Strict greater-than is also consistent with standard threshold-alarm conventions.

---

## D-044 — Journal persistence location

**Date:** 2026-06-23 (Phase 6)
**Decision:** The `journal_entries` table is added to the existing SQLite database via
`CREATE TABLE IF NOT EXISTS` in `backend/app/data/persistence/db.py`. The journal
persistence repository lives at `backend/app/data/persistence/journal_repo.py`, not under
`backend/app/journal/`. The `journal/` module contains domain model and validation only.
**Rationale:** All SQLite access must remain under `backend/app/data/persistence/` per the
architecture boundary. Mixing persistence into the domain module would break the layering
invariant enforced by architecture tests.

---

## D-045 — Journal append-only constraint

**Date:** 2026-06-23 (Phase 6)
**Decision:** `JournalRepo` exposes `add_entry()`, `get_all()`, and `get_by_ticker()` only.
No `update()` or `delete()` methods exist. Multiple entries for the same ticker are allowed.
**Rationale:** The decision journal is a factual record of past reasoning. Editing or
deleting past entries would undermine its value as an honest log. Append-only semantics
match `JOURNAL_SCHEMA.md` ("entries are append-only").

---

## D-046 — User-authored journal text and the compliance guard

**Date:** 2026-06-23 (Phase 6)
**Decision:** `check_compliance()` is NOT called on `action_taken`, `reasoning`,
`hypothesis`, or `tags`. These fields are stored verbatim as user-authored private notes.
**Rationale:** `JOURNAL_SCHEMA.md` states: "action_taken and reasoning fields are the
user's own words — they are not scanned by the compliance guard (they record past facts,
not system advice)." Compliance scanning is reserved for system-generated text only.

---

## D-047 — action_taken field name retained

**Date:** 2026-06-23 (Phase 6)
**Decision:** The field is named `action_taken` as specified in `JOURNAL_SCHEMA.md`.
It is user-authored past-tense record text describing what the user did, not
system-generated advice.
**Rationale:** `action_taken` accurately names the field's semantics (past tense, user
record) and does not imply any system recommendation or advisory signal.

---

## D-048 — review_date must be strictly after entry_date

**Date:** 2026-06-23 (Phase 6)
**Decision:** If `review_date` is provided, it must be strictly after `entry_date`.
Equal dates raise `JournalValidationError`. `None` is always valid.
**Rationale:** A review date equal to the entry date is logically meaningless — the user
cannot review a decision on the same day it was recorded in a forward-looking sense.
Strict inequality matches `JOURNAL_SCHEMA.md`: "must be a valid ISO-8601 date after entry_date."

---

## D-049 — Journal ordering: entry_date DESC, created_at DESC

**Date:** 2026-06-23 (Phase 6)
**Decision:** `get_all()` and `get_by_ticker()` return entries ordered by `entry_date DESC,
created_at DESC`. Most recent decision date first; for same-date entries, most recently
inserted first.
**Rationale:** Users most often want to see recent decisions first. Secondary sort by
`created_at` gives a deterministic and natural order when multiple entries share a date.

---

## D-050 — created_at uses UTC timestamp

**Date:** 2026-06-23 (Phase 6)
**Decision:** `created_at` is set using `datetime.now(timezone.utc).isoformat()`.
The resulting string includes UTC timezone information (e.g., `+00:00`).
**Rationale:** UTC timestamps are deterministic across local timezone changes, safe for
ordering comparisons across DST transitions, and unambiguous for any future log analysis.

---

## D-051 — Phase 7A implementation boundary

**Date:** 2026-06-23 (Phase 7A)
**Decision:** Phase 7A implements the pure report builder only (`backend/app/reports/`).
Phase 7B (minimal FastAPI routes under `backend/app/api/`) requires separate human approval
before implementation begins. No report delivery, scheduling, push, email, frontend UI, or
manual-run surface is included in Phase 7A.
**Rationale:** Incremental phase gates allow each layer to be audited independently.
The report builder is a pure composition function that can be reviewed in isolation from
any API surface.

---

## D-052 — Report builder input model

**Date:** 2026-06-23 (Phase 7A)
**Decision:** `build_daily_report()` and `build_weekly_report()` accept
already-computed result objects (`PortfolioSnapshot`, `DrawdownResult | None`,
`VolatilityResult | None`, `list[AlertResult]`, `list[JournalEntry]`) as plain function
arguments. The report builder does not access `DataAdapter`, SQLite repositories, CSV
importers, filesystem, network, or the system clock. The caller is responsible for
fetching and pre-filtering all data before invoking the builder.
**Rationale:** Keeping the builder pure and I/O-free makes it trivially testable (no
fixtures), composable with any future orchestration layer, and consistent with the purity
invariant already established for the metrics and alert engines.

---

## D-053 — Report builder output format

**Date:** 2026-06-23 (Phase 7A)
**Decision:** The builder returns frozen dataclasses: `DailyReport` and `WeeklyReport`,
each containing `list[ReportSection]` (system-generated, compliance-checked text blocks)
and `list[JournalEntry]` (user-authored entries carried verbatim, not compliance-scanned).
`ReportSection` holds a `label` and a `body` — both compliance-checked strings.
Rendering, serialisation, and formatting are the caller's responsibility.
**Rationale:** Frozen dataclasses are immutable, safely hashable, and consistent with the
pattern used throughout the project (metrics results, alert results, journal entry).
Separating journal entries from system-generated sections makes the verbatim/not-scanned
boundary unambiguous.

---

## D-054 — Compliance policy for report text

**Date:** 2026-06-23 (Phase 7A)
**Decision:** Every system-generated string placed in a `ReportSection.label` or
`ReportSection.body` must pass `check_compliance()` before the `ReportSection` is
constructed. `ComplianceViolationError` is never caught or rewritten inside the builder —
it propagates to the caller. User-authored `JournalEntry` fields (`action_taken`,
`reasoning`, `hypothesis`, `tags`) are not passed through `check_compliance()` and are
not placed inside any `ReportSection.body`. This is consistent with D-046.
**Rationale:** Compliance is a non-negotiable chokepoint (ARCHITECTURE.md §4).
Hard failure on a violation ensures that non-compliant generated text cannot reach
the user in any form.

---

## D-055 — Alert inclusion policy in reports

**Date:** 2026-06-23 (Phase 7A)
**Decision:** Reports include all evaluated `AlertResult` objects, both fired and
non-fired. The alert summary section shows the status, severity, measured value,
threshold, and explanation for every result passed in.
**Rationale:** Consistent with D-038 (evaluate_alerts returns all results). A non-firing
alert is informative — its absence would be ambiguous. Showing "within threshold" for
non-fired rules gives the user a complete picture of the evaluation.

---

## D-056 — Report date / timestamp policy

**Date:** 2026-06-23 (Phase 7A)
**Decision:** `report_date` (and `week_start` for weekly reports) are caller-provided
ISO-8601 date strings. The report builder does not call `datetime.now()`, `date.today()`,
or any system clock. Both dates are validated with `validate_iso_date()`. For weekly
reports, `week_start` must be on or before `report_date`; violation raises
`InvalidDateError`.
**Rationale:** Consistent with D-031 (valuation date policy). System-clock independence
makes tests deterministic, avoids date-sensitive fragility, and keeps the builder pure.

---

## D-057 — v0.1 closeout boundary

**Date:** 2026-06-23 (Phase 7A)
**Decision:** v0.1 is not complete at the end of Phase 7A. v0.1 is complete only after
Phase 7B (minimal FastAPI routes) is separately approved, implemented, audited, and
accepted. The definition of done for v0.1: all six metrics computed, all four alert rules
evaluated, compliance guard active on all system-generated output, decision journal
operational, daily/weekly report builder complete, minimal read-only API routes functional,
all tests green, architecture invariant green, and all docs updated. Phase 8 is the Tier 3
gate review (paper trading research boundary) — a conscious deliberate decision, not
automatic.
**Rationale:** The API layer is the surface through which the frontend will consume
reports; shipping v0.1 without any API surface would leave the product unusable. Phase 7B
must be completed before v0.1 can be declared done.
