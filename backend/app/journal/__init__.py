"""Decision journal — append-only log of user reasoning.

Records the user's own decisions and hypotheses.
Never auto-generates journal content. Implemented in Phase 6.
"""

from app.journal.models import JournalEntry, validate_new_entry

__all__ = ["JournalEntry", "validate_new_entry"]
