"""Unit tests for the decision journal domain model and validation (Phase 6)."""

import dataclasses

import pytest

from app.core.exceptions import (
    InvalidDateError,
    InvalidTickerError,
    JournalValidationError,
    ValidationError,
)
from app.journal.models import JournalEntry, validate_new_entry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_DATE = "2026-01-15"
_LATER_DATE = "2026-02-01"
_ACTION = "Reduced position size"
_REASONING = "Allocation exceeded personal ceiling after recent run-up"


# ---------------------------------------------------------------------------
# Valid entries
# ---------------------------------------------------------------------------


def test_valid_minimal_entry_passes() -> None:
    validate_new_entry(entry_date=_VALID_DATE, action_taken=_ACTION, reasoning=_REASONING)


def test_valid_entry_with_ticker() -> None:
    validate_new_entry(
        entry_date=_VALID_DATE,
        action_taken=_ACTION,
        reasoning=_REASONING,
        ticker="AAPL",
    )


def test_valid_entry_with_all_fields() -> None:
    validate_new_entry(
        entry_date=_VALID_DATE,
        action_taken=_ACTION,
        reasoning=_REASONING,
        ticker="MSFT",
        hypothesis="Expect lower volatility over next 30 days",
        review_date=_LATER_DATE,
        tags="rebalance,tech",
    )


# ---------------------------------------------------------------------------
# action_taken validation
# ---------------------------------------------------------------------------


def test_empty_action_taken_raises() -> None:
    with pytest.raises(JournalValidationError):
        validate_new_entry(entry_date=_VALID_DATE, action_taken="", reasoning=_REASONING)


def test_whitespace_action_taken_raises() -> None:
    with pytest.raises(JournalValidationError):
        validate_new_entry(entry_date=_VALID_DATE, action_taken="   ", reasoning=_REASONING)


# ---------------------------------------------------------------------------
# reasoning validation
# ---------------------------------------------------------------------------


def test_empty_reasoning_raises() -> None:
    with pytest.raises(JournalValidationError):
        validate_new_entry(entry_date=_VALID_DATE, action_taken=_ACTION, reasoning="")


def test_whitespace_reasoning_raises() -> None:
    with pytest.raises(JournalValidationError):
        validate_new_entry(entry_date=_VALID_DATE, action_taken=_ACTION, reasoning="\t\n")


# ---------------------------------------------------------------------------
# entry_date validation
# ---------------------------------------------------------------------------


def test_invalid_entry_date_raises() -> None:
    with pytest.raises(InvalidDateError):
        validate_new_entry(entry_date="not-a-date", action_taken=_ACTION, reasoning=_REASONING)


# ---------------------------------------------------------------------------
# ticker validation
# ---------------------------------------------------------------------------


def test_invalid_ticker_raises() -> None:
    with pytest.raises(InvalidTickerError):
        validate_new_entry(
            entry_date=_VALID_DATE,
            action_taken=_ACTION,
            reasoning=_REASONING,
            ticker="123invalid",
        )


def test_ticker_none_is_valid() -> None:
    validate_new_entry(
        entry_date=_VALID_DATE,
        action_taken=_ACTION,
        reasoning=_REASONING,
        ticker=None,
    )


# ---------------------------------------------------------------------------
# review_date validation
# ---------------------------------------------------------------------------


def test_invalid_review_date_raises() -> None:
    with pytest.raises(InvalidDateError):
        validate_new_entry(
            entry_date=_VALID_DATE,
            action_taken=_ACTION,
            reasoning=_REASONING,
            review_date="bad-date",
        )


def test_review_date_before_entry_date_raises() -> None:
    with pytest.raises(JournalValidationError):
        validate_new_entry(
            entry_date=_VALID_DATE,
            action_taken=_ACTION,
            reasoning=_REASONING,
            review_date="2026-01-01",
        )


