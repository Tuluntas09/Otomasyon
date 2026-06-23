"""Integration tests for JournalRepo against in-memory SQLite (Phase 6)."""

import time
from datetime import datetime, timezone

import pytest

from app.core.exceptions import InvalidTickerError, JournalValidationError
from app.data.persistence.db import get_connection, init_schema
from app.data.persistence.journal_repo import JournalRepo
from app.journal.models import JournalEntry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def conn():
    c = get_connection(":memory:")
    init_schema(c)
    return c


@pytest.fixture()
def repo(conn):
    return JournalRepo(conn)


_DATE_A = "2026-03-01"
_DATE_B = "2026-04-15"
_DATE_C = "2026-05-20"
_ACTION = "Reviewed position"
_REASONING = "Allocation within target range; no change needed"


# ---------------------------------------------------------------------------
# get_all on empty table
# ---------------------------------------------------------------------------


def test_get_all_empty_returns_empty_list(repo) -> None:
    assert repo.get_all() == []


# ---------------------------------------------------------------------------
# add_entry basic behaviour
# ---------------------------------------------------------------------------


def test_add_minimal_entry_returns_journal_entry(repo) -> None:
    entry = repo.add_entry(entry_date=_DATE_A, action_taken=_ACTION, reasoning=_REASONING)
    assert isinstance(entry, JournalEntry)


def test_add_entry_id_is_positive_integer(repo) -> None:
    entry = repo.add_entry(entry_date=_DATE_A, action_taken=_ACTION, reasoning=_REASONING)
    assert isinstance(entry.id, int)
    assert entry.id > 0


def test_add_entry_created_at_is_set(repo) -> None:
    entry = repo.add_entry(entry_date=_DATE_A, action_taken=_ACTION, reasoning=_REASONING)
    assert entry.created_at is not None
    assert len(entry.created_at) > 0


def test_add_entry_created_at_is_valid_iso_datetime(repo) -> None:
    entry = repo.add_entry(entry_date=_DATE_A, action_taken=_ACTION, reasoning=_REASONING)
    # Must parse without error
    dt = datetime.fromisoformat(entry.created_at)
    assert dt is not None


def test_add_entry_created_at_includes_utc_timezone(repo) -> None:
    entry = repo.add_entry(entry_date=_DATE_A, action_taken=_ACTION, reasoning=_REASONING)
    dt = datetime.fromisoformat(entry.created_at)
    assert dt.tzinfo is not None
    assert dt.utcoffset().total_seconds() == 0


# ---------------------------------------------------------------------------
# Round-trip: all fields
# ---------------------------------------------------------------------------


def test_get_all_round_trips_all_fields(repo) -> None:
    repo.add_entry(
        entry_date=_DATE_A,
        action_taken=_ACTION,
        reasoning=_REASONING,
        ticker="AAPL",
        hypothesis="Expect stable price over next month",
        review_date=_DATE_B,
        tags="tech,review",
    )
    entries = repo.get_all()
    assert len(entries) == 1
    e = entries[0]
    assert e.entry_date == _DATE_A
    assert e.action_taken == _ACTION
    assert e.reasoning == _REASONING
    assert e.ticker == "AAPL"
    assert e.hypothesis == "Expect stable price over next month"
    assert e.review_date == _DATE_B
    assert e.tags == "tech,review"


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


def test_get_all_orders_by_entry_date_desc(repo) -> None:
    repo.add_entry(entry_date=_DATE_A, action_taken=_ACTION, reasoning=_REASONING)
    repo.add_entry(entry_date=_DATE_C, action_taken=_ACTION, reasoning=_REASONING)
    repo.add_entry(entry_date=_DATE_B, action_taken=_ACTION, reasoning=_REASONING)
    entries = repo.get_all()
    dates = [e.entry_date for e in entries]
    assert dates == sorted(dates, reverse=True)


def test_get_all_same_entry_date_orders_by_created_at_desc(repo) -> None:
    repo.add_entry(entry_date=_DATE_A, action_taken="First entry", reasoning=_REASONING)
    # Ensure a measurable time difference between insertions
    time.sleep(0.01)
    repo.add_entry(entry_date=_DATE_A, action_taken="Second entry", reasoning=_REASONING)
    entries = repo.get_all()
    assert entries[0].action_taken == "Second entry"
    assert entries[1].action_taken == "First entry"


# ---------------------------------------------------------------------------
# Nullable fields
# ---------------------------------------------------------------------------


