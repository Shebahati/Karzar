"""First-party order acquisition attribution resolver and validation."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

ATTRIBUTION_TTL_DAYS = 30
MAX_LANDING_PATH = 256
MAX_CAMPAIGN_FIELD = 128

AcquisitionSource = Literal[
    "torob",
    "emalls",
    "instagram",
    "google",
    "direct",
    "other",
    "unknown",
]

GoogleSubtype = Literal["google_organic", "google_paid", "google_unspecified"]

ALLOWED_SOURCES: frozenset[str] = frozenset(
    {"torob", "emalls", "instagram", "google", "direct", "other", "unknown"}
)

SOURCE_LABELS_FA: dict[str, str] = {
    "torob": "ترب",
    "emalls": "ایمالز",
    "instagram": "اینستاگرام",
    "google": "گوگل",
    "direct": "ورود مستقیم",
    "other": "سایر",
    "unknown": "نامشخص",
}


class AcquisitionCampaign(BaseModel):
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None

    @field_validator("utm_source", "utm_medium", "utm_campaign", mode="before")
    @classmethod
    def _trim_campaign(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return text[:MAX_CAMPAIGN_FIELD]


class AcquisitionTouch(BaseModel):
    source: AcquisitionSource
    source_subtype: str | None = None
    method: str = "unknown"
    landing_path: str | None = None
    campaign: AcquisitionCampaign | None = None
    captured_at: datetime


class AcquisitionClientState(BaseModel):
    first_touch: AcquisitionTouch | None = None
    last_non_direct_touch: AcquisitionTouch | None = None


class AcquisitionCheckoutSnapshot(BaseModel):
    """Untrusted client snapshot; re-validated server-side."""

    first_touch: AcquisitionTouch | None = None
    last_non_direct_touch: AcquisitionTouch | None = None


class OrderAcquisitionSnapshot(BaseModel):
    source: AcquisitionSource = "unknown"
    first_touch_source: AcquisitionSource = "unknown"
    last_non_direct_source: AcquisitionSource | None = None
    source_subtype: str | None = None
    method: str = "unknown"
    landing_path: str | None = None
    campaign: dict[str, Any] | None = None
    captured_at: datetime | None = None


def source_label_fa(source: str | None) -> str:
    return SOURCE_LABELS_FA.get((source or "").strip(), SOURCE_LABELS_FA["unknown"])


def _host_from_referrer(referrer: str | None) -> str | None:
    if not referrer or not referrer.strip():
        return None
    try:
        host = (urlparse(referrer.strip()).hostname or "").lower()
    except ValueError:
        return None
    return host or None


def _normalize_utm(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip().lower()
    return text or None


def _google_subtype(utm_medium: str | None, utm_source: str | None) -> GoogleSubtype:
    medium = _normalize_utm(utm_medium) or ""
    source = _normalize_utm(utm_source) or ""
    if medium in {"cpc", "ppc", "paid", "paidsearch"} or "gclid" in medium:
        return "google_paid"
    if source in {"google", "google_ads", "adwords"} and medium in {"cpc", "ppc", "paid"}:
        return "google_paid"
    if medium in {"organic", "search"}:
        return "google_organic"
    if not medium and source in {"google"}:
        return "google_unspecified"
    return "google_unspecified"


def classify_visit(
    *,
    landing_path: str | None,
    referrer: str | None,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    captured_at: datetime | None = None,
) -> AcquisitionTouch:
    at = captured_at or datetime.now(UTC)
    path = (landing_path or "/").strip()
    if len(path) > MAX_LANDING_PATH:
        path = path[:MAX_LANDING_PATH]
    campaign = AcquisitionCampaign(
        utm_source=utm_source,
        utm_medium=utm_medium,
        utm_campaign=utm_campaign,
    )
    utm_s = _normalize_utm(utm_source)
    utm_m = _normalize_utm(utm_medium)
    host = _host_from_referrer(referrer)

    if utm_s in {"torob", "trob"} or (host and "torob" in host):
        return AcquisitionTouch(
            source="torob",
            method="utm" if utm_s else "referrer",
            landing_path=path,
            campaign=campaign if any([campaign.utm_source, campaign.utm_medium, campaign.utm_campaign]) else None,
            captured_at=at,
        )
    if utm_s in {"emalls", "emall"} or (host and "emalls" in host):
        return AcquisitionTouch(
            source="emalls",
            method="utm" if utm_s else "referrer",
            landing_path=path,
            campaign=campaign if any([campaign.utm_source, campaign.utm_medium, campaign.utm_campaign]) else None,
            captured_at=at,
        )
    if utm_s in {"instagram", "ig"} or (host and ("instagram.com" in host or "l.instagram.com" in host)):
        return AcquisitionTouch(
            source="instagram",
            method="utm" if utm_s else "referrer",
            landing_path=path,
            campaign=campaign if any([campaign.utm_source, campaign.utm_medium, campaign.utm_campaign]) else None,
            captured_at=at,
        )
    if utm_s in {"google", "google_ads", "adwords"} or (host and "google." in host):
        subtype = _google_subtype(utm_m, utm_s)
        return AcquisitionTouch(
            source="google",
            source_subtype=subtype,
            method="utm" if utm_s else "referrer",
            landing_path=path,
            campaign=campaign if any([campaign.utm_source, campaign.utm_medium, campaign.utm_campaign]) else None,
            captured_at=at,
        )
    if utm_s:
        return AcquisitionTouch(
            source="other",
            method="utm",
            landing_path=path,
            campaign=campaign,
            captured_at=at,
        )
    if host:
        return AcquisitionTouch(
            source="other",
            method="referrer",
            landing_path=path,
            campaign=None,
            captured_at=at,
        )
    return AcquisitionTouch(
        source="direct",
        method="direct",
        landing_path=path,
        campaign=None,
        captured_at=at,
    )


def merge_client_state(
    existing: AcquisitionClientState | None,
    visit: AcquisitionTouch,
) -> AcquisitionClientState:
    state = existing or AcquisitionClientState()
    if state.first_touch is None:
        state.first_touch = visit
    if visit.source != "direct":
        state.last_non_direct_touch = visit
    return state


def _touch_fresh(touch: AcquisitionTouch | None, now: datetime) -> bool:
    if touch is None:
        return False
    return touch.captured_at >= now - timedelta(days=ATTRIBUTION_TTL_DAYS)


def resolve_order_snapshot(
    payload: AcquisitionCheckoutSnapshot | None,
    *,
    now: datetime | None = None,
) -> OrderAcquisitionSnapshot:
    now = now or datetime.now(UTC)
    if payload is None:
        return OrderAcquisitionSnapshot()

    first = payload.first_touch if _touch_fresh(payload.first_touch, now) else None
    last_nd = (
        payload.last_non_direct_touch
        if _touch_fresh(payload.last_non_direct_touch, now)
        else None
    )

    primary = last_nd or first
    if primary is None:
        return OrderAcquisitionSnapshot()

    first_source = (first.source if first else primary.source) or "unknown"
    last_non_direct = last_nd.source if last_nd else None

    campaign_dict: dict[str, Any] | None = None
    if primary.campaign is not None:
        campaign_dict = primary.campaign.model_dump(exclude_none=True)

    return OrderAcquisitionSnapshot(
        source=primary.source,
        first_touch_source=first_source,
        last_non_direct_source=last_non_direct,
        source_subtype=primary.source_subtype,
        method=primary.method,
        landing_path=primary.landing_path,
        campaign=campaign_dict,
        captured_at=primary.captured_at,
    )


def sanitize_checkout_snapshot(raw: AcquisitionCheckoutSnapshot | None) -> AcquisitionCheckoutSnapshot | None:
    if raw is None:
        return None
    return raw
