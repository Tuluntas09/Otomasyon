"""Phase 2 integration test placeholders — skipped until Phase 2 is implemented.

These stubs define the expected test surface against an in-memory SQLite database.
They are explicitly skipped with a phase-gate reason. Do not delete them; replace the
skip decorator with real logic in Phase 2.
"""

import pytest


@pytest.mark.skip(reason="Phase gate: SQLite repositories not implemented until Phase 2.")
def test_holding_round_trips_through_repository() -> None:
    """A Holding inserted via HoldingsRepo is returned correctly by get_holdings()."""


@pytest.mark.skip(reason="Phase gate: SQLite repositories not implemented until Phase 2.")
def test_duplicate_ticker_rejected_by_repository() -> None:
    """Inserting a duplicate ticker via HoldingsRepo raises DuplicateTickerError."""


@pytest.mark.skip(reason="Phase gate: SQLite repositories not implemented until Phase 2.")
def test_price_record_upsert_is_idempotent() -> None:
    """Re-inserting a price record for the same (ticker, date) updates without error."""
