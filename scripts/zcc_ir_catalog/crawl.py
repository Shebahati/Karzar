"""Conservative HTTP fetch with cache, retry, and robots enforcement.

GET only. Never submits forms, carts, or orders.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from zcc_ir_catalog import USER_AGENT
from zcc_ir_catalog.models import FetchResult
from zcc_ir_catalog.normalize import encode_http_url
from zcc_ir_catalog.parse import robots_allows

ALLOWED_HOSTS = frozenset({"zcc.ir", "www.zcc.ir"})
DEFAULT_TIMEOUT_S = 45.0
DEFAULT_RETRIES = 4
DEFAULT_SLEEP_S = 0.8
MAX_BODY_BYTES = 2_500_000


class RobotsDenied(RuntimeError):
    pass


def cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return host in ALLOWED_HOSTS


class ReadOnlyFetcher:
    def __init__(
        self,
        *,
        cache_dir: Path,
        robots_rules: dict[str, list[str]],
        timeout_s: float = DEFAULT_TIMEOUT_S,
        retries: int = DEFAULT_RETRIES,
        sleep_s: float = DEFAULT_SLEEP_S,
        opener: Callable[..., object] | None = None,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.robots_rules = robots_rules
        self.timeout_s = timeout_s
        self.retries = retries
        self.sleep_s = sleep_s
        self._opener = opener or urlopen
        self._clock = clock or time.time
        self._sleep = sleeper or time.sleep
        self._last_request_at = 0.0
        self.stats = {"network": 0, "cache": 0, "retries": 0, "denied": 0, "failures": 0}

    def _cache_paths(self, url: str) -> tuple[Path, Path]:
        key = cache_key(url)
        return self.cache_dir / f"{key}.body", self.cache_dir / f"{key}.meta.json"

    def load_cache(self, url: str) -> FetchResult | None:
        body_path, meta_path = self._cache_paths(url)
        if not body_path.is_file() or not meta_path.is_file():
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        body = body_path.read_bytes()
        encoding = meta.get("encoding") or "utf-8"
        return FetchResult(
            url=url,
            ok=bool(meta.get("ok", True)),
            status=meta.get("status"),
            body=body.decode(encoding, errors="replace"),
            error=meta.get("error"),
            from_cache=True,
            content_type=meta.get("content_type") or "",
        )

    def _store_cache(self, url: str, result: FetchResult, raw: bytes, encoding: str) -> None:
        body_path, meta_path = self._cache_paths(url)
        body_path.write_bytes(raw[:MAX_BODY_BYTES])
        meta_path.write_text(
            json.dumps(
                {
                    "url": url,
                    "ok": result.ok,
                    "status": result.status,
                    "error": result.error,
                    "encoding": encoding,
                    "content_type": result.content_type,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _throttle(self) -> None:
        if self.sleep_s <= 0:
            return
        now = self._clock()
        wait = self.sleep_s - (now - self._last_request_at)
        if wait > 0:
            self._sleep(wait)

    def fetch(self, url: str, *, use_cache: bool = True) -> FetchResult:
        if not _host_allowed(url):
            self.stats["denied"] += 1
            return FetchResult(url=url, ok=False, error="host_not_allowed")
        parsed = urlparse(url)
        target = parsed.path or "/"
        if parsed.query:
            target = f"{target}?{parsed.query}"
        if not robots_allows(url, self.robots_rules):
            self.stats["denied"] += 1
            return FetchResult(url=url, ok=False, error="robots_disallowed")
        request_url = encode_http_url(url)
        if use_cache:
            cached = self.load_cache(url) or self.load_cache(request_url)
            if cached is not None:
                cached.url = url
                self.stats["cache"] += 1
                return cached

        last_error = "unknown"
        last_status = None
        for attempt in range(1, self.retries + 1):
            self._throttle()
            self._last_request_at = self._clock()
            started = self._clock()
            try:
                req = Request(
                    request_url,
                    headers={
                        "User-Agent": USER_AGENT,
                        "Accept": "text/html,application/xml,text/xml,application/json;q=0.9,*/*;q=0.8",
                    },
                    method="GET",
                )
                with self._opener(req, timeout=self.timeout_s) as resp:  # type: ignore[arg-type]
                    raw = resp.read(MAX_BODY_BYTES + 1)
                    if len(raw) > MAX_BODY_BYTES:
                        raise OSError("response_too_large")
                    status = getattr(resp, "status", None) or resp.getcode()
                    headers = getattr(resp, "headers", {})
                    content_type = ""
                    encoding = "utf-8"
                    if headers is not None and hasattr(headers, "get"):
                        content_type = headers.get("Content-Type") or ""
                        charset = "utf-8"
                        if "charset=" in content_type.lower():
                            charset = content_type.split("charset=", 1)[1].split(";")[0].strip()
                            encoding = charset or "utf-8"
                    body = raw.decode(encoding, errors="replace")
                    elapsed = int((self._clock() - started) * 1000)
                    result = FetchResult(
                        url=url,
                        ok=True,
                        status=int(status) if status else 200,
                        body=body,
                        from_cache=False,
                        elapsed_ms=elapsed,
                        content_type=content_type,
                    )
                    self._store_cache(url, result, raw, encoding)
                    if request_url != url:
                        self._store_cache(request_url, result, raw, encoding)
                    self.stats["network"] += 1
                    return result
            except HTTPError as exc:
                last_status = exc.code
                last_error = f"http_{exc.code}"
                if exc.code in {404, 410, 451}:
                    break
            except (URLError, TimeoutError, OSError) as exc:
                last_error = str(exc)
            self.stats["retries"] += 1
            if attempt < self.retries:
                self._sleep(min(32.0, 2**attempt))
        self.stats["failures"] += 1
        result = FetchResult(url=url, ok=False, status=last_status, error=last_error)
        return result
