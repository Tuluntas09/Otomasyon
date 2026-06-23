"""SQLite persistence for the decision journal.

Append-only: exposes add_entry, get_all, get_by_ticker.
No update or delete methods.
"""

import sqlite3
from datetime import datetime, timezone

from app.core.exceptions import InvalidDateError
from app.core.validation import validate_iso_date, validate_ticker
from app.journal.models import JournalEntry, validate_new_entry


class JournalRepo:
    """Repository for journal_entries table. Append-only."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def add_entry(
        self,
        entry_date: str,
        action_taken: str,
        reasoning: str,
        ticker: str | None = None,
        hypothesis: str | None = None,
        review_date: str | None = None,
        tags: str | None = None,
    ) -> JournalEntry:
        """Validate, insert, and return the persisted JournalEntry."""
        validate_new_entry(
            entry_date=entry_date,
            action_taken=action_taken,
            reasoning=reasoning,
            ticker=ticker,
            hypothesis=hypothesis,
            review_date=review_date,
            tags=tags,
        )
        created_at = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """
            INSERT INTO journal_entries
                (entry_date, ticker, action_taken, reasoning, hypothesis, review_date, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (entry_date, ticker, action_taken, reasoning, hypothesis, review_date, tags, created_at),
        )
        self._conn.commit()
        entry_id = cursor.lastrowid
        return JournalEntry(
            id=entry_id,
            entry_date=entry_date,
            action_taken=action_taken,
            reasoning=reasoning,
            created_at=created_at,
            ticker=ticker,
            hypothesis=hypothesis,
            review_date=review_date,
            tags=tags,
        )

    def get_all(self) -> list[JournalEntry]:
        """Return all entries ordered by entry_date DESC, created_at DESC."""
        rows = self._conn.execute(
            """
            SELECT id, entry_date, ticker, action_taken, reasoning,
                   hypothesis, review_date, tags, created_at
            FROM journal_entries
            ORDER BY entry_date DESC, created_at DESC
            """
        ).fetchall()
        return [_row_to_entry(row) for row in rows]

    def get_by_date_range(self, date_from: str, date_to: str) -> list[JournalEntry]:
        """Return entries with entry_date in [date_from, date_to], newest first.

        Both dates must be valid ISO-8601 strings. date_from must be <= date_to.
        Returns [] if none match. User-authored text is never rewritten or scanned.
        """
        validate_iso_date(date_from)
        validate_iso_date(date_to)
        if date_from > date_to:
            raise InvalidDateError(
                f"date_from {date_from!r} must be on or before date_to {date_to!r}."
            )
        rows = self._conn.execute(
            """
            SELECT id, entry_date, ticker, action_taken, reasoning,
                   hypothesis, review_date, tags, created_at
            FROM journal_entries
            WHERE entry_date >= ? AND entry_date <= ?
            ORDER BY entry_date DESC, created_at DESC
            """,
            (date_from, date_to),
        ).fetchall()
        return [_row_to_entry(row) for row in rows]

    def get_by_ticker(self, ticker: str) -> list[JournalEntry]:
        """Return entries for a specific ticker, ordered by entry_date DESC, created_at DESC."""
        validate_ticker(ticker)
        rows = self._conn.execute(
            """
            SELECT id, entry_date, ticker, action_taken, reasoning,
                   hypothesis, review_date, tags, created_at
            FROM journal_entries
            WHERE ticker = ?
            ORDER BY entry_date DESC, created_at DESC
            """,
            (ticker,),
        ).fetchall()
        return [_row_to_entry(row) for row in rows]


def _row_to_entry(row: sqlite3.Row) -> JournalEntry:
    return JournalEntry(
        id=row["id"],
        entry_date=row["entry_date"],
        action_taken=row["action_taken"],
        reasoning=row["reasoning"],
        created_at=row["created_at"],
        ticker=row["ticker"],
        hypothesis=row["hypothesis"],
        review_date=row["review_date"],
        tags=row["tags"],
    )
