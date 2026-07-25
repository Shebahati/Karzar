"""Async HTTP client for Hesabfa (حسابفا) REST API v1."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.hesabfa.exceptions import HesabfaApiError, HesabfaNotConfiguredError

logger = get_logger(__name__)

# InvoiceType: 0 = sale
INVOICE_TYPE_SALE = 0
# Invoice Status (typestable): 0 = draft (پیش‌نویس), 1 = approved (تأیید شده)
INVOICE_STATUS_DRAFT = 0
INVOICE_STATUS_APPROVED = 1
# ContactType: 1 = customer (اشخاص حقیقی / مشتری)
CONTACT_TYPE_CUSTOMER = 1


class HesabfaClient:
    """Thin wrapper around Hesabfa JSON POST endpoints."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        login_token: str | None = None,
        user_id: str | None = None,
        password: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else settings.HESABFA_API_KEY
        self.login_token = (
            login_token if login_token is not None else settings.HESABFA_LOGIN_TOKEN
        )
        self.user_id = user_id if user_id is not None else settings.HESABFA_USER_ID
        self.password = password if password is not None else settings.HESABFA_PASSWORD
        self.base_url = (base_url or settings.HESABFA_BASE_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.HESABFA_TIMEOUT_SECONDS

    def is_configured(self) -> bool:
        has_key = bool(self.api_key and self.api_key.strip())
        has_token = bool(self.login_token and self.login_token.strip())
        has_user_pass = bool(
            self.user_id and self.user_id.strip() and self.password and self.password.strip()
        )
        return has_key and (has_token or has_user_pass)

    def _auth_payload(self) -> dict[str, Any]:
        if not self.is_configured():
            raise HesabfaNotConfiguredError(
                "Hesabfa credentials missing (need HESABFA_API_KEY and "
                "HESABFA_LOGIN_TOKEN, or userId/password)"
            )
        payload: dict[str, Any] = {"apiKey": self.api_key}
        if self.login_token and self.login_token.strip():
            payload["loginToken"] = self.login_token
        if self.user_id and self.user_id.strip():
            payload["userId"] = self.user_id
        if self.password and self.password.strip():
            payload["password"] = self.password
        return payload

    async def _post(self, path: str, body: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}/{path.lstrip('/')}"
        payload = {**self._auth_payload(), **(body or {})}
        # Never log apiKey / loginToken / password.
        logger.debug("Hesabfa request path=%s keys=%s", path, sorted((body or {}).keys()))
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise HesabfaApiError(f"Hesabfa timeout calling {path}") from exc
        except httpx.HTTPError as exc:
            raise HesabfaApiError(f"Hesabfa HTTP error calling {path}: {exc}") from exc

        if response.status_code >= 400:
            raise HesabfaApiError(
                f"Hesabfa HTTP {response.status_code} for {path}",
                status_code=response.status_code,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise HesabfaApiError(f"Hesabfa returned non-JSON for {path}") from exc

        if not isinstance(data, dict):
            raise HesabfaApiError(f"Hesabfa unexpected payload type for {path}")

        if not data.get("Success", False):
            raise HesabfaApiError(
                data.get("ErrorMessage") or f"Hesabfa call failed: {path}",
                error_code=data.get("ErrorCode"),
            )
        return data.get("Result")

    async def get_items(
        self,
        *,
        take: int = 100,
        skip: int = 0,
        filters: list[dict[str, Any]] | None = None,
        sort_by: str = "Code",
        sort_desc: bool = False,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {
            "sortBy": sort_by,
            "sortDesc": sort_desc,
            "take": take,
            "skip": skip,
        }
        if filters:
            query["filters"] = filters
        result = await self._post("item/getItems", {"queryInfo": query})
        return result if isinstance(result, dict) else {"List": [], "TotalCount": 0}

    async def get_quantity(
        self,
        *,
        codes: list[str] | None = None,
        warehouse_code: int | None = None,
    ) -> list[dict[str, Any]]:
        body: dict[str, Any] = {}
        if codes is not None:
            body["codes"] = codes
        wh = warehouse_code if warehouse_code is not None else settings.HESABFA_WAREHOUSE_CODE
        if wh is not None:
            body["warehouseCode"] = wh
        result = await self._post("item/GetQuantity", body)
        if isinstance(result, list):
            return result
        return []

    async def save_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Create or update a Hesabfa item (کالا). Stock/qty is not set here (defaults to 0)."""
        result = await self._post("item/save", {"item": item})
        return result if isinstance(result, dict) else {}

    async def get_contacts(
        self,
        *,
        take: int = 20,
        skip: int = 0,
        filters: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {
            "sortBy": "Code",
            "sortDesc": False,
            "take": take,
            "skip": skip,
        }
        if filters:
            query["filters"] = filters
        result = await self._post("contact/getContacts", {"queryInfo": query})
        return result if isinstance(result, dict) else {"List": [], "TotalCount": 0}

    async def save_contact(self, contact: dict[str, Any]) -> dict[str, Any]:
        result = await self._post("contact/save", {"contact": contact})
        return result if isinstance(result, dict) else {}

    async def save_invoice(self, invoice: dict[str, Any]) -> dict[str, Any]:
        result = await self._post("invoice/save", {"invoice": invoice})
        return result if isinstance(result, dict) else {}

    async def get_invoices(
        self,
        *,
        invoice_type: int = INVOICE_TYPE_SALE,
        take: int = 100,
        skip: int = 0,
        filters: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {
            "sortBy": "Date",
            "sortDesc": True,
            "take": take,
            "skip": skip,
        }
        if filters:
            query["filters"] = filters
        result = await self._post(
            "invoice/getInvoices",
            {"type": invoice_type, "queryInfo": query},
        )
        return result if isinstance(result, dict) else {"List": [], "TotalCount": 0}

    async def profit_and_loss(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        project: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if start_date:
            body["startDate"] = start_date
        if end_date:
            body["endDate"] = end_date
        if project:
            body["project"] = project
        result = await self._post("report/profitandlossStatement", body)
        return result if isinstance(result, dict) else {}


_client: HesabfaClient | None = None


def get_hesabfa_client() -> HesabfaClient:
    global _client
    if _client is None:
        _client = HesabfaClient()
    return _client


def reset_hesabfa_client_for_tests() -> None:
    global _client
    _client = None


def hesabfa_integration_active() -> bool:
    """True when feature flag is on and credentials are present."""
    if not settings.HESABFA_ENABLED:
        return False
    return get_hesabfa_client().is_configured()
