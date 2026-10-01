from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    AUTH_NOT_CONFIGURED = "AUTH_NOT_CONFIGURED"
    AUTH_REFRESH_FAILED = "AUTH_REFRESH_FAILED"
    PROPERTY_FORBIDDEN = "PROPERTY_FORBIDDEN"
    URL_NOT_ALLOWED = "URL_NOT_ALLOWED"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    UPSTREAM_RATE_LIMITED = "UPSTREAM_RATE_LIMITED"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    UPSTREAM_PERMISSION_DENIED = "UPSTREAM_PERMISSION_DENIED"
    NO_DATA = "NO_DATA"
    CRUX_NOT_CONFIGURED = "CRUX_NOT_CONFIGURED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMITED = "RATE_LIMITED"


class GscMcpError(Exception):
    def __init__(self, code: ErrorCode, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"status": "error", "error_code": self.code.value, "message": self.message}
        if self.details:
            out["details"] = self.details
        return out
