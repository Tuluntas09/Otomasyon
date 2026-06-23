# Phase 5 Closeout Report

**Date:** 2026-06-23
**Phase:** 5 — Alerts + compliance guard
**Status:** Complete — awaiting human review

---

## 1. Decisions recorded

| ID | Decision |
|---|---|
| D-036 | Alert engine boundary: receives already-computed metric result objects; no I/O; returns AlertResult list. |
| D-037 | AlertConfig: frozen caller-provided thresholds with conservative defaults (concentration 0.25, drawdown 0.15, volatility 0.02, max_unpriced_holdings 0). |
| D-038 | AlertResult schema: frozen dataclass; evaluate_alerts returns results for all rules, not only fired ones. |
| D-039 | Compliance guard: raises ComplianceViolationError listing all violations; never rewrites or sanitizes text. |
| D-040 | Compliance chokepoint: every alert explanation passes check_compliance inside evaluate_alerts before AlertResult is constructed. |
| D-041 | Severity labels: informational, watch, elevated only. No urgent/critical/action-oriented labels. |
| D-042 | Compliance matching: whole-word \b for single terms, bounded phrase for multi-word; false-positive protections verified by \b semantics. |
| D-043 | Alert threshold equality: strict greater-than only. metric_value == threshold does not fire. |

---

## 2. Files created

| File | Purpose |
|---|---|
| `backend/app/compliance/guard.py` | `ComplianceViolation` dataclass; `check_compliance()`; 28 forbidden English and Turkish terms/phrases |
| `backend/app/alerts/results.py` | `AlertConfig`, `AlertResult` frozen dataclasses |
| `backend/app/alerts/rules.py` | `evaluate_alerts()`; four rule evaluators: `_evaluate_conc`, `_evaluate_dd`, `_evaluate_vol`, `_evaluate_cov`; `_severity` helper |
| `backend/tests/unit/test_compliance.py` | Compliance guard unit tests |
| `backend/tests/unit/test_alerts.py` | Alert engine unit and boundary tests |
| `docs/reports/PHASE5_CLOSEOUT.md` | This file |

---

## 3. Files modified

| File | Change |
|---|---|
| `backend/app/core/exceptions.py` | Added `ComplianceViolationError` (inherits `OtomasyonError`; exposes `.violations` list) |
| `backend/app/compliance/__init__.py` | Re-exports `ComplianceViolation`, `ComplianceViolationError`, `check_compliance` |
| `backend/app/alerts/__init__.py` | Re-exports `AlertConfig`, `AlertResult`, `evaluate_alerts` |
| `docs/DECISIONS.md` | Appended D-036 through D-043 |
| `docs/ROADMAP.md` | Phase 5 status updated to complete; key deliverables and acceptance criteria added |
| `PROJECT_BRAIN.md` | Phase 5 status updated; D-036–D-043 added to decisions index; phase completion summary appended |

---

## 4. Alert rules implemented

### CONC-001 — Single-position concentration
- Per-position evaluation for all positions with `weight is not None`.
- `fired = weight > config.concentration_ceiling` (strict greater-than, D-043).
- If no priced positions: one informational result with `metric_value=0.0, ticker=None`.
- If no position fires: one informational summary result with `ticker=None`.
- If one or more fire: one `AlertResult` per breaching position with `ticker` populated.

### DD-001 — Drawdown from peak
- Input: `DrawdownResult | None`.
- `None` → informational result with `metric_value=0.0`.
- `fired = drawdown.drawdown > config.drawdown_ceiling` (strict greater-than, D-043).
- `ticker=None` always.

### VOL-001 — Volatility proxy
- Input: `VolatilityResult | None`.
- `None` → informational result with `metric_value=0.0`.
- `fired = volatility.volatility_proxy > config.volatility_ceiling` (strict, D-043).
- `ticker=None` always.

### COV-001 — Missing price coverage
- `count = len(snapshot.unpriced_tickers)`.
- `fired = count > config.max_unpriced_holdings` (strict, D-043).
- `metric_value = float(count)`, `threshold = float(config.max_unpriced_holdings)`.
- `ticker=None` always.

