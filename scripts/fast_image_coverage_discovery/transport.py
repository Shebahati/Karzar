"""Sync HTTP transport wrapper for external discovery."""

from __future__ import annotations

from scripts.image_discovery.transport import HostThrottledFetcher

DEFAULT_GLOBAL_CONCURRENCY = 12
DEFAULT_PER_HOST_CONCURRENCY = 2
DEFAULT_DELAY = 0.5
DEFAULT_TIMEOUT = 20.0
DEFAULT_RETRIES = 2


def make_fetcher(
    allowed_hosts: frozenset[str],
    *,
    delay: float = DEFAULT_DELAY,
    timeout: float = DEFAULT_TIMEOUT,
    urlopen=None,
) -> HostThrottledFetcher:
    return HostThrottledFetcher(
        allowed_hosts=allowed_hosts,
        delay=delay,
        timeout=timeout,
        urlopen=urlopen,
    )
