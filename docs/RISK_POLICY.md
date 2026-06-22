# RISK_POLICY.md

**Safety constitution for Otomasyon. When this document conflicts with any other document,
this document wins.**

---

## 1. One-line identity

This system is a **research and decision-support instrument**. It reads data, computes
facts, and notifies the user. It never acts on a market, advises a user, or claims profit.

---

## 2. The four-tier capability model

Tier promotion is irreversible within a version — once a higher tier is reached, the
system must maintain all lower-tier guarantees.

| Tier | Capability | v0.1 status |
|---|---|---|
| 1 — Analysis | Compute and display metrics | ✅ in scope |
| 2 — Alerting | Notify on explainable threshold rules | ✅ in scope |
| 3 — Paper trading | Simulate positions / P&L for hypothesis testing | ❌ Phase 8 research boundary |
| 4 — Live trading | Place real orders through a broker | ❌ off-roadmap |

**v0.1 = Tiers 1 and 2 only.**

Moving from Tier 2 to Tier 3 requires a conscious, dated `DECISIONS.md` entry and explicit
human approval. Moving to Tier 4 is off-roadmap.

---

## 3. Hard prohibitions (cannot be overridden by any phase gate)

1. **No order placement** — real or simulated — through any code path.
2. **No broker integration** — no broker credentials, no broker API clients.
3. **No buy / sell / hold / target-price language** in any system-generated user-facing copy.
4. **No profit claims, guaranteed-return claims, or opportunity-to-profit claims.**
5. **No advisory output** — the system describes facts; the user draws conclusions.
6. **No execution endpoints** in the API layer, ever.
7. **No trading credentials** stored, transmitted, or referenced.
8. **No technical trade signals** (RSI crossovers, MA signals, etc.) generated or displayed.
9. **No news scraping or sentiment analysis** used to suggest action.
10. **No arbitrage detection** or cross-asset opportunity scanning.

---

## 4. Data input safety

- USD only. Non-USD inputs raise a typed `CurrencyError` and are excluded — never silently
  converted or summed.
- Negative quantities raise `NegativeQuantityError`. No short positions.
- Duplicate tickers raise `DuplicateTickerError`. No silent merging.
- Single portfolio only. No multi-portfolio aggregation.

---

## 5. Alerts safety

Alerts must:
- State which named rule fired and which threshold was crossed.
- Use measured, factual language.
- Never include the words buy, sell, hold, recommend, suggest, or action.
- Never include directional price predictions.

See `ALERT_POLICY.md` for exact examples.

---

## 6. AI usage limits

If AI-generated text appears anywhere in the system:
- It must pass through the compliance guard before reaching the user.
- It must not be the source of a trade decision, directional view, or profit claim.
- It is permitted to summarize or explain computed facts in neutral language only.

---

## 7. Automation ceiling

The maximum automation level is: **read → compute → notify**.

The system may never autonomously: rebalance, place orders, cancel orders, modify positions,
or take any action that changes a market position.

---

## 8. Disclaimer

> Not investment advice. Past performance is not indicative of future results. The user is
> solely responsible for their own financial decisions.

This disclaimer must appear in the README and in any report header.
