"""Matching contract for multisource candidates."""

from __future__ import annotations

from urllib.parse import urlparse

from . import AUTOMATIC_MATCH_BASES, RETAILER_SOURCE_CLASSES, MultisourceError
from .registry import SourceDeclaration


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").strip().casefold()


def host_allowed(url: str, allowed_hosts: tuple[str, ...]) -> bool:
    host = host_of(url)
    if not host:
        return False
    allowed = {h.casefold() for h in allowed_hosts}
    if host in allowed:
        return True
    return any(host.endswith("." + h) for h in allowed)


def sku_token_present(haystack: str, sku: str) -> bool:
    text = (haystack or "").casefold()
    token = (sku or "").strip().casefold()
    if not token or not text:
        return False
    # Fail closed against footer/sidebar-only heuristics: require token as whole fragment.
    for sep in (" ", "\n", "\t", ",", ";", "|", "/", ">", "<", "(", ")", "[", "]", '"', "'"):
        text = text.replace(sep, " ")
    parts = [p for p in text.split(" ") if p]
    return token in parts or token.replace("-", "") in {p.replace("-", "") for p in parts}


def classify_match(
    *,
    source: SourceDeclaration,
    product_id: str,
    sku: str,
    brand_key: str,
    page_url: str,
    asset_url: str,
    page_text: str,
    match_basis: str,
    brand_confirmed: bool,
    subject_exact: bool,
    redirect_approved: bool,
) -> dict[str, str]:
    if not product_id or not sku:
        raise MultisourceError("matching", "product_id and sku are required")
    if (brand_key or "").casefold() not in {b.casefold() for b in source.brand_keys}:
        return _reject("brand_mismatch", "brand_key not declared for source")
    if not brand_confirmed:
        return _reject("brand_not_confirmed", "manufacturer/brand evidence missing")
    if not redirect_approved:
        return _reject("unapproved_redirect", "redirect outside approved hosts")
    if not host_allowed(page_url, source.allowed_page_hosts):
        return _reject("unapproved_page_host", host_of(page_url))
    if not host_allowed(asset_url, source.allowed_asset_hosts):
        return _reject("unapproved_asset_host", host_of(asset_url))
    if not subject_exact:
        return _reject("subject_not_exact", "image not tied to exact product subject")
    if not sku_token_present(page_text, sku):
        return _reject("exact_sku_or_model_not_confirmed", "SKU/model token absent from page body")

    basis = (match_basis or "").strip()
    if source.source_class in RETAILER_SOURCE_CLASSES:
        return {
            "discovery_status": "retailer_review",
            "eligible_for_automatic_acceptance": "false",
            "match_basis": basis or "retailer_candidate",
            "reason_code": "retailer_review_default",
            "reason_detail": "S4/S5 default to retailer_review until governed promotion",
        }

    if basis not in AUTOMATIC_MATCH_BASES:
        return _reject("match_basis_not_allowed", basis or "missing")

    if source.authorization_status in {"specialist_retailer", "iranian_supplier"}:
        return {
            "discovery_status": "retailer_review",
            "eligible_for_automatic_acceptance": "false",
            "match_basis": basis,
            "reason_code": "retailer_auth_status",
            "reason_detail": source.authorization_status,
        }

    return {
        "discovery_status": "candidate_ready",
        "eligible_for_automatic_acceptance": "true",
        "match_basis": basis,
        "reason_code": "",
        "reason_detail": "",
    }


def _reject(code: str, detail: str) -> dict[str, str]:
    return {
        "discovery_status": "rejected",
        "eligible_for_automatic_acceptance": "false",
        "match_basis": "",
        "reason_code": code,
        "reason_detail": detail,
    }


REJECT_PATTERNS = (
    "brand_only",
    "name_similarity_only",
    "generic_category",
    "marketplace_thumbnail",
    "navigation_or_recommendation",
    "footer_or_sidebar_only",
    "multi_product_collage_unmapped",
    "unapproved_third_party_redirect",
)


def quarantine_reason(code: str) -> bool:
    return code in REJECT_PATTERNS or code.startswith("unapproved_")
