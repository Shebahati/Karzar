"""IMG-02B — Deterministic source-discovery worklists (read-only; no network/DB/storage)."""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = 1
TASK_ID = "IMG-02B"

AUTHORITATIVE_CHECKSUMS_DIGEST = (
    "4a2669e1da514b59198e37f3b761a179f0e626c174232043a63612db8581e48d"
)

EXPECTED_INVENTORY_FACTS = {
    "non_deleted_products": 5917,
    "products_with_image_rows": 1194,
    "products_without_image_rows": 4724,
    "valid_local_image_rows": 1193,
    "unique_local_assets": 614,
}

TARGET_BRAND_KEYS = ("dasqua", "insize", "san_ou")

BRAND_DISPLAY = {
    "dasqua": "Dasqua",
    "insize": "INSIZE",
    "san_ou": "SAN OU",
}

# Exact token → brand_key (English + Persian display fragments). No substring matching.
BRAND_TOKENS: dict[str, str] = {
    "dasqua": "dasqua",
    "داسکوا": "dasqua",
    "insize": "insize",
    "اینسایز": "insize",
    "san ou": "san_ou",
    "sanou": "san_ou",
    "سانو": "san_ou",
}

WORK_TYPES = (
    "manual_review_hold",
    "replace_required",
    "missing_image",
    "watermark_cleaner",
)

WORK_TYPE_PRECEDENCE = {name: idx for idx, name in enumerate(WORK_TYPES)}

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}

BUNDLE_SPECS = (
    {
        "batch_id": "IMG-02A-02-PILOT-001",
        "label": "pilot_001",
        "zip_name": "IMG-02A-02-pilot-001-human-review.zip",
        "expected_outer_sha256": (
            "02f8ebd66644073871d4109638625292f3c5c88c1ad60523bbcd409b8ea37b8d"
        ),
        "assets": 100,
        "assignments": 465,
        "replace_required": 41,
        "manual_review": 1,
    },
    {
        "batch_id": "IMG-02A-02-BATCH-002",
        "label": "batch_002",
        "zip_name": "IMG-02A-02-batch-002-human-review.zip",
        "expected_outer_sha256": (
            "3402f341ec6b0f5ca9e50a0abd069191bfc1ebb28656728bd3adafd7697d7bc5"
        ),
        "assets": 100,
        "assignments": 212,
        "replace_required": 17,
        "manual_review": 1,
    },
    {
        "batch_id": "IMG-02A-02-REMAINDER-ALL",
        "label": "remainder_all",
        "zip_name": "IMG-02A-02-REMAINDER-ALL-human-review.zip",
        "expected_outer_sha256": (
            "9e40733a7bd9eece40c2cb3b84732b7dae664ef87ec3c1d4b5ef2f09e2262b87"
        ),
        "assets": 414,
        "assignments": 516,
        "replace_required": 30,
        "manual_review": 0,
    },
)

CUMULATIVE_REVIEW = {
    "assets_reviewed": 614,
    "assignments_reviewed": 1193,
    "replace_required_assignments": 88,
    "manual_review_assignments": 2,
}

SOURCE_PATH_CONTRACTS = {
    "dasqua": {
        "brand_key": "dasqua",
        "brand_name": "Dasqua",
        "source_adapter_candidate": "dasqua_official",
        "source_class": "official_manufacturer",
        "allowed_hosts": ["www.dasquatools.com"],
        "matching_basis": ["exact normalized Dasqua item code"],
        "discovery_strategy": ["official sitemap and product pages"],
        "current_legacy_script": "scripts/import_dasqua_images_from_official.py",
        "legacy_execution_allowed": False,
        "legacy_note": "Mutation-capable legacy importer; must not be executed by IMG-02B-01.",
        "rights_status": "review_required",
        "apply_status": "not_started",
        "network_discovery_status": "not_started",
    },
    "insize": {
        "brand_key": "insize",
        "brand_name": "INSIZE",
        "source_adapter_candidate": "insize_tosag",
        "source_class": "authorized_distributor_candidate",
        "allowed_hosts": ["www.tosag.ch"],
        "matching_basis": ["exact SKU confirmed on product detail page"],
        "current_generic_adapter": "insize_tosag",
        "live_parser_status": "pending_validation",
        "legacy_execution_allowed": False,
        "absence_of_official_source_note": (
            "Absence of an official INSIZE source in this contract must not be "
            "interpreted as rights clearance."
        ),
        "rights_status": "review_required",
        "apply_status": "not_started",
        "network_discovery_status": "not_started",
    },
    "san_ou": {
        "brand_key": "san_ou",
        "brand_name": "SAN OU",
        "source_adapter_candidate": "sanou_official",
        "source_class": "official_manufacturer",
        "allowed_hosts": ["www.sanouchuck.com", "en.sanouchuck.com"],
        "matching_basis": ["exact official model / governed model mapping"],
        "current_legacy_script": "scripts/sanou_official_catalog_enrich.py",
        "legacy_execution_allowed": False,
        "legacy_note": (
            "Existing SAN OU script is a content-enrichment/API tool and not an "
            "approved image-discovery Adapter."
        ),
        "rights_status": "review_required",
        "apply_status": "not_started",
        "network_discovery_status": "not_started",
    },
}

WORKLIST_FIELDS = [
    "schema_version",
    "task_id",
    "work_item_id",
    "product_key",
    "product_id",
    "sku",
    "product_name",
    "brand_key",
    "brand_name",
    "category_name",
    "work_type",
    "work_reasons",
    "priority",
    "active",
    "available",
    "current_image_id",
    "current_asset_id",
    "source_assignment_id",
    "review_batch_id",
    "review_decision",
    "suitability_status",
    "has_third_party_watermark",
    "rights_status",
    "source_adapter_candidate",
    "source_class",
    "eligible_for_automatic_discovery",
    "status",
    "notes",
]


class WorklistError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def normalize_token(value: str) -> str:
    import re
    import unicodedata

    text = unicodedata.normalize("NFKC", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text


def normalize_brand(raw: str | None) -> str | None:
    """Return canonical brand_key for a target brand, or None if not a target brand."""
    if raw is None:
        return None
    mapped: set[str] = set()
    for part in str(raw).split("|"):
        token = normalize_token(part)
        if not token:
            continue
        if token in BRAND_TOKENS:
            mapped.add(BRAND_TOKENS[token])
    if not mapped:
        return None
    if len(mapped) > 1:
        raise WorklistError(
            "brand",
            f"ambiguous brand identity in {raw!r}: {sorted(mapped)}",
        )
    return next(iter(mapped))


def brand_display(brand_key: str) -> str:
    try:
        return BRAND_DISPLAY[brand_key]
    except KeyError as e:
        raise WorklistError("brand", f"unknown brand_key: {brand_key}") from e


def stable_work_item_id(parts: list[str]) -> str:
    import hashlib

    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def sha256_file(path: Any) -> str:
    import hashlib
    from pathlib import Path

    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def split_pipe_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [p.strip() for p in str(value).split("|") if p.strip()]
