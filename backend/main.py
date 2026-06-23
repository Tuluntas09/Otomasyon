"""Entry point — exposes the ASGI app for uvicorn.

To run the server manually (uvicorn must be installed separately):
  pip install uvicorn
  uvicorn main:app --reload

Uvicorn is not a declared project dependency in Phase 7B.
"""

from app.api.app import app  # noqa: F401 — re-exported for uvicorn
