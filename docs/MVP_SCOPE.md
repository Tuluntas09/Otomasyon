# MVP_SCOPE.md

## Locked v0.1 boundary

This document is the authoritative in/out list for v0.1. Items marked OUT are either
deferred to a later version or off-roadmap entirely. The boundary is locked — expanding it
requires a new `DECISIONS.md` entry and human review.

---

### IN (v0.1)

- **Watchlist** — a list of tickers the user wants to monitor.
- **Single-portfolio input** — manual entry or CSV upload of holdings (ticker, quantity,
  cost basis). One portfolio only. USD only. No negative quantities. No duplicate tickers.
- **EOD price ingestion** — end-of-day prices loaded from CSV files. No live feed.
- **Risk and exposure metrics** — concentration by position, portfolio-level volatility
  proxy, drawdown from peak, allocation by sector (if provided). See `METRICS_SPEC.md`.
- **Decision journal** — append-only log of the user's own reasoning. Not a trade log.
  See `JOURNAL_SCHEMA.md`.
- **Explainable threshold alerts** — rule-based notifications when a measurable threshold is
  crossed (e.g., single-position weight exceeds X%). Alerts describe; they never prescribe.
  See `ALERT_POLICY.md`.
- **Daily / weekly summary reports** — human-readable summaries of current portfolio state
  and any fired alerts.

---

### OUT (deferred or off-roadmap)

| Item | Notes |
|---|---|
| Live / real-time price feeds | v0.2+ |
| Broker API integration | Off-roadmap |
| Order placement (real or simulated) | Off-roadmap |
| Paper trading | Phase 8 research boundary — not v0.1 |
| Backtesting | Off-roadmap |
| Technical indicators (MA, RSI, etc.) | Off-roadmap |
| Buy / sell / hold signals | Off-roadmap |
| News scraping / sentiment | Off-roadmap |
| Arbitrage detection | Off-roadmap |
| Multi-currency aggregation | v0.2+ |
| Multi-portfolio | v0.2+ |
| Non-USD instruments (BIST, crypto, FX) | v0.2+ |
| Auth / user accounts | v0.2+ |
| Cloud deployment | v0.2+ |
| ML-based predictions | Off-roadmap |

---

### Constraints (non-negotiable for v0.1)

1. USD only — non-USD inputs are rejected, not converted.
2. Single portfolio — no `portfolio_id` in schema.
3. No negative quantities — short positions are not supported.
4. No duplicate tickers — one row per ticker.
5. No advisory language in any system output.
6. All system-generated text passes through the compliance guard (Phase 5+).
