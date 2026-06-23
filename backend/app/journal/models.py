"""Decision journal domain model and validation.

Records user-authored reasoning about their own decisions.
No I/O, no persistence, no compliance scanning of user text.
"""

from dataclasses import dataclass
from datetime import date as _date

from app.core.exceptions import JournalValidationError
from app.core.validation import validate_iso_date, validate_ticker


@dataclass(frozen=True)
class JournalEntry:
    """Immutable record of one user-authored journal entry."""

    id: int
    entry_date: str
    action_taken: str
    reasoning: str
    created_at: str
    ticker: str | None = None
    hypothesis: str | None = None
    review_date: str | None = None
    tags: str | None = None


def validate_new_entry(
    entry_date: str,
    action_taken: str,
    reasoning: str,
    ticker: str | None = None,
    hypothesis: str | None = None,
    review_date: str | None = None,
    tags: str | None = None,
) -> None:
    """Validate fields for a new journal entry; raise on any violation.

    Does not call check_compliance — these are user-authored private notes.
    """
    validate_iso_date(entry_date)

    if not isinstance(action_taken, str) or not action_taken.strip():
        raise JournalValidationError("action_taken must be a non-empty string.")

    if not isinstance(reasoning, str) or not reasoning.strip():
        raise JournalValidationError("reasoning must be a non-empty string.")

    if ticker is not None:
        validate_ticker(ticker)

    if review_date is not None:
        validate_iso_date(review_date)
        if _date.fromisoformat(review_date) <= _date.fromisoformat(entry_date):
            raise JournalValidationError(
                f"review_date {review_date!r} must be strictly after entry_date {entry_date!r}."
            )
