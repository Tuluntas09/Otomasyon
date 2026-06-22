# Otomasyon

**Personal finance research and decision-support instrument.**

> **Disclaimer:** This tool is not investment advice. It measures, records, and notifies.
> It never advises, never trades, and never claims profit. The user is solely responsible
> for their own financial decisions.

---

## What it is

Otomasyon is a local-first tool that helps a single user:

- See the real risk shape of one portfolio.
- Record the reasoning behind their own decisions.
- Receive explainable, rule-based alerts when measurable thresholds are crossed.

## What it is not

It is **not** a trading bot, signal service, advisor, broker client, backtester, news engine,
or arbitrage scanner. Profit is treated as an unproven hypothesis the system helps test —
never as a promised outcome.

---

## Stack

- **Backend:** Python / FastAPI / SQLite
- **Frontend:** React / Vite
- **Tests:** pytest

## Status

- Phase 0 (docs): ✅ complete
- Phase 1 (empty skeleton): ✅ complete
- Phase 2 (data model + local storage): ⛔ not started

## Development

```bash
cd backend
python -m pytest
```

---

*See `PROJECT_BRAIN.md` for full orientation and `docs/` for specifications.*
