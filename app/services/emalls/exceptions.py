"""Emalls adapter exceptions (never include raw tokens)."""

from __future__ import annotations


class EmallsError(Exception):
    """Base Emalls adapter error."""


class EmallsTokenInvalidError(EmallsError):
    """Emalls validator rejected the token."""


class EmallsValidationUnavailableError(EmallsError):
    """Emalls validation service timed out or errored with no valid cache."""
