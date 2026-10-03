from __future__ import annotations

import ipaddress
import re
from datetime import date
from urllib.parse import urlparse

from services.gsc_mcp.config import ALLOWED_DIMENSIONS, ALLOWED_SEARCH_TYPES
from services.gsc_mcp.errors import ErrorCode, GscMcpError

_PRIVATE_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
)


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise GscMcpError(ErrorCode.INVALID_ARGUMENT, f"Invalid date: {value}") from exc


def validate_date_range(start: str, end: str, max_span_days: int) -> tuple[date, date]:
    start_d = parse_iso_date(start)
    end_d = parse_iso_date(end)
    if end_d < start_d:
        raise GscMcpError(ErrorCode.INVALID_ARGUMENT, "end_date must be on or after start_date")
    span = (end_d - start_d).days + 1
    if span > max_span_days:
        raise GscMcpError(
            ErrorCode.INVALID_ARGUMENT,
            f"Date span {span} days exceeds maximum {max_span_days}",
        )
    return start_d, end_d


def validate_dimensions(dimensions: list[str] | None) -> list[str]:
    if not dimensions:
        return []
    if len(dimensions) > 5:
        raise GscMcpError(ErrorCode.INVALID_ARGUMENT, "At most 5 dimensions are allowed")
    invalid = [d for d in dimensions if d not in ALLOWED_DIMENSIONS]
    if invalid:
        raise GscMcpError(
            ErrorCode.INVALID_ARGUMENT,
            f"Unsupported dimensions: {invalid}. Allowed: {sorted(ALLOWED_DIMENSIONS)}",
        )
    return dimensions


def validate_search_type(search_type: str | None) -> str:
    st = (search_type or "web").strip()
    if st not in ALLOWED_SEARCH_TYPES:
        raise GscMcpError(
            ErrorCode.INVALID_ARGUMENT,
            f"Unsupported search_type: {st}. Allowed: {sorted(ALLOWED_SEARCH_TYPES)}",
        )
    return st


def validate_row_limit(row_limit: int | None, max_row_limit: int) -> int:
    limit = row_limit if row_limit is not None else 1000
    if limit < 1 or limit > max_row_limit:
        raise GscMcpError(
            ErrorCode.INVALID_ARGUMENT,
            f"row_limit must be between 1 and {max_row_limit}",
        )
    return limit


def validate_property(site_url: str, configured_site: str, allow_foreign: bool) -> None:
    if allow_foreign:
        return
    if site_url != configured_site:
        raise GscMcpError(
            ErrorCode.PROPERTY_FORBIDDEN,
            f"Property {site_url!r} is not allowed. Configured property: {configured_site!r}",
        )


def _host_is_blocked(host: str) -> bool:
    h = host.lower().strip()
    if h in {"localhost", "127.0.0.1", "::1"}:
        return True
    if h.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return False
    for net in _PRIVATE_NETWORKS:
        if ip in net:
            return True
    return False


def validate_inspection_url(url: str, allowed_origins: tuple[str, ...]) -> str:
    raw = url.strip()
    if not raw:
        raise GscMcpError(ErrorCode.INVALID_ARGUMENT, "inspection_url is required")
    lowered = raw.lower()
    for bad in ("javascript:", "file:", "data:"):
        if lowered.startswith(bad):
            raise GscMcpError(ErrorCode.URL_NOT_ALLOWED, f"URL scheme not allowed: {bad}")
    parsed = urlparse(raw)
    if parsed.username or parsed.password:
        raise GscMcpError(ErrorCode.URL_NOT_ALLOWED, "URLs with userinfo are not allowed")
    if parsed.scheme not in ("http", "https"):
        raise GscMcpError(ErrorCode.URL_NOT_ALLOWED, "Only http/https URLs are allowed")
    if not parsed.netloc:
        raise GscMcpError(ErrorCode.URL_NOT_ALLOWED, "URL must include a host")
    if _host_is_blocked(parsed.hostname or ""):
        raise GscMcpError(ErrorCode.URL_NOT_ALLOWED, "Local or private hosts are not allowed")

    normalized_allowed = tuple(o.rstrip("/") for o in allowed_origins)
    candidate = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    if candidate not in normalized_allowed:
        raise GscMcpError(
            ErrorCode.URL_NOT_ALLOWED,
            f"URL origin {candidate!r} is not in the configured allowlist",
        )
    return raw


_FILTER_OP_RE = re.compile(r"^[a-zA-Z]+$")


def validate_search_analytics_filters(filters: list[dict] | None) -> list[dict]:
    if not filters:
        return []
    for f in filters:
        dim = f.get("dimension")
        if dim and dim not in ALLOWED_DIMENSIONS:
            raise GscMcpError(ErrorCode.INVALID_ARGUMENT, f"Filter dimension not allowed: {dim}")
        op = f.get("operator") or f.get("op")
        if op and not _FILTER_OP_RE.match(str(op)):
            raise GscMcpError(ErrorCode.INVALID_ARGUMENT, f"Invalid filter operator: {op}")
        expr = f.get("expression")
        if expr is not None and len(str(expr)) > 500:
            raise GscMcpError(ErrorCode.INVALID_ARGUMENT, "Filter expression too long")
    return filters
