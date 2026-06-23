# API_CONTRACT.md

> **This document describes the current read-only API contract only.**
> It is derived from accepted implementation as of Phase 8C (commit `e7e8d63`).
> Do not document planned fields or future behavior here.
> All documented fields and shapes are verified against the source code.

---

## 1. Overview

Otomasyon exposes three read-only HTTP endpoints. All routes are `GET`-only.
No write, delete, or mutation routes exist in any form.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness check — returns service status with no side effects |
| `GET /reports/daily` | Returns a serialised daily report for a caller-supplied date |
| `GET /reports/weekly` | Returns a serialised weekly report for a caller-supplied date range |

**Base path:** Routes are registered under a `/reports` prefix for the report routes.
The full paths are `/health`, `/reports/daily`, and `/reports/weekly`.

**Content-Type:** All responses are `application/json`.

**Authentication:** None. The application is local-first; no auth layer exists.

**Read-only guarantee:** No request to any route modifies the local database, the filesystem,
or any external state. All routes are side-effect-free from the caller's perspective.

---

## 2. Boundary and Safety Notes

These are properties of the current implementation, not aspirational statements.

- **Read-only.** No `POST`, `PUT`, `PATCH`, or `DELETE` routes exist.
- **No broker integration.** The application has no broker client, no broker credentials,
  and no broker abstraction layer.
- **No order placement.** No order — real or simulated — is ever placed, recorded, or
  implied by any route response.
- **No trading credentials.** The application stores no trading API keys, tokens, or
  session credentials.
- **No external market-data API calls.** All data used to compute responses comes from
  the local SQLite database. No HTTP request to any external service is made during
  route handling.
- **No web scraping.** The application does not fetch or parse external web content.
- **No technical indicators.** No moving averages, RSI, MACD, Bollinger bands, or any
  derived indicator is computed or returned.
- **No backtesting.** The application does not simulate historical strategies or
  compute strategy performance metrics.
- **No paper trading or live trading.** No simulated or live position lifecycle exists.
- **Reports describe computed facts only.** Report sections describe measured values,
  threshold comparisons, and data coverage. They do not prescribe actions.
- **Alerts describe threshold conditions only.** An alert section states which rule
  evaluated, whether the threshold was crossed, the measured value, and the threshold.
  No directional action is implied.
- **System-generated report text is compliance-checked.** Every `ReportSection` label
  and body passes through the compliance guard (`check_compliance()`) before being
  stored. `ComplianceViolationError` propagates if any forbidden term is present.
- **User-authored journal text is returned verbatim and not compliance-scanned.**
  `JournalEntry` fields (`action_taken`, `reasoning`, `hypothesis`, `tags`) are the
  user's own words. They are stored and returned without modification or filtering.

---

## 3. Shared Type Definitions

These types appear nested in the report route responses. They are produced by
`dataclasses.asdict()` applied to frozen dataclasses; all field names in the JSON
output match the dataclass field names exactly.

### 3.1 ReportSection

A single labelled text block within a report. All fields are always present.

| Field | JSON type | Nullable | Description |
|---|---|---|---|
| `label` | string | No | Section title. System-generated. Compliance-checked. |
| `body` | string | No | Section content. System-generated. Compliance-checked. Body text may contain newlines (`\n`). |

### 3.2 JournalEntry

A user-authored decision journal record. Fields match the `JournalEntry` frozen dataclass.
User-authored fields (`action_taken`, `reasoning`, `hypothesis`, `tags`) are returned
verbatim without compliance scanning.

| Field | JSON type | Nullable | Description |
|---|---|---|---|
| `id` | integer | No | Auto-assigned database row ID. |
| `entry_date` | string | No | ISO-8601 date the entry was recorded (e.g. `"2025-01-10"`). |
| `action_taken` | string | No | User-authored description of what the user did. Never empty. |
| `reasoning` | string | No | User-authored reasoning text. Never empty. |
| `created_at` | string | No | UTC ISO-8601 timestamp when the row was inserted (e.g. `"2025-01-10T09:00:00+00:00"`). |
| `ticker` | string | Yes | Optional ticker symbol the entry relates to. `null` if not provided. |
| `hypothesis` | string | Yes | Optional user-authored hypothesis text. `null` if not provided. |
| `review_date` | string | Yes | Optional ISO-8601 date for a future review. Must be strictly after `entry_date` if provided. `null` if not provided. |
| `tags` | string | Yes | Optional free-text tags. `null` if not provided. |

### 3.3 TickerQuality

Per-ticker price history depth and local continuity metrics. Part of `DataQualitySummary`.
All fields are always present in the object; nullable fields use JSON `null`.