def test_ticker_none_persists_and_retrieves_as_none(repo) -> None:
    repo.add_entry(entry_date=_DATE_A, action_taken=_ACTION, reasoning=_REASONING, ticker=None)
    e = repo.get_all()[0]
    assert e.ticker is None


def test_optional_fields_none_persist(repo) -> None:
    repo.add_entry(entry_date=_DATE_A, action_taken=_ACTION, reasoning=_REASONING)
    e = repo.get_all()[0]
    assert e.ticker is None
    assert e.hypothesis is None
    assert e.review_date is None
    assert e.tags is None


def test_optional_fields_populated_round_trip(repo) -> None:
    repo.add_entry(
        entry_date=_DATE_A,
        action_taken=_ACTION,
        reasoning=_REASONING,
        ticker="GOOG",
        hypothesis="Lower beta expected",
        review_date=_DATE_B,
        tags="diversification",
    )
    e = repo.get_all()[0]
    assert e.ticker == "GOOG"
    assert e.hypothesis == "Lower beta expected"
    assert e.review_date == _DATE_B
    assert e.tags == "diversification"


# ---------------------------------------------------------------------------
# Multiple entries for same ticker
# ---------------------------------------------------------------------------


def test_multiple_entries_for_same_ticker_allowed(repo) -> None:
    repo.add_entry(entry_date=_DATE_A, action_taken="First", reasoning=_REASONING, ticker="MSFT")
    repo.add_entry(entry_date=_DATE_B, action_taken="Second", reasoning=_REASONING, ticker="MSFT")
    entries = repo.get_by_ticker("MSFT")
    assert len(entries) == 2


# ---------------------------------------------------------------------------
# get_by_ticker
# ---------------------------------------------------------------------------


def test_get_by_ticker_returns_matching_entries_only(repo) -> None:
    repo.add_entry(entry_date=_DATE_A, action_taken=_ACTION, reasoning=_REASONING, ticker="AAPL")
    repo.add_entry(entry_date=_DATE_B, action_taken=_ACTION, reasoning=_REASONING, ticker="MSFT")
    entries = repo.get_by_ticker("AAPL")
    assert len(entries) == 1
    assert entries[0].ticker == "AAPL"


def test_get_by_ticker_validates_ticker(repo) -> None:
    with pytest.raises(InvalidTickerError):
        repo.get_by_ticker("123bad")


def test_get_by_ticker_unknown_ticker_returns_empty(repo) -> None:
    repo.add_entry(entry_date=_DATE_A, action_taken=_ACTION, reasoning=_REASONING, ticker="AAPL")
    assert repo.get_by_ticker("ZZZZ") == []


def test_get_by_ticker_does_not_return_ticker_less_entries(repo) -> None:
    repo.add_entry(entry_date=_DATE_A, action_taken=_ACTION, reasoning=_REASONING, ticker=None)
    repo.add_entry(entry_date=_DATE_B, action_taken=_ACTION, reasoning=_REASONING, ticker="AAPL")
    entries = repo.get_by_ticker("AAPL")
    assert all(e.ticker == "AAPL" for e in entries)
    assert len(entries) == 1


# ---------------------------------------------------------------------------
# Append-only: no update or delete methods
# ---------------------------------------------------------------------------


def test_journal_repo_has_no_delete_method(repo) -> None:
    assert not hasattr(repo, "delete")


def test_journal_repo_has_no_update_method(repo) -> None:
    assert not hasattr(repo, "update")


# ---------------------------------------------------------------------------
# Schema idempotency
# ---------------------------------------------------------------------------


def test_journal_entries_table_created_idempotently() -> None:
    c = get_connection(":memory:")
    init_schema(c)
    # Second call must not raise
    init_schema(c)
    rows = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='journal_entries'").fetchall()
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# Validation before DB write
# ---------------------------------------------------------------------------


def test_invalid_entry_raises_before_db_write(repo) -> None:
    from app.core.exceptions import ValidationError
    with pytest.raises(ValidationError):
        repo.add_entry(entry_date="bad-date", action_taken=_ACTION, reasoning=_REASONING)
    assert repo.get_all() == []


# ---------------------------------------------------------------------------
# User-authored text with compliance-forbidden terms stored verbatim
# ---------------------------------------------------------------------------


def test_forbidden_compliance_terms_stored_and_retrieved_verbatim(repo) -> None:
    forbidden_text = "buy signal; sell opportunity; profit target met"
    entry = repo.add_entry(
        entry_date=_DATE_A,
        action_taken=forbidden_text,
        reasoning="My own note about this situation",
    )
    assert entry.action_taken == forbidden_text
    retrieved = repo.get_all()
    assert retrieved[0].action_taken == forbidden_text
