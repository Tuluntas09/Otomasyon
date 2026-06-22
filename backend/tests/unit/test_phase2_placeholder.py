"""Phase 2 unit test placeholders — skipped until Phase 2 is implemented.

These stubs define the expected test surface. They are explicitly skipped with a phase-gate
reason. Do not delete them; replace the skip decorator with real logic in Phase 2.
"""

import pytest


@pytest.mark.skip(reason="Phase gate: domain models not implemented until Phase 2.")
def test_holding_model_valid_construction() -> None:
    """A valid Holding with positive quantity and USD currency constructs without error."""


@pytest.mark.skip(reason="Phase gate: validation layer not implemented until Phase 2.")
def test_negative_quantity_raises_error() -> None:
    """Negative quantity input raises NegativeQuantityError."""


@pytest.mark.skip(reason="Phase gate: validation layer not implemented until Phase 2.")
def test_non_usd_currency_raises_error() -> None:
    """Non-USD currency input raises CurrencyError."""
