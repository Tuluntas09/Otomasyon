"""Health route — minimal smoke-test endpoint.

GET /health

Returns {"status": "ok"}.
No DB access. No metrics. No external calls.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    """Return service status. No data access."""
    return {"status": "ok"}