| Field | JSON type | Nullable | Description |
|---|---|---|---|
| `ticker` | string | No | Ticker symbol for the held position. |
| `price_record_count` | integer | No | Total count of price records for this ticker in the local database, across all dates. |
| `earliest_price_date` | string | Yes | ISO-8601 date of the earliest price record across all dates. `null` if no price records exist. |
| `latest_price_date` | string | Yes | ISO-8601 date of the latest price record across all dates. `null` if no price records exist. |
| `days_since_last_price` | integer | Yes | Calendar days between the most recent price record on or before `report_date` and `report_date` itself. `null` if no price record exists on or before `report_date`. |
| `has_price_on_or_before_report_date` | boolean | No | `true` if at least one price record exists with a date on or before `report_date`. |
| `local_price_date_count_on_or_before_report_date` | integer | No | Count of unique local price dates on or before `report_date`. Duplicate dates are collapsed before counting. |
| `largest_price_date_gap_days` | integer | Yes | Calendar days of the largest consecutive gap between unique local price dates on or before `report_date`. `null` when fewer than two unique local price dates exist on or before `report_date`. |
| `largest_price_date_gap_start` | string | Yes | ISO-8601 date at the start of the largest gap. `null` when `largest_price_date_gap_days` is `null`. |
| `largest_price_date_gap_end` | string | Yes | ISO-8601 date at the end of the largest gap. `null` when `largest_price_date_gap_days` is `null`. |

**Gap tie behavior:** When multiple consecutive gaps share the same length, the earliest
gap (first in ascending date order) is reported.

**Gap scope:** Gap computation uses only local price dates on or before `report_date`.
Future-dated price records are excluded. No exchange-session calendar is applied —
all gaps are in calendar days.

### 3.4 DataQualitySummary

Portfolio-level and per-ticker price history depth summary. Nested under `data_quality`
in both report responses. In Phase 8D, the API always supplies `data_quality`; the field
is `null` only if the builder is called without a `DataQualitySummary` argument, which does
not occur in the current route handlers.

