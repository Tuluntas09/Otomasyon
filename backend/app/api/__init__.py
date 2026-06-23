"""FastAPI boundary — read-only report API (Phase 7B).

Exposed routes:
  GET /health
  GET /reports/daily?report_date=YYYY-MM-DD
  GET /reports/weekly?week_start=YYYY-MM-DD&report_date=YYYY-MM-DD

No execution endpoints. No order placement. No broker integration.
No write routes. No scheduled tasks. No external calls.
"""
