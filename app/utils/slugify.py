"""URL-safe slug generation helpers."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

_SLUG_CLEAN_RE = re.compile(r"[^\w\s-]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"[-\s]+")


def slugify(text: str, *, max_length: int = 200) -> str:
    """Convert arbitrary text to a lowercase URL slug."""
    normalized = text.strip().lower()
    cleaned = _SLUG_CLEAN_RE.sub("", normalized)
    slug = _WHITESPACE_RE.sub("-", cleaned).strip("-")
    if not slug:
        return ""
    return slug[:max_length]


async def ensure_unique_slug(
    base_text: str,
    *,
    exists: Callable[[str], Awaitable[bool]],
    fallback_prefix: str = "item",
    max_length: int = 200,
) -> str:
    """Return a slug derived from base_text that does not yet exist."""
    root = slugify(base_text, max_length=max_length) or slugify(fallback_prefix, max_length=max_length)
    if not root:
        root = fallback_prefix

    candidate = root
    suffix = 2
    while await exists(candidate):
        tail = f"-{suffix}"
        candidate = f"{root[: max_length - len(tail)]}{tail}"
        suffix += 1
    return candidate
