"""Transport with optional media-host allowlist extension (TLS still verified)."""

from __future__ import annotations

from scripts.image_discovery.transport import HostThrottledFetcher

from .media_policy import classify_media_host

DEFAULT_DELAY = 0.5
DEFAULT_TIMEOUT = 20.0


class MediaAwareFetcher:
    """Wrap HostThrottledFetcher; allow CDN image hosts after media_policy checks."""

    def __init__(self, inner: HostThrottledFetcher, page_hosts: frozenset[str]) -> None:
        self.inner = inner
        self.page_hosts = page_hosts
        self.allowed_media: set[str] = set()
        self.media_relations: list[dict[str, str]] = []

    def allow_media_for_page(self, page_url: str, image_url: str) -> bool:
        ok, page_host, media_host, relation = classify_media_host(page_url, image_url)
        if not ok:
            return False
        self.allowed_media.add(media_host)
        # Mutate underlying allowlist for this run
        self.inner.allowed_hosts = frozenset(set(self.inner.allowed_hosts) | {media_host})
        self.media_relations.append(
            {
                "page_host": page_host,
                "media_host": media_host,
                "media_host_relation": relation,
                "image_url": image_url,
            }
        )
        return True

    def get(self, url: str, *, fail_code: str, max_bytes: int | None = None):
        return self.inner.get(url, fail_code=fail_code, max_bytes=max_bytes)


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
        max_transient_retries=2,
        urlopen=urlopen,
    )


def make_media_fetcher(
    page_hosts: frozenset[str],
    *,
    urlopen=None,
) -> MediaAwareFetcher:
    return MediaAwareFetcher(make_fetcher(page_hosts, urlopen=urlopen), page_hosts)
