"""Parse Postex JSON into provider-neutral DTOs. Official response bodies are often undocumented."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.services.logistics.exceptions import ShippingUnavailableError
from app.services.logistics.models import (
    BoxType,
    LocationCity,
    ParcelBooking,
    ParcelLookup,
    QuoteResult,
    ShippingServiceOption,
    TrackingEvent,
)
from app.services.logistics.money import IRR, irr_to_toman
from app.services.logistics.redaction import redact_secrets


def _as_list(payload: Any) -> list[Any]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "items", "result", "cities", "provinces", "boxes", "statuses"):
            inner = payload.get(key)
            if isinstance(inner, list):
                return inner
            if isinstance(inner, dict):
                nested = _as_list(inner)
                if nested:
                    return nested
    return []


def _int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_cities(payload: Any) -> list[LocationCity]:
    cities: list[LocationCity] = []
    for item in _as_list(payload):
        if not isinstance(item, dict):
            continue
        code = _int(item.get("id") or item.get("code") or item.get("city_id") or item.get("cityId"))
        name = _str(item.get("name") or item.get("city_name") or item.get("title"))
        if code is None or not name:
            continue
        cities.append(
            LocationCity(
                code=code,
                name=name,
                province_code=_int(
                    item.get("province_code")
                    or item.get("provinceId")
                    or item.get("province_id")
                    or item.get("state_id")
                ),
                province_name=_str(
                    item.get("province_name") or item.get("provinceName") or item.get("state_name")
                ),
            )
        )
    return cities


def parse_boxes(payload: Any) -> list[BoxType]:
    boxes: list[BoxType] = []
    for item in _as_list(payload):
        if not isinstance(item, dict):
            continue
        box_id = _int(item.get("id") or item.get("box_type_id") or item.get("boxTypeId"))
        if box_id is None:
            continue
        boxes.append(
            BoxType(
                id=box_id,
                name=_str(item.get("name") or item.get("title")),
                length_cm=_int(item.get("length") or item.get("length_cm")),
                width_cm=_int(item.get("width") or item.get("width_cm")),
                height_cm=_int(item.get("height") or item.get("height_cm")),
            )
        )
    return boxes


def _service_fields(entry: dict[str, Any]) -> tuple[str, str, str, str | None]:
    carrier = (
        _str(
            entry.get("courier_code")
            or entry.get("courierCode")
            or entry.get("courier")
            or entry.get("name")
            or entry.get("provider")
        )
        or "UNKNOWN"
    )
    service = (
        _str(
            entry.get("service_type")
            or entry.get("serviceType")
            or entry.get("service_code")
            or entry.get("service")
        )
        or "STANDARD"
    )
    title = (
        _str(
            entry.get("service_name")
            or entry.get("title")
            or entry.get("display_name")
            or entry.get("name")
        )
        or f"{carrier} {service}"
    )
    eta = _str(entry.get("eta") or entry.get("sla") or entry.get("delivery_time"))
    return carrier, service, title, eta


def _decimal_amount(entry: dict[str, Any]) -> Decimal | None:
    for key in (
        "totalPrice",
        "total_price",
        "price",
        "amount",
        "service_price",
        "total",
    ):
        value = entry.get(key)
        if value is None:
            continue
        try:
            return Decimal(str(value))
        except Exception:
            continue
    return None


def parse_quotes(payload: Any) -> QuoteResult:
    raw = redact_secrets(payload) if isinstance(payload, dict) else {"value": payload}
    if not isinstance(payload, dict):
        raise ShippingUnavailableError("پاسخ استعلام ارسال قابل تفسیر نیست.")

    pickup_raw = payload.get("pickup_price")
    if pickup_raw is None:
        pickup_raw = payload.get("pickupPrice")
    pickup_toman: Decimal | None = None
    if pickup_raw is not None:
        pickup_toman = irr_to_toman(pickup_raw)

    options: list[ShippingServiceOption] = []
    shipping_prices = payload.get("shipping_prices") or payload.get("shippingPrices") or []
    if not isinstance(shipping_prices, list):
        shipping_prices = []

    for group in shipping_prices:
        if not isinstance(group, dict):
            continue
        services = (
            group.get("service_price")
            or group.get("servicePrice")
            or group.get("services")
            or [group]
        )
        if not isinstance(services, list):
            continue
        for service in services:
            if not isinstance(service, dict):
                continue
            amount = _decimal_amount(service)
            if amount is None:
                continue
            carrier, service_code, title, eta = _service_fields({**group, **service})
            toman = irr_to_toman(amount)
            customer = toman if pickup_toman is None else (toman + pickup_toman)
            options.append(
                ShippingServiceOption(
                    carrier_code=carrier,
                    service_code=service_code,
                    service_name=title,
                    provider_amount=amount,
                    provider_currency=IRR,
                    provider_amount_toman=toman,
                    customer_amount_toman=customer,
                    pickup_amount_toman=pickup_toman,
                    eta_text=eta,
                )
            )

    if not options:
        raise ShippingUnavailableError("هیچ سرویس ارسالی برای این مقصد برگردانده نشد.")

    from app.services.logistics.models import PackageSpec

    return QuoteResult(
        options=options,
        package=PackageSpec(length_cm=0, width_cm=0, height_cm=0, weight_grams=0),
        declared_value_irr=Decimal("0"),
        raw_provider_response=raw if isinstance(raw, dict) else {},
        pickup_amount_toman=pickup_toman,
    )


def parse_parcel_booking(payload: Any) -> ParcelBooking:
    raw = redact_secrets(payload) if isinstance(payload, dict) else {"value": payload}
    node: Any = payload
    if isinstance(payload, list) and payload:
        node = payload[0]
    if isinstance(node, dict):
        data = node.get("data") if isinstance(node.get("data"), dict) else node
        shipments = data.get("shipments") if isinstance(data, dict) else None
        first = None
        if isinstance(shipments, list) and shipments:
            first = shipments[0]
        elif isinstance(data, dict):
            first = data
        else:
            first = node
        tracking = {}
        if isinstance(first, dict):
            tracking = first.get("tracking") if isinstance(first.get("tracking"), dict) else {}
            barcode = _str(
                tracking.get("barcode")
                if tracking
                else first.get("barcode") or first.get("tracking_code") or first.get("trackingCode")
            )
            parcel_no = _str(
                first.get("parcel_no")
                or first.get("parcelNo")
                or first.get("id")
                or first.get("no")
                or (data.get("parcel_no") if isinstance(data, dict) else None)
            )
            courier = _str(
                (first.get("courier") or {}).get("name")
                if isinstance(first.get("courier"), dict)
                else first.get("courier") or first.get("courier_code")
            )
            service = _str(
                (first.get("courier") or {}).get("service_type")
                if isinstance(first.get("courier"), dict)
                else first.get("service_type")
            )
            status = _str(first.get("status") or first.get("status_code"))
            return ParcelBooking(
                provider_parcel_no=parcel_no,
                tracking_code=barcode,
                carrier_code=courier,
                service_code=service,
                provider_status=status,
                raw=raw if isinstance(raw, dict) else {},
            )
    return ParcelBooking(raw=raw if isinstance(raw, dict) else {})


def parse_parcel_lookup(payload: Any) -> ParcelLookup:
    if payload is None:
        return ParcelLookup(found=False)
    if isinstance(payload, dict):
        success, _ = (
            payload.get("isSuccess"),
            payload.get("message"),
        )
        if success is False:
            return ParcelLookup(found=False)
    booking = parse_parcel_booking(payload)
    found = bool(booking.provider_parcel_no or booking.tracking_code)
    return ParcelLookup(found=found, booking=booking if found else booking)


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        return None


def parse_tracking_events(payload: Any) -> list[TrackingEvent]:
    events: list[TrackingEvent] = []
    items = _as_list(payload)
    if not items and isinstance(payload, dict):
        maybe = payload.get("events") or payload.get("tracking") or payload.get("data")
        items = maybe if isinstance(maybe, list) else _as_list(maybe)
    for item in items:
        if not isinstance(item, dict):
            continue
        events.append(
            TrackingEvent(
                provider_status=_str(
                    item.get("event_name") or item.get("status") or item.get("eventName")
                ),
                provider_code=_str(
                    item.get("event_code") or item.get("eventCode") or item.get("status_code")
                ),
                occurred_at=_parse_dt(
                    item.get("change_status_date_utc")
                    or item.get("change_status_date")
                    or item.get("occurred_at")
                    or item.get("date")
                ),
                description=_str(
                    item.get("event_desc") or item.get("event_name") or item.get("description")
                ),
                location=_str(item.get("location") or item.get("location_name")),
                payload=redact_secrets(item) if isinstance(item, dict) else {},
            )
        )
    return events