def test_review_date_equal_entry_date_raises() -> None:
    with pytest.raises(JournalValidationError):
        validate_new_entry(
            entry_date=_VALID_DATE,
            action_taken=_ACTION,
            reasoning=_REASONING,
            review_date=_VALID_DATE,
        )


def test_review_date_after_entry_date_valid() -> None:
    validate_new_entry(
        entry_date=_VALID_DATE,
        action_taken=_ACTION,
        reasoning=_REASONING,
        review_date=_LATER_DATE,
    )


def test_review_date_none_valid() -> None:
    validate_new_entry(
        entry_date=_VALID_DATE,
        action_taken=_ACTION,
        reasoning=_REASONING,
        review_date=None,
    )


# ---------------------------------------------------------------------------
# Optional free-text fields
# ---------------------------------------------------------------------------


def test_hypothesis_none_valid() -> None:
    validate_new_entry(
        entry_date=_VALID_DATE,
        action_taken=_ACTION,
        reasoning=_REASONING,
        hypothesis=None,
    )


def test_tags_none_valid() -> None:
    validate_new_entry(
        entry_date=_VALID_DATE,
        action_taken=_ACTION,
        reasoning=_REASONING,
        tags=None,
    )


# ---------------------------------------------------------------------------
# JournalEntry dataclass invariants
# ---------------------------------------------------------------------------


def test_journal_entry_is_frozen() -> None:
    entry = JournalEntry(
        id=1,
        entry_date=_VALID_DATE,
        action_taken=_ACTION,
        reasoning=_REASONING,
        created_at="2026-06-23T00:00:00+00:00",
    )
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        entry.reasoning = "modified"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


def test_journal_validation_error_inherits_validation_error() -> None:
    assert issubclass(JournalValidationError, ValidationError)


# ---------------------------------------------------------------------------
# Compliance guard NOT applied to user-authored text
# ---------------------------------------------------------------------------


def test_forbidden_compliance_words_in_user_text_pass_validation() -> None:
    """User-authored text containing compliance-forbidden words must not raise.

    The compliance guard does not scan action_taken, reasoning, hypothesis, or tags.
    These fields are stored verbatim as private user notes.
    """
    validate_new_entry(
        entry_date=_VALID_DATE,
        action_taken="buy signal triggered my decision",
        reasoning="I think this is a profit opportunity and I should sell half",
        hypothesis="hold recommendation suggests upside",
        tags="buy,sell,profit",
    )


# ---------------------------------------------------------------------------
# Boundary: journal/models.py must not import forbidden modules
# ---------------------------------------------------------------------------


def test_journal_models_does_not_import_forbidden_modules() -> None:
    import importlib
    import importlib.util
    import sys

    # Force a fresh import to inspect the module's imported names
    spec = importlib.util.find_spec("app.journal.models")
    assert spec is not None

    import app.journal.models as jm

    module_file = jm.__file__
    assert module_file is not None

    source = open(module_file, encoding="utf-8").read()

    forbidden = [
        "sqlite3",
        "data.persistence",
        "app.metrics",
        "app.alerts",
        "app.compliance",
        "requests",
        "httpx",
        "aiohttp",
        "import os",
        "import pathlib",
        "import csv",
    ]
    for term in forbidden:
        assert term not in source, f"journal/models.py must not import {term!r}"


def test_journal_repo_does_not_import_forbidden_modules() -> None:
    import app.data.persistence.journal_repo as jr

    module_file = jr.__file__
    assert module_file is not None

    source = open(module_file, encoding="utf-8").read()

    forbidden = [
        "app.metrics",
        "app.alerts",
        "app.compliance",
        "requests",
        "httpx",
        "aiohttp",
    ]
    for term in forbidden:
        assert term not in source, f"journal_repo.py must not import {term!r}"


def test_journal_models_does_not_call_check_compliance() -> None:
    import app.journal.models as jm

    source = open(jm.__file__, encoding="utf-8").read()
    # Must not call the guard (function call form), though docstrings may mention it
    assert "check_compliance(" not in source
