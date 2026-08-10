"""Deterministic known-placeholder signatures (conservative).

Repository-proven markers only — no visual heuristics.
"""

from __future__ import annotations

from urllib.parse import unquote, urlparse

# frontend/Storefront/public/images/placeholders/karzar-editorial.svg
KNOWN_PLACEHOLDER_SHA256: frozenset[str] = frozenset(
    {
        "6beb73e070a87c786ec339cb1d46943c726ba5e96866172690687e065b7b346f",
    }
)

KNOWN_PLACEHOLDER_PATH_MARKERS: frozenset[str] = frozenset(
    {
        "/images/placeholders/",
        "/static/images/placeholders/",
    }
)

KNOWN_PLACEHOLDER_FILENAMES: frozenset[str] = frozenset(
    {
        "karzar-editorial.svg",
    }
)


def normalize_asset_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
    except Exception:
        return raw
    path = unquote(parsed.path or "")
    # Drop query/fragment for identity; keep host+scheme+path
    scheme = (parsed.scheme or "").lower()
    netloc = (parsed.netloc or "").lower()
    if scheme and netloc:
        return f"{scheme}://{netloc}{path}"
    return path or raw


def is_known_placeholder_url(url: str | None) -> bool:
    if not url:
        return False
    norm = normalize_asset_url(url).lower()
    path = urlparse(norm).path if "://" in norm else norm
    path_l = path.lower()
    for marker in KNOWN_PLACEHOLDER_PATH_MARKERS:
        if marker in path_l:
            return True
    name = path_l.rsplit("/", 1)[-1]
    if name in {f.lower() for f in KNOWN_PLACEHOLDER_FILENAMES}:
        return True
    return False


def is_known_placeholder_sha256(sha256: str | None) -> bool:
    if not sha256:
        return False
    return sha256.lower() in KNOWN_PLACEHOLDER_SHA256


def mark_placeholder(url: str | None, sha256: str | None) -> bool:
    return is_known_placeholder_url(url) or is_known_placeholder_sha256(sha256)
