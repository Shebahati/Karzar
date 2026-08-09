"""Bounded HTTP GET/HEAD transport with retries and 429 backoff."""

from __future__ import annotations

import asyncio
import hashlib
import io
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

from .contracts import AssetValidation, BaselineError, RunCounters
from .placeholders import mark_placeholder, normalize_asset_url

DEFAULT_TIMEOUT_S = 20.0
DEFAULT_RETRIES = 2
MAX_ASSET_BYTES = 25 * 1024 * 1024


@dataclass
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    content: bytes
    url: str


TransportFn = Callable[[str, str], HttpResponse]
# method, url -> response


@dataclass
class RateLimitedTransport:
    """Async-friendly transport using httpx; injectable sync fetch for tests."""

    counters: RunCounters
    timeout_s: float = DEFAULT_TIMEOUT_S
    retries: int = DEFAULT_RETRIES
    api_concurrency: int = 4
    asset_concurrency: int = 8
    per_host_concurrency: int = 6
    sync_fetch: TransportFn | None = None
    _api_sem: asyncio.Semaphore = field(init=False)
    _asset_sem: asyncio.Semaphore = field(init=False)
    _host_sems: dict[str, asyncio.Semaphore] = field(default_factory=dict)
    _host_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _client: httpx.AsyncClient | None = None

    def __post_init__(self) -> None:
        self._api_sem = asyncio.Semaphore(self.api_concurrency)
        self._asset_sem = asyncio.Semaphore(self.asset_concurrency)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout_s,
                follow_redirects=True,
                headers={"User-Agent": "Karzar-IMG-FAST-01A-baseline/1.0"},
            )
        return self._client

    async def _host_sem(self, url: str) -> asyncio.Semaphore:
        host = (urlparse(url).netloc or "").lower() or "_"
        async with self._host_lock:
            if host not in self._host_sems:
                self._host_sems[host] = asyncio.Semaphore(self.per_host_concurrency)
            return self._host_sems[host]

    def _reject_writes(self, method: str) -> None:
        m = method.upper()
        if m not in {"GET", "HEAD"}:
            self.counters.api_write_requests += 1
            raise BaselineError("http", f"forbidden method {method}")

    async def request(
        self,
        method: str,
        url: str,
        *,
        kind: str,
        allow_body: bool = True,
    ) -> HttpResponse:
        self._reject_writes(method)
        if kind == "api":
            gate = self._api_sem
        elif kind == "asset":
            gate = self._asset_sem
        else:
            raise BaselineError("http", f"unknown kind {kind}")

        host_sem = await self._host_sem(url)
        attempt = 0
        last_exc: Exception | None = None
        while attempt <= self.retries:
            attempt += 1
            async with gate:
                async with host_sem:
                    try:
                        resp = await self._do_fetch(method, url, allow_body=allow_body)
                    except Exception as exc:  # noqa: BLE001 — counted then retried
                        last_exc = exc
                        await asyncio.sleep(min(2 ** (attempt - 1), 8))
                        continue
            if resp.status_code == 429:
                self.counters.count_429 += 1
                ra = resp.headers.get("retry-after") or resp.headers.get("Retry-After")
                sleep_s = float(ra) if ra and str(ra).replace(".", "", 1).isdigit() else min(
                    2 ** attempt, 30
                )
                await asyncio.sleep(sleep_s)
                continue
            if 500 <= resp.status_code <= 599:
                if attempt <= self.retries:
                    await asyncio.sleep(min(2 ** (attempt - 1), 8))
                    continue
                self.counters.count_5xx_exhausted += 1
                return resp
            return resp
        self.counters.other_exhausted_network_failures += 1
        raise BaselineError("http", f"exhausted retries for {url}: {last_exc}")

    async def _do_fetch(self, method: str, url: str, *, allow_body: bool) -> HttpResponse:
        if self.sync_fetch is not None:
            return self.sync_fetch(method, url)
        client = self._ensure_client()
        if method.upper() == "HEAD":
            r = await client.head(url)
            headers = {k.lower(): v for k, v in r.headers.items()}
            return HttpResponse(r.status_code, headers, b"", str(r.url))
        r = await client.get(url)
        content = r.content if allow_body else b""
        if len(content) > MAX_ASSET_BYTES:
            raise BaselineError("http", f"payload exceeds max bytes for {url}")
        headers = {k.lower(): v for k, v in r.headers.items()}
        return HttpResponse(r.status_code, headers, content, str(r.url))

    async def get_json(self, url: str, *, kind: str = "api") -> Any:
        resp = await self.request("GET", url, kind=kind)
        if resp.status_code != 200:
            raise BaselineError("http", f"GET {url} -> {resp.status_code}")
        import json

        return json.loads(resp.content.decode("utf-8"))


def decode_image_bytes(data: bytes) -> tuple[bool, int | None, int | None, str | None]:
    """Return decode_ok, width, height, error."""
    if not data:
        return False, None, None, "empty_payload"
    try:
        from PIL import Image, ImageFile

        ImageFile.LOAD_TRUNCATED_IMAGES = False
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        with Image.open(io.BytesIO(data)) as im2:
            width, height = int(im2.width), int(im2.height)
            im2.load()
        return True, width, height, None
    except Exception as exc:  # noqa: BLE001
        return False, None, None, f"decode_failed:{type(exc).__name__}"


async def validate_asset(
    transport: RateLimitedTransport,
    url: str,
    *,
    cache: dict[str, AssetValidation],
) -> AssetValidation:
    norm = normalize_asset_url(url)
    if norm in cache:
        return cache[norm]

    transport.counters.asset_validation_requests += 1
    result = AssetValidation(url=url, normalized_url=norm)
    try:
        resp = await transport.request("GET", url, kind="asset")
    except BaselineError as exc:
        result.error = str(exc)
        result.transient_exhausted = True
        cache[norm] = result
        return result

    result.attempts = transport.retries + 1
    result.http_status = resp.status_code
    result.final_url = resp.url
    result.content_type = resp.headers.get("content-type")
    result.byte_size = len(resp.content)
    if resp.status_code != 200:
        result.error = f"http_{resp.status_code}"
        result.transient_exhausted = 500 <= resp.status_code <= 599 or resp.status_code == 429
        cache[norm] = result
        return result

    result.sha256 = hashlib.sha256(resp.content).hexdigest()
    ok, w, h, err = decode_image_bytes(resp.content)
    result.decode_ok = ok
    result.width = w
    result.height = h
    result.error = err
    result.is_known_placeholder = mark_placeholder(url, result.sha256) or mark_placeholder(
        result.final_url, result.sha256
    )
    cache[norm] = result
    return result


def sleep_sync(seconds: float) -> None:
    time.sleep(seconds)
