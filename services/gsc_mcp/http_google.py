from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from services.gsc_mcp.errors import ErrorCode, GscMcpError
from services.gsc_mcp.redaction import redact_text

logger = logging.getLogger(__name__)

ALLOWED_GOOGLE_HOSTS = frozenset(
    {
        "oauth2.googleapis.com",
        "www.googleapis.com",
        "searchconsole.googleapis.com",
        "chromeuxreport.googleapis.com",
    }
)


@dataclass
class GoogleHttpResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes

    def json(self) -> Any:
        import json

        return json.loads(self.content.decode("utf-8"))


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise GscMcpError(ErrorCode.INVALID_ARGUMENT, "Only https Google API URLs are allowed")
    host = parsed.hostname or ""
    if host not in ALLOWED_GOOGLE_HOSTS:
        raise GscMcpError(ErrorCode.INVALID_ARGUMENT, f"Disallowed upstream host: {host}")


def map_upstream_error(status_code: int, body_text: str) -> GscMcpError:
    safe = redact_text(body_text[:500])
    if status_code == 429:
        return GscMcpError(ErrorCode.UPSTREAM_RATE_LIMITED, "Google API rate limited", details={"body": safe})
    if status_code == 403:
        return GscMcpError(ErrorCode.UPSTREAM_PERMISSION_DENIED, "Google API permission denied", details={"body": safe})
    if status_code >= 500:
        return GscMcpError(ErrorCode.UPSTREAM_UNAVAILABLE, "Google API unavailable", details={"body": safe})
    return GscMcpError(ErrorCode.INTERNAL_ERROR, f"Google API error HTTP {status_code}", details={"body": safe})


@dataclass
class GoogleHttpClient:
    timeout_seconds: float
    max_retries: int
    user_agent: str
    token_provider: Any | None
    max_response_bytes: int = 5_000_000

    def request(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        form_body: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        skip_auth: bool = False,
        extra_headers: dict[str, str] | None = None,
    ) -> GoogleHttpResponse:
        if json_body is not None and form_body is not None:
            raise GscMcpError(
                ErrorCode.INVALID_ARGUMENT,
                "json_body and form_body are mutually exclusive",
            )
        _validate_url(url)
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        if not skip_auth:
            if not self.token_provider:
                raise GscMcpError(ErrorCode.AUTH_NOT_CONFIGURED, "Google auth not configured")
            headers.update(self.token_provider.auth_headers())

        attempt = 0
        last_exc: Exception | None = None
        while attempt <= self.max_retries:
            attempt += 1
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.request(
                        method,
                        url,
                        json=json_body,
                        data=form_body,
                        params=params,
                        headers=headers,
                    )
                content = response.content
                if len(content) > self.max_response_bytes:
                    raise GscMcpError(
                        ErrorCode.INVALID_ARGUMENT,
                        f"Response exceeds max size ({self.max_response_bytes} bytes)",
                    )
                if response.status_code in {429, 500, 502, 503, 504} and attempt <= self.max_retries:
                    sleep_s = min(2 ** (attempt - 1), 8)
                    logger.warning(
                        "Retrying Google request status=%s attempt=%s url_host=%s",
                        response.status_code,
                        attempt,
                        urlparse(url).hostname,
                    )
                    time.sleep(sleep_s)
                    continue
                if response.status_code >= 400:
                    raise map_upstream_error(response.status_code, response.text)
                return GoogleHttpResponse(
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    content=content,
                )
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt > self.max_retries:
                    raise GscMcpError(ErrorCode.UPSTREAM_UNAVAILABLE, "Google API request timed out") from exc
                time.sleep(min(2 ** (attempt - 1), 8))
            except GscMcpError:
                raise
            except Exception as exc:
                last_exc = exc
                if attempt > self.max_retries:
                    raise GscMcpError(ErrorCode.INTERNAL_ERROR, "Google API request failed") from exc
                time.sleep(min(2 ** (attempt - 1), 8))
        raise GscMcpError(ErrorCode.INTERNAL_ERROR, "Google API request failed") from last_exc