---

## 5. Compliance guard behavior

- **Guard module:** `backend/app/compliance/guard.py`.
- **Forbidden terms:** 16 English single-word terms + 5 Turkish single-word terms + 11 English phrases + 7 Turkish phrases = 39 total patterns.
- **Matching:** `re.IGNORECASE | re.UNICODE`; `\b<term>\b` for all patterns.
- **False positives prevented:** "threshold" does not trigger "hold"; "glossy" does not trigger "loss"; "total" and "capital" do not trigger Turkish "al" — all by standard `\b` word-boundary semantics.
- **Empty input:** passes silently.
- **Compliant input:** passes silently.
- **Non-compliant input:** raises `ComplianceViolationError` with `.violations` listing all matched terms and their context snippets.
- **No rewriting:** the guard never modifies the input text.

---

## 6. Threshold equality behavior

All four rules use strict `>`. The condition `metric_value == threshold` evaluates to `False` for `fired`. Confirmed by explicit tests:
- `test_conc_does_not_fire_at_exact_threshold`
- `test_dd_does_not_fire_at_exact_threshold`
- `test_vol_does_not_fire_at_exact_threshold`
- `test_cov_does_not_fire_when_count_equals_max`

All exact-equality tests assert `fired=False` and `severity="informational"`.

---

## 7. Severity behavior

| Condition | Severity |
|---|---|
| `fired=False` | `"informational"` |
| `fired=True` and `threshold == 0.0` | `"watch"` (2× undefined) |
| `fired=True` and `value > 2 * threshold` | `"elevated"` |
| `fired=True` otherwise | `"watch"` |

No other severity labels are used. `"urgent"`, `"critical"`, and action-oriented labels are absent.

---

## 8. Test result

```
313 passed, 0 skipped in 0.36s
```

- 222 tests carried forward from Phases 1–4: **all PASSED**
- 91 new Phase 5 tests: **all PASSED**
- Architecture invariant (`test_no_broker_no_execution.py`): **PASSED**
- No tests from prior phases deleted or weakened.
- `pyproject.toml` `dependencies = []` — unchanged.

New test breakdown:
- `test_compliance.py`: 53 tests (clean/empty, all English terms, all Turkish terms, multiple violations, context fields, all alert templates)
- `test_alerts.py`: 38 tests (dataclass structure, default thresholds, all four rules, exact-equality, severity, custom config, compliance integration, boundary/purity)

---

## 9. Commit hash

Committed as: `feat: add phase 5 alert rules and compliance guard`
*(hash recorded after git commit)*

---

## 10. Confirmation: every alert explanation passes compliance guard

Every explanation string is passed through `check_compliance()` inside `evaluate_alerts()`, before `AlertResult` is constructed. This is verified both by:
- Code structure: all six explanation-producing code paths call `check_compliance(explanation)` before `AlertResult(...)`.
- Tests: `test_every_explanation_passes_compliance` and `test_every_explanation_passes_compliance_all_unfired` exercise all templates end-to-end via `check_compliance` after the results are returned.

No `AlertResult` object can exist in the system with an unchecked explanation.

---

## 11. Confirmation: out-of-scope items not implemented

The following are absent from all new code:

- Notification delivery (email, SMS, push)
- Scheduled jobs or cron triggers
- FastAPI routes or HTTP layer
- Frontend UI
- Decision journal
- Report generation
- CSV parsing
- SQLite persistence changes
- External market-data API calls
- HTTP clients or web scraping
- Technical indicators
- Backtesting, paper trading, live trading
- Broker integration or order placement
- Buy/sell/hold/target-price/profit/opportunity language in generated copy
- Metrics engine changes (no bugs found requiring modification)

---

## 12. Deviations from the Phase 5 implementation prompt

None. All rules, thresholds, severity labels, explanation templates, compliance terms, exact-equality behavior, frozen dataclasses, boundary constraints, and documentation requirements were implemented as specified.

---

*End of Phase 5 closeout report.*
