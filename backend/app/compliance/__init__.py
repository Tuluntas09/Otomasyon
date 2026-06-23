"""Compliance safety guard.

Scans all system-generated user-facing text before it reaches the user.
Raises ComplianceViolationError if forbidden language is detected.
"""

from app.compliance.guard import ComplianceViolation, check_compliance
from app.core.exceptions import ComplianceViolationError

__all__ = ["ComplianceViolation", "ComplianceViolationError", "check_compliance"]
