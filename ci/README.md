# CI

Continuous integration configuration — implementation deferred.

## Planned pipeline (future)

1. `cd backend && python -m pytest` — full test suite including architecture invariant.
2. Lint / type-check (mypy or pyright).
3. Frontend build check (`npm run build` from `frontend/`).

## Gate

The architecture invariant test (`tests/architecture/test_no_broker_no_execution.py`)
must pass on every commit. CI failure on this test is a hard block — not a warning.

## Status

Not wired. No CI provider chosen. Will be added when the project has a remote repository.
