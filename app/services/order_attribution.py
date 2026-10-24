"""First-party order acquisition attribution resolver and validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator

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
    "google:google_organic": "گوگل (ارگانیک)",
    "google:google_paid": "گوگل (تبلیغات)",
    "google:google_unspecified": "گوگل",
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


def source_label_fa(source: str | None, source_subtype: str | None = None) -> str:
    src = (source or "").strip() or "unknown"
    if src == "google" and source_subtype:
        return SOURCE_LABELS_FA.get(f"google:{source_subtype}", SOURCE_LABELS_FA["google"])
    return SOURCE_LABELS_FA.get(src, SOURCE_LABELS_FA["unknown"])


def report_row_key(source: str | None, source_subtype: str | None = None) -> str:
    src = (source or "unknown").strip() or "unknown"
    if src == "google" and source_subtype:
        return f"google:{source_subtype}"
    return src


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



RECOGNIZED_UTM_SOURCES: dict[str, str] = {
    "torob": "torob", "trob": "torob", "emalls": "emalls", "emall": "emalls",
    "instagram": "instagram", "ig": "instagram", "google": "google",
    "google_ads": "google", "adwords": "google",
}

MAX_FUTURE_SKEW = timedelta(minutes=5)


def _host_matches_domain(host: str, domain: str) -> bool:
    host = host.lower().strip(".")
    domain = domain.lower()
    return host == domain or host.endswith(f".{domain}")


def _is_google_host(host: str) -> bool:
    if _host_matches_domain(host, "google.com"):
        return True
    labels = host.lower().split(".")
    return len(labels) >= 2 and labels[-2] == "google"


def _source_from_recognized_utm(utm_s: str | None, utm_m: str | None):
    if not utm_s:
        return None
    canonical = RECOGNIZED_UTM_SOURCES.get(utm_s)
    if canonical is None:
        return None
    if canonical == "google":
        return canonical, _google_subtype(utm_m, utm_s)
    return canonical, None


def _source_from_trusted_referrer(host: str | None):
    if not host:
        return None
    if _host_matches_domain(host, "torob.com"):
        return "torob", None
    if _host_matches_domain(host, "emalls.ir"):
        return "emalls", None
    if _host_matches_domain(host, "instagram.com") or _host_matches_domain(host, "l.instagram.com"):
        return "instagram", None
    if _is_google_host(host):
        return "google", "google_unspecified"
    return None

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
    has_campaign = any([campaign.utm_source, campaign.utm_medium, campaign.utm_campaign])

    from_utm = _source_from_recognized_utm(utm_s, utm_m)
    if from_utm is not None:
        source, subtype = from_utm
        return AcquisitionTouch(
            source=source,
            source_subtype=subtype,
            method="utm",
            landing_path=path,
            campaign=campaign if has_campaign else None,
            captured_at=at,
        )

    from_ref = _source_from_trusted_referrer(host)
    if from_ref is not None:
        source, subtype = from_ref
        return AcquisitionTouch(
            source=source,
            source_subtype=subtype,
            method="referrer",
            landing_path=path,
            campaign=None,
            captured_at=at,
        )

    if utm_s:
        return AcquisitionTouch(
            source="other",
            method="utm",
            landing_path=path,
            campaign=campaign if has_campaign else None,
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


def _touch_usable(touch: AcquisitionTouch | None, now: datetime) -> bool:
    if touch is None:
        return False
    if touch.captured_at > now + MAX_FUTURE_SKEW:
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

    first = payload.first_touch if _touch_usable(payload.first_touch, now) else None
    last_nd = (
        payload.last_non_direct_touch
        if _touch_usable(payload.last_non_direct_touch, now)
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
