"""Shared stdlib HTTP helpers for live ops (never used by CI tests)."""

from __future__ import annotations

import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = "KarzarImageMultisource/0.1 (+local-ops; review-only)"


def fetch_url(
    url: str,
    *,
    timeout: float = 30.0,
    max_bytes: int = 4_000_000,
    delay: float = 0.0,
) -> tuple[int, str, bytes]:
    if delay > 0:
        time.sleep(delay)
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en,fa;q=0.8"})
    try:
        with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — caller host-allowlists
            final = resp.geturl()
            data = resp.read(max_bytes)
            status = int(getattr(resp, "status", 200) or 200)
            return status, final, data
    except HTTPError as exc:
        body = exc.read(max_bytes) if hasattr(exc, "read") else b""
        final = getattr(exc, "url", url) or url
        return int(exc.code), str(final), body
    except (URLError, TimeoutError, OSError):
        raise
