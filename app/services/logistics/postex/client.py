"""Typed async Postex HTTP client. Secrets never logged."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from app.core.logging import get_logger
from app.services.logistics.exceptions import (
    ProviderAmbiguousWriteError,
    ProviderAuthenticationError,
    ProviderConflictError,
    ProviderError,
    ProviderNotFoundError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderTransientError,
    ProviderValidationError,
)
from app.services.logistics.redaction import redact_secrets

logger = get_logger(__name__)

_JSON_ACCEPT = "application/json"
_MAX_READ_RETRIES = 2
_RETRY_STATUSES = {429, 500, 502, 503, 504}


def _parse_api_result(payload: Any) -> tuple[bool | None, str | None]:
    if not isinstance(payload, dict):
        return None, None
    success = payload.get("isSuccess")
    if success is None:
        success = payload.get("IsSuccess")
    message = payload.get("message")
    if message is None:
        message = payload.get("Message")
    if isinstance(success, bool):
        return success, str(message) if message is not None else None
    return None, str(message) if message is not None else None


class PostexClient:
    """Single-responsibility HTTP client for api.postex.ir."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self.timeout = httpx.Timeout(
            timeout_seconds,
            connect=min(10.0, timeout_seconds),
        )

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "Accept": _JSON_ACCEPT,
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any | None = None,
        params: dict[str, Any] | None = None,
        mutating: bool = False,
        expect_bytes: bool = False,
        operation: str,
    ) -> Any:
        attempts = 1 if mutating else _MAX_READ_RETRIES
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            started = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method,
                        self._url(path),
                        headers=self._headers(),
                        json=json_body,
                        params=params,
                    )
            except httpx.TimeoutException as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                logger.warning(
                    "postex timeout operation=%s method=%s status=timeout duration_ms=%s attempt=%s",
                    operation,
                    method,
                    duration_ms,
                    attempt,
                )
                last_error = ProviderTimeoutError(
                    f"Postex timeout on {operation}",
                    ambiguous_write=mutating,
                )
                if mutating:
                    raise last_error from exc
                if attempt >= attempts:
                    raise last_error from exc
                await asyncio.sleep(0.25 * attempt)
                continue
            except httpx.HTTPError as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                logger.warning(
                    "postex network operation=%s method=%s duration_ms=%s attempt=%s",
                    operation,
                    method,
                    duration_ms,
                    attempt,
                )
                if mutating:
                    raise ProviderAmbiguousWriteError(
                        f"Ambiguous mutating Postex request on {operation}",
                    ) from exc
                last_error = ProviderTransientError(
                    f"Postex network error on {operation}",
                )
                if attempt >= attempts:
                    raise last_error from exc
                await asyncio.sleep(0.25 * attempt)
                continue

            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "postex operation=%s method=%s http_status=%s duration_ms=%s",
                operation,
                method,
                response.status_code,
                duration_ms,
            )
            if expect_bytes:
                if 200 <= response.status_code < 300:
                    return response.content
                self._raise_for_status(response, operation=operation, mutating=mutating)

            payload = self._decode_json(response)
            success, message = _parse_api_result(payload)
            if 200 <= response.status_code < 300:
                if success is False:
                    raise ProviderValidationError(
                        message or f"Postex rejected {operation}",
                        http_status=response.status_code,
                    )
                return payload
            if not mutating and response.status_code in _RETRY_STATUSES and attempt < attempts:
                await asyncio.sleep(0.25 * attempt)
                continue
            self._raise_for_status(
                response,
                operation=operation,
                mutating=mutating,
                payload=payload,
                message=message,
            )
        assert last_error is not None
        raise last_error

    def _decode_json(self, response: httpx.Response) -> Any:
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return {"_non_json": True, "http_status": response.status_code}

    def _raise_for_status(
        self,
        response: httpx.Response,
        *,
        operation: str,
        mutating: bool,
        payload: Any | None = None,
        message: str | None = None,
    ) -> None:
        status = response.status_code
        text = message or f"Postex HTTP {status} on {operation}"
        # Never include raw body (may contain PII) in the exception message.
        _ = redact_secrets(payload) if payload else None
        if status in {401, 403}:
            raise ProviderAuthenticationError(text, http_status=status)
        if status == 404:
            raise ProviderNotFoundError(text, http_status=status)
        if status == 409:
            raise ProviderConflictError(text, http_status=status)
        if status == 429:
            raise ProviderRateLimitError(text, http_status=status)
        if status in {400, 422}:
            raise ProviderValidationError(text, http_status=status)
        if status >= 500:
            if mutating:
                raise ProviderAmbiguousWriteError(
                    f"Ambiguous Postex HTTP {status} on {operation}",
                    http_status=status,
                )
            raise ProviderTransientError(text, http_status=status, retryable=True)
        raise ProviderError(text, http_status=status)

    async def whoami(self) -> Any:
        return await self.request("GET", "/user/whoami", operation="whoami")

    async def get_json(
        self, path: str, *, operation: str, params: dict[str, Any] | None = None
    ) -> Any:
        return await self.request("GET", path, operation=operation, params=params)

    async def post_json(
        self,
        path: str,
        body: Any,
        *,
        operation: str,
        mutating: bool,
    ) -> Any:
        return await self.request(
            "POST",
            path,
            json_body=json_body_or_none(body),
            operation=operation,
            mutating=mutating,
        )

    async def patch_json(self, path: str, body: Any, *, operation: str) -> Any:
        return await self.request(
            "PATCH",
            path,
            json_body=body,
            operation=operation,
            mutating=True,
        )

    async def get_bytes(self, path: str, *, operation: str) -> bytes:
        result = await self.request(
            "GET",
            path,
            operation=operation,
            expect_bytes=True,
        )
        if not isinstance(result, bytes | bytearray):
            raise ProviderValidationError(f"Postex {operation} did not return bytes")
        return bytes(result)


def json_body_or_none(body: Any) -> Any:
    return body
