"""HTTP client for Emalls token validation (wp_plugin.ashx)."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.emalls.exceptions import (
    EmallsTokenInvalidError,
    EmallsValidationUnavailableError,
)

logger = get_logger(__name__)

# Official Emalls plugin v1.3.0 exact acceptance message (case-insensitive after trim).
_VALID_TOKEN_MESSAGE = "the token is valid"


class EmallsClient:
    """Isolated outbound client for Emalls token validation only."""

    def __init__(
        self,
        *,
        validation_url: str | None = None,
        shop_domain: str | None = None,
        timeout_seconds: float | None = None,
        version: str | None = None,
    ) -> None:
        self.validation_url = (
            validation_url if validation_url is not None else settings.EMALLS_VALIDATION_URL
        )
        self.shop_domain = (
            shop_domain if shop_domain is not None else settings.EMALLS_SHOP_DOMAIN
        ).strip().lower()
        timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.EMALLS_HTTP_TIMEOUT_SECONDS
        )
        self.timeout = httpx.Timeout(timeout, connect=min(5.0, timeout))
        # Protocol compatibility version (official plugin sends 1.3.0).
        self.version = (
            version if version is not None else settings.EMALLS_COMPAT_VERSION
        )

    async def validate_token(self, token: str) -> None:
        """Validate token with Emalls. Raises on invalid or transport failure.

        Never logs the raw token.
        Accepts only success=true AND message exactly ``the token is valid``.
        """
        form: dict[str, Any] = {
            "token": token,
            "shop_domain": self.shop_domain,
            "version": self.version,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.validation_url, data=form)
        except httpx.TimeoutException as exc:
            logger.warning(
                "integration=emalls validation_result=timeout shop_domain=%s",
                self.shop_domain,
            )
            raise EmallsValidationUnavailableError(
                "Emalls token validation timed out"
            ) from exc
        except httpx.HTTPError as exc:
            logger.warning(
                "integration=emalls validation_result=http_error shop_domain=%s reason=%s",
                self.shop_domain,
                type(exc).__name__,
            )
            raise EmallsValidationUnavailableError(
                "Emalls token validation service unavailable"
            ) from exc

        if response.status_code >= 500:
            logger.warning(
                "integration=emalls validation_result=upstream_5xx status=%s",
                response.status_code,
            )
            raise EmallsValidationUnavailableError(
                "Emalls token validation service unavailable"
            )

        if response.status_code >= 400:
            logger.info(
                "integration=emalls validation_result=invalid status=%s",
                response.status_code,
            )
            raise EmallsTokenInvalidError("Emalls token is invalid")

        try:
            payload = response.json()
        except ValueError as exc:
            logger.warning("integration=emalls validation_result=non_json")
            raise EmallsValidationUnavailableError(
                "Emalls token validation returned non-JSON"
            ) from exc

        if not isinstance(payload, dict):
            logger.warning("integration=emalls validation_result=non_object")
            raise EmallsValidationUnavailableError(
                "Emalls token validation returned unexpected payload"
            )

        success_raw = payload.get("success")
        if success_raw is None:
            success_raw = payload.get("Success")
        success = success_raw is True

        raw_message = payload.get("message")
        if raw_message is None:
            raw_message = payload.get("Message")
        message = str(raw_message or "").strip().lower()

        if success and message == _VALID_TOKEN_MESSAGE:
            logger.info(
                "integration=emalls validation_result=success shop_domain=%s "
                "compat_version=%s",
                self.shop_domain,
                self.version,
            )
            return

        logger.info(
            "integration=emalls validation_result=invalid shop_domain=%s",
            self.shop_domain,
        )
        raise EmallsTokenInvalidError("Emalls token is invalid")


def get_emalls_client() -> EmallsClient:
    return EmallsClient()