| Field | JSON type | Nullable | Description |
|---|---|---|---|
| `report_date` | string | No | ISO-8601 date used for all quality computations (caller-provided, matches the route's `report_date` parameter). |
| `total_holding_count` | integer | No | Total number of held positions. |
| `priced_holding_count` | integer | No | Number of positions with at least one price record on or before `report_date`. |
| `unpriced_holding_count` | integer | No | `total_holding_count - priced_holding_count`. |
| `coverage_ratio` | float | No | `priced_holding_count / total_holding_count`. `0.0` when `total_holding_count` is `0`. |
| `unpriced_tickers` | array of string | No | Ticker symbols for positions with no price record on or before `report_date`. Empty array when all positions are priced. |
| `ticker_quality` | array of TickerQuality | No | One entry per held position, in the order holdings were loaded. |

---

## 4. Endpoints

### 4.1 GET /health

**Purpose:** Liveness check. Confirms the process is running. No data access.

**Method / Path:** `GET /health`

**Query parameters:** None.

**Response — 200 OK:**

```json
{"status": "ok"}
```

| Field | JSON type | Description |
|---|---|---|
| `status` | string | Always `"ok"`. |

**Error responses:** None under normal conditions. A `500` may occur for unexpected
server errors but has no documented structured body.

**Implementation notes:**
- No database connection is opened.
- No metrics, alerts, or report builder are invoked.
- No side effects of any kind.

---

### 4.2 GET /reports/daily

**Purpose:** Returns a serialised daily report for a single caller-supplied date.
Computes portfolio snapshot, drawdown, volatility proxy, alert evaluation, data quality
diagnostics, and assembles a full report. All computation uses only locally stored data.

**Method / Path:** `GET /reports/daily`

**Query parameters:**

| Parameter | Required | Format | Description |
|---|---|---|---|
| `report_date` | Yes | `YYYY-MM-DD` | ISO-8601 date for which the report is generated. Must be a valid calendar date. |

**Journal entry filter:** The route fetches journal entries where `entry_date` equals
`report_date` exactly (`date_from=report_date, date_to=report_date`).

#### Response shape — 200 OK

The response is produced by `dataclasses.asdict(DailyReport(...))`. All field names
match the frozen dataclass field names exactly.

```
{
  "report_date":     string,           // ISO-8601 date (mirrors the query parameter)
  "report_type":     string,           // always "daily"
  "sections":        [ ReportSection ],// ordered list; see §4.2.1
  "journal_entries": [ JournalEntry ], // entries for report_date; may be empty
  "data_quality":    DataQualitySummary | null  // see §3.4; null only if builder
}                                                // called without quality arg (not
                                                 // the case in current route handler)
```

#### 4.2.1 Daily report section ordering

Sections appear in this fixed order. The `label` values below are exact strings.

| # | Label | Presence | Description |
|---|---|---|---|
| 1 | `"Report"` | Always | Report type, date, and top-level disclaimer statement. |
| 2 | `"Data Coverage"` | Always | Count of priced vs. total positions, list of unpriced tickers. |
| 3 | `"Data Quality Summary"` | When `data_quality` is not `null` | Per-ticker price record counts, unique dates, gap facts, and gap methodology note. |
| 4 | `"Data Quality Caveat"` | When `data_quality` is not `null` **and** `unpriced_holding_count > 0` | Explains which metrics are affected by incomplete price coverage. |
| 5 | `"Metric Definitions"` | Always | Fact-stating definitions of M-001 through M-006. |
| 6 | `"Alert Rule Definitions"` | Always | Threshold conditions for CONC-001, DD-001, VOL-001, COV-001. |
| 7 | `"Portfolio Snapshot"` | Always | Total market value (USD), priced count, total count. |
| 8 | `"Position Weights"` | Always | Per-ticker weight, market value, unrealised change in value (where available). |
| 9 | `"Alert Summary"` | Always | All evaluated alert rules (fired and non-fired), with status, severity, measured value, threshold, and explanation. |
| 10 | `"Journal Entries"` | Always | Count of user-authored entries for `report_date`, or "No entries recorded for this period." |
| 11 | `"Method Note"` | Always | Statement that metrics are computed from supplied data; no prescriptive statements. |
| 12 | `"Disclaimer"` | Always | Standard disclaimer statement. |

**Section count:** 10 sections when no `data_quality` is provided; 11 when `data_quality`
is provided and all holdings are priced; 12 when `data_quality` is provided and at least
one holding is unpriced.

In the current route handler, `data_quality` is always computed and passed to the builder,
so the minimum section count in production is 11 (all priced) or 12 (any unpriced).

#### Error responses

See §6 (API Error Taxonomy) for complete shapes.

| Condition | Status | Shape |
|---|---|---|
| `report_date` missing | 422 | FastAPI-generated validation error (§6.4) |
| `report_date` not a valid ISO-8601 date | 422 | Custom error body with `error: "invalid_date"` (§6.1) |

---

### 4.3 GET /reports/weekly

**Purpose:** Returns a serialised weekly report for a caller-supplied date range.
Computes the same metrics and alerts as the daily route, plus drawdown and volatility
proxy values that appear in weekly-specific sections.

**Method / Path:** `GET /reports/weekly`

**Query parameters:**

| Parameter | Required | Format | Description |
|---|---|---|---|
| `week_start` | Yes | `YYYY-MM-DD` | ISO-8601 start date of the reporting period. Must be on or before `report_date`. |
| `report_date` | Yes | `YYYY-MM-DD` | ISO-8601 end date of the reporting period. |

**Constraint:** `week_start` must be on or before `report_date`. Equal dates are valid.

**Journal entry filter:** The route fetches journal entries where `entry_date` is between
`week_start` and `report_date` inclusive.

**Quality computation:** `data_quality` uses `report_date` (not `week_start`) as the
reference date for all per-ticker coverage and gap computations.

#### Response shape — 200 OK

The response is produced by `dataclasses.asdict(WeeklyReport(...))`.

```
{
  "report_date":     string,           // ISO-8601 end date of the period
  "week_start":      string,           // ISO-8601 start date of the period
  "report_type":     string,           // always "weekly"
  "sections":        [ ReportSection ],// ordered list; see §4.3.1
  "journal_entries": [ JournalEntry ], // entries for week_start..report_date; may be empty
  "data_quality":    DataQualitySummary | null
}
```

#### 4.3.1 Weekly report section ordering

| # | Label | Presence | Description |
|---|---|---|---|
| 1 | `"Report"` | Always | Report type, date, and top-level disclaimer statement. |
| 2 | `"Week Range"` | Always — weekly only | Period start and end dates (`"Period: YYYY-MM-DD to YYYY-MM-DD."`). |
| 3 | `"Data Coverage"` | Always | Count of priced vs. total positions, list of unpriced tickers. |
| 4 | `"Data Quality Summary"` | When `data_quality` is not `null` | Per-ticker price record counts, unique dates, gap facts, and gap methodology note. |
| 5 | `"Data Quality Caveat"` | When `data_quality` is not `null` **and** `unpriced_holding_count > 0` | Explains which metrics are affected by incomplete price coverage. |
| 6 | `"Metric Definitions"` | Always | Fact-stating definitions of M-001 through M-006. |
| 7 | `"Alert Rule Definitions"` | Always | Threshold conditions for CONC-001, DD-001, VOL-001, COV-001. |
| 8 | `"Portfolio Snapshot"` | Always | Total market value (USD), priced count, total count. |
| 9 | `"Drawdown Summary"` | Always — weekly only | M-005 value, peak/current value (USD), window (days), dates in window, coverage ratios. If insufficient data: `"not available — insufficient data."` |
| 10 | `"Volatility Proxy Summary"` | Always — weekly only | M-006 value, window (days), return count, coverage ratios. If insufficient data: `"not available — insufficient data."` |
| 11 | `"Position Weights"` | Always | Per-ticker weight, market value, unrealised change in value (where available). |
| 12 | `"Alert Summary"` | Always | All evaluated alert rules, both fired and non-fired. |
| 13 | `"Journal Entries"` | Always | Count of user-authored entries for the week, or "No entries recorded for this period." |
| 14 | `"Method Note"` | Always | Statement that metrics are computed from supplied data. |
| 15 | `"Disclaimer"` | Always | Standard disclaimer statement. |

**Section count:** 13 (all priced, with data_quality) or 14 (any unpriced, with data_quality).

#### Error responses

| Condition | Status | Shape |
|---|---|---|
| `week_start` or `report_date` missing | 422 | FastAPI-generated validation error (§6.4) |
| `week_start` not a valid ISO-8601 date | 422 | Custom error body with `error: "invalid_date"`, `field: "week_start"` (§6.1) |
| `report_date` not a valid ISO-8601 date | 422 | Custom error body with `error: "invalid_date"`, `field: "report_date"` (§6.1) |
| `week_start` is after `report_date` | 422 | Custom error body with `error: "invalid_date_range"` (§6.3) |

**Validation order:** For the weekly route, `week_start` is validated before `report_date`.
If `week_start` is invalid, the route raises immediately; `report_date` is not checked.

---

## 5. Example JSON Payloads

All examples are structurally accurate against the current implementation. Field values
are illustrative. Section `body` strings are abbreviated with `"..."` where the actual
text is long; the structure and key names are exact.

Ticker names `"AAAA"` and `"BBBB"` are neutral placeholders.

---

### Scenario A — GET /health success

```json
{"status": "ok"}
```

---

### Scenario B — Daily report, complete price support, no Data Quality Caveat

All held positions have price records on or before `report_date`. `unpriced_holding_count`
is 0; the "Data Quality Caveat" section is absent.

```json
{
  "report_date": "2025-01-10",
  "report_type": "daily",
  "sections": [
    {
      "label": "Report",
      "body": "Type: daily | Date: 2025-01-10 | This report describes computed facts only. Not investment advice. The user is solely responsible for their own financial decisions."
    },
    {
      "label": "Data Coverage",
      "body": "2 of 2 position(s) priced. Data coverage: complete."
    },
    {
      "label": "Data Quality Summary",
      "body": "Price history coverage as of 2025-01-10: 2 of 2 position(s) have at least one price record on or before the report date. Coverage ratio: 100.00%.\nAAAA: 5 price record(s), 5 unique local price date(s) on or before 2025-01-10, earliest 2025-01-06, 0 day(s) since last price as of report date. Largest local price-date gap: 3 calendar day(s) between 2025-01-07 and 2025-01-10.\nBBBB: 5 price record(s), 5 unique local price date(s) on or before 2025-01-10, earliest 2025-01-06, 0 day(s) since last price as of report date. Largest local price-date gap: 3 calendar day(s) between 2025-01-07 and 2025-01-10.\nGap diagnostics are based only on local price records available on or before the report date. No exchange-session calendar is applied."
    },
    {
      "label": "Metric Definitions",
      "body": "M-001 (Position Weight): ..."
    },
    {
      "label": "Alert Rule Definitions",
      "body": "CONC-001 (Single-Position Concentration): ..."
    },
    {
      "label": "Portfolio Snapshot",
      "body": "Total market value: 3000.00 USD. Priced positions: 2. Total positions: 2."
    },
    {
      "label": "Position Weights",
      "body": "AAAA: weight 66.67%, market value 2000.00 USD, unrealised change in value: +500.00 USD (+33.33%)\nBBBB: weight 33.33%, market value 1000.00 USD, unrealised change in value: +100.00 USD (+11.11%)"
    },
    {
      "label": "Alert Summary",
      "body": "[CONC-001] Within threshold | Severity: watch | Measured: 0.666700 | Threshold: 0.800000 | ...\n[DD-001] Within threshold | Severity: elevated | Measured: 0.000000 | Threshold: 0.200000 | ...\n[VOL-001] Within threshold | Severity: watch | Measured: 0.000000 | Threshold: 0.050000 | ...\n[COV-001] Within threshold | Severity: informational | Measured: 0.000000 | Threshold: 0.000000 | ..."
    },
    {
      "label": "Journal Entries",
      "body": "No entries recorded for this period."
    },
    {
      "label": "Method Note",
      "body": "Metrics are computed from supplied price and position data. Unavailable data is reported as not available. This report describes measured values only. No prescriptive statements are made by this report."
    },
    {
      "label": "Disclaimer",
      "body": "Not investment advice. Past performance is not indicative of future results. The user is solely responsible for their own financial decisions."
    }
  ],
  "journal_entries": [],
  "data_quality": {
    "report_date": "2025-01-10",
    "total_holding_count": 2,
    "priced_holding_count": 2,
    "unpriced_holding_count": 0,
    "coverage_ratio": 1.0,
    "unpriced_tickers": [],
    "ticker_quality": [
      {
        "ticker": "AAAA",
        "price_record_count": 5,
        "earliest_price_date": "2025-01-06",
        "latest_price_date": "2025-01-10",
        "days_since_last_price": 0,
        "has_price_on_or_before_report_date": true,
        "local_price_date_count_on_or_before_report_date": 5,
        "largest_price_date_gap_days": 3,
        "largest_price_date_gap_start": "2025-01-07",
        "largest_price_date_gap_end": "2025-01-10"
      },
      {
        "ticker": "BBBB",
        "price_record_count": 5,
        "earliest_price_date": "2025-01-06",
        "latest_price_date": "2025-01-10",
        "days_since_last_price": 0,
        "has_price_on_or_before_report_date": true,
        "local_price_date_count_on_or_before_report_date": 5,
        "largest_price_date_gap_days": 3,
        "largest_price_date_gap_start": "2025-01-07",
        "largest_price_date_gap_end": "2025-01-10"
      }
    ]
  }
}
```

---

### Scenario C — Daily report, incomplete price support, Data Quality Caveat present

`BBBB` has no price records on or before `report_date`. `unpriced_holding_count` is 1;
the "Data Quality Caveat" section is present. Gap fields for `BBBB` are `null`.

```json
{
  "report_date": "2025-01-10",
  "report_type": "daily",
  "sections": [
    {
      "label": "Report",
      "body": "Type: daily | Date: 2025-01-10 | This report describes computed facts only. Not investment advice. The user is solely responsible for their own financial decisions."
    },
    {
      "label": "Data Coverage",
      "body": "1 of 2 position(s) priced. Price data not available for: BBBB."
    },
    {
      "label": "Data Quality Summary",
      "body": "Price history coverage as of 2025-01-10: 1 of 2 position(s) have at least one price record on or before the report date. Coverage ratio: 50.00%.\nPositions without price data on or before 2025-01-10: BBBB.\nAAAA: 5 price record(s), 5 unique local price date(s) on or before 2025-01-10, earliest 2025-01-06, 0 day(s) since last price as of report date. Largest local price-date gap: 3 calendar day(s) between 2025-01-07 and 2025-01-10.\nBBBB: no price records.\nGap diagnostics are based only on local price records available on or before the report date. No exchange-session calendar is applied."
    },
    {
      "label": "Data Quality Caveat",
      "body": "Coverage as of 2025-01-10: 1 of 2 position(s) are data-supported. Coverage ratio: 50.00%. 1 position(s) have no price data on or before the report date and are excluded from affected computations.\nAffected metrics:\nM-001 (Position Weight): computed for data-supported positions only. Positions without price data are not included in weight computations.\nM-002 (Portfolio Market Value): computed as the sum of data-supported positions only.\nM-004 (Unrealised Change in Value): not available for positions without price data.\nM-005 (Drawdown from Peak) and M-006 (Volatility Proxy): time-series values are computed from dates where at least one position has price data. Positions without price data are excluded from each date's portfolio value.\nAll figures in this report reflect only the data available in the local database as of 2025-01-10."
    },
    {
      "label": "Metric Definitions",
      "body": "M-001 (Position Weight): ..."
    },
    {
      "label": "Alert Rule Definitions",
      "body": "CONC-001 (Single-Position Concentration): ..."
    },
    {
      "label": "Portfolio Snapshot",
      "body": "Total market value: 2000.00 USD. Priced positions: 1. Total positions: 2."
    },
    {
      "label": "Position Weights",
      "body": "AAAA: weight 100.00%, market value 2000.00 USD, unrealised change in value: +500.00 USD (+33.33%)\nBBBB: price data not available"
    },
    {
      "label": "Alert Summary",
      "body": "[CONC-001] Fired | Severity: watch | Measured: 1.000000 | Threshold: 0.800000 | ...\n[DD-001] Within threshold | Severity: elevated | Measured: 0.000000 | Threshold: 0.200000 | ...\n[VOL-001] Within threshold | Severity: watch | Measured: 0.000000 | Threshold: 0.050000 | ...\n[COV-001] Fired | Severity: informational | Measured: 1.000000 | Threshold: 0.000000 | ..."
    },
    {
      "label": "Journal Entries",
      "body": "No entries recorded for this period."
    },
    {
      "label": "Method Note",
      "body": "Metrics are computed from supplied price and position data. Unavailable data is reported as not available. This report describes measured values only. No prescriptive statements are made by this report."
    },
    {
      "label": "Disclaimer",
      "body": "Not investment advice. Past performance is not indicative of future results. The user is solely responsible for their own financial decisions."
    }
  ],
  "journal_entries": [],
  "data_quality": {
    "report_date": "2025-01-10",
    "total_holding_count": 2,
    "priced_holding_count": 1,
    "unpriced_holding_count": 1,
    "coverage_ratio": 0.5,
    "unpriced_tickers": ["BBBB"],
    "ticker_quality": [
      {
        "ticker": "AAAA",
        "price_record_count": 5,
        "earliest_price_date": "2025-01-06",
        "latest_price_date": "2025-01-10",
        "days_since_last_price": 0,
        "has_price_on_or_before_report_date": true,
        "local_price_date_count_on_or_before_report_date": 5,
        "largest_price_date_gap_days": 3,
        "largest_price_date_gap_start": "2025-01-07",
        "largest_price_date_gap_end": "2025-01-10"
      },
      {
        "ticker": "BBBB",
        "price_record_count": 0,
        "earliest_price_date": null,
        "latest_price_date": null,
        "days_since_last_price": null,
        "has_price_on_or_before_report_date": false,
        "local_price_date_count_on_or_before_report_date": 0,
        "largest_price_date_gap_days": null,
        "largest_price_date_gap_start": null,
        "largest_price_date_gap_end": null
      }
    ]
  }
}
```

---

### Scenario D — Weekly report, journal entries present, data_quality present

`week_start` is 2025-01-06, `report_date` is 2025-01-10. Journal entries for the
period are included. The "Week Range", "Drawdown Summary", and "Volatility Proxy Summary"
sections are weekly-only and always present.

The `journal_entries` array contains user-authored data returned verbatim. The text
shown below is **sample text only** — actual user journal content is not shown or
replaced; it is always returned exactly as stored.

```json
{
  "report_date": "2025-01-10",
  "week_start": "2025-01-06",
  "report_type": "weekly",
  "sections": [
    {
      "label": "Report",
      "body": "Type: weekly | Date: 2025-01-10 | This report describes computed facts only. Not investment advice. The user is solely responsible for their own financial decisions."
    },
    {
      "label": "Week Range",
      "body": "Period: 2025-01-06 to 2025-01-10."
    },
    {
      "label": "Data Coverage",
      "body": "2 of 2 position(s) priced. Data coverage: complete."
    },
    {
      "label": "Data Quality Summary",
      "body": "Price history coverage as of 2025-01-10: 2 of 2 position(s) have at least one price record on or before the report date. Coverage ratio: 100.00%.\nAAAA: 5 price record(s), 5 unique local price date(s) on or before 2025-01-10, earliest 2025-01-06, 0 day(s) since last price as of report date. Largest local price-date gap: 3 calendar day(s) between 2025-01-07 and 2025-01-10.\nBBBB: 5 price record(s), 5 unique local price date(s) on or before 2025-01-10, earliest 2025-01-06, 0 day(s) since last price as of report date. Largest local price-date gap: 3 calendar day(s) between 2025-01-07 and 2025-01-10.\nGap diagnostics are based only on local price records available on or before the report date. No exchange-session calendar is applied."
    },
    {
      "label": "Metric Definitions",
      "body": "M-001 (Position Weight): ..."
    },
    {
      "label": "Alert Rule Definitions",
      "body": "CONC-001 (Single-Position Concentration): ..."
    },
    {
      "label": "Portfolio Snapshot",
      "body": "Total market value: 3000.00 USD. Priced positions: 2. Total positions: 2."
    },
    {
      "label": "Drawdown Summary",
      "body": "Drawdown from peak (M-005): 0.00% | Peak value: 3000.00 USD | Current value: 3000.00 USD | Window: 90 days | Dates in window: 5 | Min coverage ratio: 100.00% | Latest coverage ratio: 100.00%."
    },
    {
      "label": "Volatility Proxy Summary",
      "body": "Volatility proxy (M-006): 0.005000 (population std dev of daily percentage returns) | Window: 30 days | Returns computed: 4 | Min coverage ratio: 100.00% | Latest coverage ratio: 100.00%."
    },
    {
      "label": "Position Weights",
      "body": "AAAA: weight 66.67%, market value 2000.00 USD, unrealised change in value: +500.00 USD (+33.33%)\nBBBB: weight 33.33%, market value 1000.00 USD, unrealised change in value: +100.00 USD (+11.11%)"
    },
    {
      "label": "Alert Summary",
      "body": "[CONC-001] Within threshold | Severity: watch | Measured: 0.666700 | Threshold: 0.800000 | ...\n[DD-001] Within threshold | Severity: elevated | Measured: 0.000000 | Threshold: 0.200000 | ...\n[VOL-001] Within threshold | Severity: watch | Measured: 0.005000 | Threshold: 0.050000 | ...\n[COV-001] Within threshold | Severity: informational | Measured: 0.000000 | Threshold: 0.000000 | ..."
    },
    {
      "label": "Journal Entries",
      "body": "1 user-authored entry recorded for this period."
    },
    {
      "label": "Method Note",
      "body": "Metrics are computed from supplied price and position data. Unavailable data is reported as not available. This report describes measured values only. No prescriptive statements are made by this report."
    },
    {
      "label": "Disclaimer",
      "body": "Not investment advice. Past performance is not indicative of future results. The user is solely responsible for their own financial decisions."
    }
  ],
  "journal_entries": [
    {
      "id": 1,
      "entry_date": "2025-01-08",
      "action_taken": "[sample — actual user text returned verbatim]",
      "reasoning": "[sample — actual user text returned verbatim]",
      "created_at": "2025-01-08T10:30:00+00:00",
      "ticker": "AAAA",
      "hypothesis": null,
      "review_date": "2025-04-08",
      "tags": null
    }
  ],
  "data_quality": {
    "report_date": "2025-01-10",
    "total_holding_count": 2,
    "priced_holding_count": 2,
    "unpriced_holding_count": 0,
    "coverage_ratio": 1.0,
    "unpriced_tickers": [],
    "ticker_quality": [
      {
        "ticker": "AAAA",
        "price_record_count": 5,
        "earliest_price_date": "2025-01-06",
        "latest_price_date": "2025-01-10",
        "days_since_last_price": 0,
        "has_price_on_or_before_report_date": true,
        "local_price_date_count_on_or_before_report_date": 5,
        "largest_price_date_gap_days": 3,
        "largest_price_date_gap_start": "2025-01-07",
        "largest_price_date_gap_end": "2025-01-10"
      },
      {
        "ticker": "BBBB",
        "price_record_count": 5,
        "earliest_price_date": "2025-01-06",
        "latest_price_date": "2025-01-10",
        "days_since_last_price": 0,
        "has_price_on_or_before_report_date": true,
        "local_price_date_count_on_or_before_report_date": 5,
        "largest_price_date_gap_days": 3,
        "largest_price_date_gap_start": "2025-01-07",
        "largest_price_date_gap_end": "2025-01-10"
      }
    ]
  }
}
```

---

## 6. API Error Taxonomy

This section documents the **current** error response behavior. No error shapes are
standardised or changed in Phase 8D. The behaviors described here are verified against
the source code.

There are two distinct error response shapes in the current implementation: one
produced by the application's custom validation logic and one produced by FastAPI's
built-in parameter validation.

---

### 6.1 Invalid date format — custom (both routes)

**Trigger:** `report_date` or `week_start` is present but cannot be parsed as a valid
ISO-8601 date by `datetime.date.fromisoformat()`.

**Status:** `422 Unprocessable Entity`

**Source:** Custom `_parse_date()` function in `backend/app/api/routes/reports.py`,
which raises `fastapi.HTTPException(status_code=422, detail={...})`.

**Response shape:** The `detail` key contains a **dict** (not a list).

```json
{
  "detail": {
    "error": "invalid_date",
    "field": "report_date",
    "value": "not-a-date",
    "message": "report_date must be a valid ISO-8601 date (YYYY-MM-DD)."
  }
}
```

| Field | Description |
|---|---|
| `error` | Always `"invalid_date"` for this error type. |
| `field` | The parameter name that failed: `"report_date"` or `"week_start"`. |
| `value` | The value that was supplied and rejected. |
| `message` | Human-readable description. Template: `"{field} must be a valid ISO-8601 date (YYYY-MM-DD)."` |

**Example — invalid `week_start`:**

```json
{
  "detail": {
    "error": "invalid_date",
    "field": "week_start",
    "value": "2025-13-01",
    "message": "week_start must be a valid ISO-8601 date (YYYY-MM-DD)."
  }
}
```

---

### 6.2 Date value rejected by Python — custom (both routes)

Same shape as §6.1. `datetime.date.fromisoformat()` rejects calendar-invalid dates
(e.g., month 13, day 32) as well as non-date strings. Both cases produce the same
`"invalid_date"` error with the same shape.

---

### 6.3 week_start after report_date — custom (weekly route only)

**Trigger:** Both `week_start` and `report_date` are individually valid ISO-8601 dates
but `week_start` is strictly after `report_date`.

**Status:** `422 Unprocessable Entity`

**Source:** Explicit range check in `get_weekly_report()` after both dates are parsed.

**Response shape:** `detail` is a **dict**. Note: this error shape does **not** include
a `value` field, unlike the `invalid_date` error.

```json
{
  "detail": {
    "error": "invalid_date_range",
    "field": "week_start",
    "message": "week_start must be on or before report_date."
  }
}
```

| Field | Description |
|---|---|
| `error` | Always `"invalid_date_range"` for this error type. |
| `field` | Always `"week_start"`. |
| `message` | Always `"week_start must be on or before report_date."` |

---

### 6.4 Missing required query parameter — FastAPI-generated (both routes)

**Trigger:** A required query parameter (`report_date`, `week_start`) is absent from
the request.

**Status:** `422 Unprocessable Entity`

**Source:** FastAPI's built-in request validation (Pydantic), which runs before the
route handler is called.

**Response shape:** The `detail` key contains a **list** of validation error objects.
This is distinct from the custom error shapes above, where `detail` is a dict.

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["query", "report_date"],
      "msg": "Field required",
      "input": null,
      "url": "https://errors.pydantic.dev/2.10/v/missing"
    }
  ]
}
```

| Field | Description |
|---|---|
| `type` | Pydantic error type identifier (e.g. `"missing"`). |
| `loc` | Array indicating the error location: `["query", "<param_name>"]`. |
| `msg` | Human-readable Pydantic error message. |
| `input` | The value received (`null` for missing params). |
| `url` | Link to Pydantic error documentation. Exact URL varies by Pydantic version. |

**Note for consumers:** When both `week_start` and `report_date` are missing from a
weekly request, FastAPI returns a single 422 response with both errors in the `detail`
array.

---

### 6.5 Error shape disambiguation

To distinguish custom errors from FastAPI-generated errors:

| `detail` is… | Error source |
|---|---|
| A **dict** with an `"error"` key | Custom application error (§6.1 or §6.3) |
| A **list** of objects with `"type"` and `"loc"` keys | FastAPI-generated validation error (§6.4) |

---

### 6.6 Other status codes

| Status | Condition |
|---|---|
| `200` | Successful response (all routes). |
| `422` | Parameter validation failure (all routes; see §6.1–6.4). |
| `500` | Unhandled server error. Body is FastAPI's default error format; no structured application shape is defined for this case. |

No `404` is returned by the current implementation — unknown route paths are handled
by FastAPI's default routing, which may return its own error format.

---

## 7. Serialisation Notes

- All response bodies are serialised by `dataclasses.asdict()` applied to frozen
  dataclasses (`DailyReport`, `WeeklyReport`). `asdict()` recurses into nested frozen
  dataclasses (`DataQualitySummary`, `TickerQuality`, `ReportSection`, `JournalEntry`)
  and converts them to plain dicts. Python `None` becomes JSON `null`.
- Field order in the JSON output follows Python dataclass field declaration order.
  JSON consumers should not rely on key ordering.
- Floating-point values (`coverage_ratio`, metric values, portfolio values) are Python
  `float` serialised by FastAPI's JSON encoder. No rounding is applied by the route
  handler.
- `created_at` on `JournalEntry` is a UTC ISO-8601 timestamp including timezone offset
  (e.g. `"2025-01-08T10:30:00+00:00"`). It is not a plain date string.

---

## 8. Phase Reference

| Field or feature | Introduced |
|---|---|
| `GET /health`, `GET /reports/daily`, `GET /reports/weekly` | Phase 7B |
| `sections`, `journal_entries`, `report_date`, `report_type` | Phase 7B |
| `week_start` (weekly only) | Phase 7B |
| `"Report"`, `"Data Coverage"`, `"Portfolio Snapshot"`, `"Position Weights"`, `"Alert Summary"`, `"Journal Entries"`, `"Method Note"`, `"Disclaimer"` sections | Phase 7A / 7B |
| `"Week Range"`, `"Drawdown Summary"`, `"Volatility Proxy Summary"` sections | Phase 7A / 7B |
| `data_quality` top-level key | Phase 8A |
| `DataQualitySummary`: `report_date`, `total_holding_count`, `priced_holding_count`, `unpriced_holding_count`, `coverage_ratio`, `unpriced_tickers`, `ticker_quality` | Phase 8A |
| `TickerQuality`: `ticker`, `price_record_count`, `earliest_price_date`, `latest_price_date`, `days_since_last_price`, `has_price_on_or_before_report_date` | Phase 8A |
| `"Data Quality Summary"` section | Phase 8A |
| `"Metric Definitions"`, `"Alert Rule Definitions"`, `"Data Quality Caveat"` sections | Phase 8B |
| `TickerQuality`: `local_price_date_count_on_or_before_report_date`, `largest_price_date_gap_days`, `largest_price_date_gap_start`, `largest_price_date_gap_end` | Phase 8C |

---

*This document describes the accepted API contract as of Phase 8C. It is a documentation
artefact. No application code was changed to produce it. Future phases that add fields
or routes must update this document as part of their acceptance criteria.*
