"""Hesabfa integration error types."""

from __future__ import annotations


class HesabfaError(Exception):
    """Base error for Hesabfa client/service failures."""


class HesabfaNotConfiguredError(HesabfaError):
    """Raised when Hesabfa is disabled or secrets are missing."""


class HesabfaApiError(HesabfaError):
    """Remote API returned Success=false or an HTTP failure."""

    def __init__(
        self,
        message: str,
        *,
        error_code: int | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code
