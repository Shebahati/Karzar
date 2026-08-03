"""HTTP transport with host allowlist, bounded reads, and controlled redirects."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from http.cookiejar import CookieJar
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener

from .contracts import DiscoveryError

UrlOpenFn = Callable[[Request, float], Any]

DEFAULT_MAX_DETAIL_PAGE_BYTES = 2_000_000
DEFAULT_MAX_IMAGE_BYTES = 15_000_000
DEFAULT_MAX_ERROR_BODY_BYTES = 64_000


class _RedirectSignal(Exception):
    def __init__(self, url: str, code: int) -> None:
        self.url = url
        self.code = code


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower().rstrip(".")


def host_allowed(url: str, allowed_hosts: frozenset[str]) -> bool:
    return host_of(url) in allowed_hosts


def normalize_url_key(url: str) -> str:
    """Scheme/host/port/path/query — consistent loop and single-flight keys."""
    p = urlparse(url)
    scheme = (p.scheme or "https").lower()
    host = (p.hostname or "").lower().rstrip(".")
    port = p.port
    if port is None:
        port = 443 if scheme == "https" else 80 if scheme == "http" else None
    path = p.path or "/"
    # Keep trailing slash significance only via rstrip of empty → /
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/") or "/"
    query = p.query or ""
    netloc = f"{host}:{port}" if port is not None else host
    if query:
        return f"{scheme}://{netloc}{path}?{query}"
    return f"{scheme}://{netloc}{path}"


def validate_url_policy(
    url: str,
    *,
    allow_http: bool = False,
    allowed_ports: frozenset[int] | None = None,
) -> None:
    p = urlparse(url)
    scheme = (p.scheme or "").lower()
    if scheme == "https":
        default_ports = frozenset({443})
    elif scheme == "http":
        if not allow_http:
            raise DiscoveryError("fetch", "unsupported_scheme", f"http not allowed: {url}")
        default_ports = frozenset({80})
    else:
        raise DiscoveryError("fetch", "unsupported_scheme", f"scheme not allowed: {scheme or '(empty)'}")
    ports = allowed_ports if allowed_ports is not None else default_ports
    port = p.port
    if port is None:
        port = 443 if scheme == "https" else 80
    if port not in ports:
        raise DiscoveryError("fetch", "unexpected_port", f"port {port} not allowed for {scheme}")


def read_bounded(
    resp: Any,
    *,
    max_bytes: int,
    headers: Any = None,
) -> bytes:
    hdrs = headers if headers is not None else getattr(resp, "headers", None)
    if hdrs is not None:
        cl = hdrs.get("Content-Length") if hasattr(hdrs, "get") else None
        if cl is not None and str(cl).strip() != "":
            try:
                if int(cl) > max_bytes:
                    raise DiscoveryError(
                        "fetch",
                        "response_too_large",
                        f"Content-Length {cl} exceeds {max_bytes}",
                    )
            except ValueError:
                pass
    chunks: list[bytes] = []
    total = 0
    while True:
        try:
            chunk = resp.read(65536)
        except TypeError:
            # Some mocks only implement read()
            data = resp.read()
            if total + len(data) > max_bytes:
                raise DiscoveryError(
                    "fetch",
                    "response_too_large",
                    f"body exceeds {max_bytes}",
                ) from None
            return data
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise DiscoveryError(
                "fetch",
                "response_too_large",
                f"body exceeds {max_bytes}",
            )
        chunks.append(chunk)
    return b"".join(chunks)


class HostThrottledFetcher:
    """GET with throttle, allowlist, redirect host checks, bounded retries/reads."""

    def __init__(
        self,
        *,
        allowed_hosts: frozenset[str],
        delay: float = 0.5,
        timeout: float = 60.0,
        max_redirects: int = 8,
        max_transient_retries: int = 1,
        user_agent: str = "KarzarImageDiscovery/1.2 (+https://www.karzartools.com)",
        urlopen: UrlOpenFn | None = None,
        allow_http: bool = False,
        allowed_ports: frozenset[int] | None = None,
        max_detail_page_bytes: int = DEFAULT_MAX_DETAIL_PAGE_BYTES,
        max_image_bytes: int = DEFAULT_MAX_IMAGE_BYTES,
        max_error_body_bytes: int = DEFAULT_MAX_ERROR_BODY_BYTES,
    ) -> None:
        self.allowed_hosts = allowed_hosts
        self.delay = delay
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.max_transient_retries = max_transient_retries
        self.user_agent = user_agent
        self._urlopen = urlopen
        self.allow_http = allow_http
        self.allowed_ports = allowed_ports
        self.max_detail_page_bytes = max_detail_page_bytes
        self.max_image_bytes = max_image_bytes
        self.max_error_body_bytes = max_error_body_bytes
        self._host_locks: dict[str, threading.Lock] = {}
        self._host_next: dict[str, float] = {}
        self._meta = threading.Lock()
        self._cookie_jar = CookieJar()

    def _throttle(self, host: str) -> None:
        with self._meta:
            lock = self._host_locks.setdefault(host, threading.Lock())
        with lock:
            now = time.monotonic()
            with self._meta:
                nxt = self._host_next.get(host, 0.0)
            wait = nxt - now
            if wait > 0:
                time.sleep(wait)
            with self._meta:
                self._host_next[host] = time.monotonic() + self.delay

    def _normalize_url(self, url: str) -> str:
        return normalize_url_key(url)

    def _validate(self, url: str) -> None:
        validate_url_policy(url, allow_http=self.allow_http, allowed_ports=self.allowed_ports)

    def _default_urlopen(self, req: Request, timeout: float) -> Any:
        class _BlockRedirect(HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
                raise _RedirectSignal(newurl, code)

        opener = build_opener(HTTPCookieProcessor(self._cookie_jar), _BlockRedirect)
        return opener.open(req, timeout=timeout)

    def get(
        self,
        url: str,
        *,
        fail_code: str,
        max_bytes: int | None = None,
    ) -> tuple[int, bytes, str, str]:
        if not host_allowed(url, self.allowed_hosts):
            raise DiscoveryError(
                "fetch",
                "unsupported_host",
                f"host not allowlisted: {host_of(url)}",
            )
        self._validate(url)
        limit = max_bytes if max_bytes is not None else self.max_detail_page_bytes

        transient_left = self.max_transient_retries
        current = url
        redirects = 0
        seen: set[str] = set()
        same_url_bounces = 0

        while True:
            self._validate(current)
            norm = self._normalize_url(current)
            if norm in seen and same_url_bounces == 0:
                raise DiscoveryError("fetch", "redirect_loop", f"loop at {current}")
            if not host_allowed(current, self.allowed_hosts):
                raise DiscoveryError(
                    "fetch",
                    "cross_host_redirect",
                    f"host not allowlisted: {host_of(current)}",
                )

            host = host_of(current)
            self._throttle(host)
            req = Request(current, headers={"User-Agent": self.user_agent, "Accept": "*/*"})
            open_fn = self._urlopen or self._default_urlopen
            try:
                with open_fn(req, self.timeout) as resp:
                    status = int(getattr(resp, "status", None) or resp.getcode())
                    body = read_bounded(resp, max_bytes=limit, headers=resp.headers)
                    ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                    final = resp.geturl() if hasattr(resp, "geturl") else current
                    if not host_allowed(final, self.allowed_hosts):
                        raise DiscoveryError(
                            "fetch",
                            "cross_host_redirect",
                            f"final URL host not allowlisted: {host_of(final)}",
                            status,
                        )
                    self._validate(final)
                    return status, body, ctype, final
            except _RedirectSignal as redir:
                redirects += 1
                if redirects > self.max_redirects:
                    raise DiscoveryError("fetch", "redirect_limit", "too many redirects") from redir
                nxt = urljoin(current, redir.url)
                if not host_allowed(nxt, self.allowed_hosts):
                    raise DiscoveryError(
                        "fetch",
                        "cross_host_redirect",
                        f"redirect host not allowlisted: {host_of(nxt)}",
                        redir.code,
                    ) from redir
                if self._normalize_url(nxt) == self._normalize_url(current):
                    same_url_bounces += 1
                    if same_url_bounces > 2:
                        raise DiscoveryError(
                            "fetch", "redirect_loop", f"loop at {current}"
                        ) from redir
                    seen.discard(norm)
                    continue
                seen.add(norm)
                same_url_bounces = 0
                current = nxt
                continue
            except HTTPError as e:
                if e.code in {301, 302, 303, 307, 308}:
                    loc = e.headers.get("Location") if e.headers else None
                    if not loc:
                        raise DiscoveryError(
                            "fetch", fail_code, f"HTTP {e.code} without Location", e.code
                        ) from e
                    redirects += 1
                    if redirects > self.max_redirects:
                        raise DiscoveryError("fetch", "redirect_limit", "too many redirects") from e
                    nxt = urljoin(current, loc)
                    if not host_allowed(nxt, self.allowed_hosts):
                        raise DiscoveryError(
                            "fetch",
                            "cross_host_redirect",
                            f"redirect host not allowlisted: {host_of(nxt)}",
                            e.code,
                        ) from e
                    if self._normalize_url(nxt) == self._normalize_url(current):
                        same_url_bounces += 1
                        if same_url_bounces > 2:
                            raise DiscoveryError(
                                "fetch", "redirect_loop", f"loop at {current}"
                            ) from e
                        seen.discard(norm)
                        continue
                    seen.add(norm)
                    same_url_bounces = 0
                    current = nxt
                    continue
                body = b""
                if hasattr(e, "read"):
                    try:
                        body = read_bounded(e, max_bytes=self.max_error_body_bytes, headers=e.headers)
                    except DiscoveryError:
                        raise
                    except Exception:
                        body = b""
                ctype = (
                    (e.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                    if e.headers
                    else ""
                )
                return int(e.code), body, ctype, current
            except (URLError, TimeoutError, OSError) as e:
                if transient_left > 0:
                    transient_left -= 1
                    time.sleep(1.0)
                    continue
                reason = getattr(e, "reason", None) or str(e)
                detail = "timed out" if isinstance(e, TimeoutError) else str(reason)
                raise DiscoveryError("fetch", fail_code, detail) from e
