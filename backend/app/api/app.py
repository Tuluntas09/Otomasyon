"""FastAPI application instance — Otomasyon read-only report API.

Mounts:
  GET /health              — smoke-test; no data access
  GET /reports/daily       — daily report for a given date
  GET /reports/weekly      — weekly report for a given date range

No write endpoints. No execution endpoints. No broker integration.
No scheduled tasks. No external calls.
"""

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.reports import router as reports_router

app = FastAPI(
    title="Otomasyon API",
    description=(
        "Read-only research and decision-support API. "
        "Returns computed portfolio metrics and reports. "
        "Not investment advice."
    ),
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(reports_router, prefix="/reports")
