from __future__ import annotations

import re
from typing import Any

REDACTED = "***REDACTED***"

_SENSITIVE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(refresh[_-]?token)(['\"]?\s*[:=]\s*)([^\s'\",}]+)"), r"\1\2" + REDACTED),
    (re.compile(r"(?i)(client[_-]?secret)(['\"]?\s*[:=]\s*)([^\s'\",}]+)"), r"\1\2" + REDACTED),
    (re.compile(r"(?i)(access[_-]?token)(['\"]?\s*[:=]\s*)([^\s'\",}]+)"), r"\1\2" + REDACTED),
    (re.compile(r"(?i)(api[_-]?key)(['\"]?\s*[:=]\s*)([^\s'\",}]+)"), r"\1\2" + REDACTED),
    (re.compile(r"(?i)authorization:\s*bearer\s+[^\s]+"), "Authorization: Bearer " + REDACTED),
    (re.compile(r"(?i)(crux_api_key|google_gsc_refresh_token|karzar_mcp_access_token)=\S+"), r"\1=" + REDACTED),
)


def redact_text(text: str) -> str:
    out = text
    for pattern, repl in _SENSITIVE_PATTERNS:
        out = pattern.sub(repl, out)
    return out


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(v) for v in value]
    return value
