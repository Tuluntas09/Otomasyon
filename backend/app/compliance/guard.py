"""Compliance safety guard for all system-generated user-facing text.

Scans text for forbidden advisory, trading, and profit-claim language.
Raises ComplianceViolationError listing every matched term if any are found.
Never rewrites or sanitizes text — the caller must supply clean text.
"""

import re
from dataclasses import dataclass

from app.core.exceptions import ComplianceViolationError


@dataclass(frozen=True)
class ComplianceViolation:
    matched_term: str
    context: str


# ---------------------------------------------------------------------------
# Forbidden term lists
# ---------------------------------------------------------------------------

_SINGLE_WORD_FORBIDDEN: list[str] = [
    # English — advisory
    "buy", "sell", "hold", "reduce", "increase",
    "recommend", "suggest", "opportunity", "profit", "loss",
    "should", "must", "guaranteed", "execute", "order", "broker",
    # Turkish — advisory
    "al", "sat", "tut", "fırsat", "emir",
]

_PHRASE_FORBIDDEN: list[str] = [
    # English — multi-word
    "target price", "price target", "price prediction",
    "take profit", "stop loss", "profit opportunity",
    "opportunity to profit", "should enter", "should exit",
    "trade now", "paper trade", "live trade",
    # Turkish — multi-word
    "hedef fiyat", "kar al", "zarar durdur", "kesin kazanç",
    "işlem aç", "işlem kapat", "aracı kurum",
]

# ---------------------------------------------------------------------------
# Compile patterns — phrases first so longer matches are reported by their
# own term string; both single-word and phrase patterns use \b boundaries.
# False-positive notes (verified by \b semantics):
#   "threshold" → does not trigger "hold"  (\b before 'h' is absent inside a word)
#   "glossy"    → does not trigger "loss"  (\b before 'l' absent inside a word)
#   "total"     → does not trigger "al"    (\b before 'a' absent inside a word)
#   "capital"   → does not trigger "al"    (\b before 'a' absent inside a word)
# ---------------------------------------------------------------------------

_FLAGS = re.IGNORECASE | re.UNICODE

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (term, re.compile(r"\b" + re.escape(term) + r"\b", _FLAGS))
    for term in _PHRASE_FORBIDDEN + _SINGLE_WORD_FORBIDDEN
]


def check_compliance(text: str) -> None:
    """Scan *text* for forbidden terms.

    Passes silently for empty or compliant text.
    Raises ComplianceViolationError listing all matched terms if any are found.
    """
    if not text:
        return

    violations: list[ComplianceViolation] = []
    for term, pattern in _PATTERNS:
        match = pattern.search(text)
        if match:
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            violations.append(
                ComplianceViolation(matched_term=term, context=text[start:end])
            )

    if violations:
        raise ComplianceViolationError(violations)
