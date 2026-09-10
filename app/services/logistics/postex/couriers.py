"""Postex courier/service pairs and live-verified quote request fragments.

Provider-local reference data — not Karzar domain assumptions.
Live evidence 2026-09-10: POST /shipping/quotes requires `courier` and
`value_added_service` even though OpenAPI marks them optional.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Exact OptionalServices shape from OpenAPI + successful live quote request.
MINIMAL_VALUE_ADDED_SERVICE: dict[str, bool] = {
    "request_label": False,
    "request_packaging": False,
    "request_sms_notification": False,
}


@dataclass(frozen=True)
class PostexCourierService:
    """One Postex courier_code + service_type pair (GetQuotesCourier)."""

    courier_code: str
    service_type: str
    service_name: str | None = None
    courier_service_id: int | None = None
    is_active: bool = True

    def as_quote_courier(self) -> dict[str, str]:
        """Live-compatible GetQuotesCourier object."""
        return {
            "courier_code": self.courier_code,
            "service_type": self.service_type,
        }


# Live-verified enabled v1 pair (IR_POST / EXPRESS). Config may override.
LIVE_VERIFIED_V1_QUOTE_SERVICE = PostexCourierService(
    courier_code="IR_POST",
    service_type="EXPRESS",
    service_name="پست پیشتاز",
    courier_service_id=18,
    is_active=True,
)


def parse_quote_services_config(raw: str | None) -> list[PostexCourierService]:
    """Parse `POSTEX_QUOTE_SERVICES` as comma-separated `COURIER:SERVICE` pairs."""
    text = (raw or "").strip()
    if not text:
        return [LIVE_VERIFIED_V1_QUOTE_SERVICE]
    out: list[PostexCourierService] = []
    seen: set[tuple[str, str]] = set()
    for part in text.split(","):
        token = part.strip()
        if not token:
            continue
        if ":" not in token:
            raise ValueError(
                "POSTEX_QUOTE_SERVICES entries must be COURIER_CODE:SERVICE_TYPE "
                f"(got {token!r})"
            )
        courier, service = token.split(":", 1)
        courier_code = courier.strip()
        service_type = service.strip()
        if not courier_code or not service_type:
            raise ValueError(f"Invalid POSTEX_QUOTE_SERVICES entry: {token!r}")
        key = (courier_code, service_type)
        if key in seen:
            continue
        seen.add(key)
        out.append(PostexCourierService(courier_code=courier_code, service_type=service_type))
    if not out:
        return [LIVE_VERIFIED_V1_QUOTE_SERVICE]
    return out


def _shipping_method_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        # Single method object
        if any(k in payload for k in ("courierCode", "courier_code", "courierServiceCode")):
            return [payload]
    return []


def parse_shipping_methods(payload: Any) -> list[PostexCourierService]:
    """Map live `/shipping-methods` rows into typed courier/service pairs."""
    services: list[PostexCourierService] = []
    seen: set[tuple[str, str]] = set()
    for item in _shipping_method_items(payload):
        courier = str(
            item.get("courierCode")
            or item.get("courier_code")
            or item.get("courierCodeAlias")
            or ""
        ).strip()
        service = str(
            item.get("courierServiceCode")
            or item.get("service_type")
            or item.get("serviceType")
            or item.get("courier_service_code")
            or ""
        ).strip()
        if not courier or not service:
            continue
        key = (courier, service)
        if key in seen:
            continue
        seen.add(key)
        active = item.get("isActive")
        if active is None:
            active = item.get("is_active")
        services.append(
            PostexCourierService(
                courier_code=courier,
                service_type=service,
                service_name=(
                    str(item["courierServiceName"]).strip()
                    if item.get("courierServiceName")
                    else (
                        str(item["service_name"]).strip() if item.get("service_name") else None
                    )
                ),
                courier_service_id=(
                    int(item["courierServiceId"])
                    if item.get("courierServiceId") is not None
                    else (
                        int(item["id"])
                        if isinstance(item.get("id"), int)
                        else None
                    )
                ),
                is_active=True if active is None else bool(active),
            )
        )
    return services


def select_quote_services(
    configured: list[PostexCourierService],
    catalog: list[PostexCourierService] | None,
) -> list[PostexCourierService]:
    """Deterministic enabled set: configured pairs, optionally intersected with live catalog."""
    if not configured:
        configured = [LIVE_VERIFIED_V1_QUOTE_SERVICE]
    if not catalog:
        return list(configured)
    active = {(s.courier_code, s.service_type): s for s in catalog if s.is_active}
    selected: list[PostexCourierService] = []
    for cfg in configured:
        key = (cfg.courier_code, cfg.service_type)
        live = active.get(key)
        if live is None:
            # Do not invent unsupported carriers; skip pairs absent from catalog.
            continue
        selected.append(
            PostexCourierService(
                courier_code=live.courier_code,
                service_type=live.service_type,
                service_name=live.service_name or cfg.service_name,
                courier_service_id=live.courier_service_id,
                is_active=True,
            )
        )
    return selected
