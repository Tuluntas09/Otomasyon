"""Phase 3 unit test placeholders — skipped until Phase 3 (CSV adapter) is implemented.

These stubs define the expected test surface. They are explicitly skipped with a phase-gate
reason. Do not delete them; replace the skip decorator with real logic in Phase 3.
"""

import pytest


@pytest.mark.skip(reason="Phase gate: CSV adapter not implemented until Phase 3.")
def test_valid_holdings_csv_parses_correctly() -> None:
    """A well-formed holdings CSV is parsed into Holding objects without error."""


@pytest.mark.skip(reason="Phase gate: CSV adapter not implemented until Phase 3.")
def test_csv_with_duplicate_ticker_raises_error() -> None:
    """A holdings CSV containing a duplicate ticker raises DuplicateTickerError."""


@pytest.mark.skip(reason="Phase gate: CSV adapter not implemented until Phase 3.")
def test_csv_with_non_usd_currency_raises_error() -> None:
    """A holdings CSV row with non-USD currency raises CurrencyError."""
