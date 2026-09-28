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

ADAPTER_VERSION_FOR_VALIDATOR = "1.0.0"


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
        self.version = version if version is not None else ADAPTER_VERSION_FOR_VALIDATOR

    async def validate_token(self, token: str) -> None:
        """Validate token with Emalls. Raises on invalid or transport failure.

        Never logs the raw token.
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

        success = False
        message = ""
        if isinstance(payload, dict):
            success = bool(payload.get("success") is True or payload.get("Success") is True)
            raw_message = payload.get("message")
            if raw_message is None:
                raw_message = payload.get("Message")
            message = str(raw_message or "").strip().lower()

        if success and ("valid" in message or message == ""):
            logger.info(
                "integration=emalls validation_result=success shop_domain=%s",
                self.shop_domain,
            )
            return

        logger.info(
            "integration=emalls validation_result=invalid shop_domain=%s",
            self.shop_domain,
        )
        raise EmallsTokenInvalidError("Emalls token is invalid")


def get_emalls_client() -> EmallsClient:
    return EmallsClient()
