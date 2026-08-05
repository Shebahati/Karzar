"""Typed deterministic source registry for IMG-02C."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import AUTHORIZATION_STATES, SOURCE_CLASS_ORDER, MultisourceError

REQUIRED_FIELDS = (
    "source_id",
    "source_class",
    "brand_keys",
    "allowed_page_hosts",
    "allowed_asset_hosts",
    "country",
    "authorization_status",
    "authorization_evidence",
    "robots_status",
    "discovery_method",
    "exact_sku_supported",
    "catalog_pdf_supported",
    "enabled",
    "rights_status",
    "notes",
)


@dataclass(frozen=True)
class SourceDeclaration:
    source_id: str
    source_class: str
    brand_keys: tuple[str, ...]
    allowed_page_hosts: tuple[str, ...]
    allowed_asset_hosts: tuple[str, ...]
    country: str
    authorization_status: str
    authorization_evidence: str
    robots_status: str
    discovery_method: str
    exact_sku_supported: bool
    catalog_pdf_supported: bool
    enabled: bool
    rights_status: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["brand_keys"] = list(self.brand_keys)
        d["allowed_page_hosts"] = list(self.allowed_page_hosts)
        d["allowed_asset_hosts"] = list(self.allowed_asset_hosts)
        return d


def _as_tuple(value: Any, *, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise MultisourceError("registry", f"{field_name} must be a non-empty list")
    out: list[str] = []
    for item in value:
        text = str(item).strip().casefold()
        if not text:
            raise MultisourceError("registry", f"empty entry in {field_name}")
        out.append(text)
    return tuple(out)


def parse_source(raw: dict[str, Any]) -> SourceDeclaration:
    missing = [k for k in REQUIRED_FIELDS if k not in raw]
    if missing:
        raise MultisourceError("registry", f"missing fields: {','.join(missing)}")
    source_class = str(raw["source_class"]).strip().upper()
    if source_class not in SOURCE_CLASS_ORDER:
        raise MultisourceError("registry", f"invalid source_class={source_class}")
    auth = str(raw["authorization_status"]).strip().casefold()
    if auth not in AUTHORIZATION_STATES:
        raise MultisourceError("registry", f"invalid authorization_status={auth}")
    enabled = bool(raw["enabled"])
    if auth == "unknown" and enabled:
        raise MultisourceError(
            "registry",
            f"source {raw.get('source_id')!r} has unknown authorization and must stay disabled",
        )
    rights = str(raw["rights_status"]).strip().casefold()
    if rights != "review_required":
        raise MultisourceError("registry", "rights_status must be review_required")
    return SourceDeclaration(
        source_id=str(raw["source_id"]).strip(),
        source_class=source_class,
        brand_keys=_as_tuple(raw["brand_keys"], field_name="brand_keys"),
        allowed_page_hosts=_as_tuple(raw["allowed_page_hosts"], field_name="allowed_page_hosts"),
        allowed_asset_hosts=_as_tuple(
            raw["allowed_asset_hosts"], field_name="allowed_asset_hosts"
        ),
        country=str(raw["country"]).strip(),
        authorization_status=auth,
        authorization_evidence=str(raw["authorization_evidence"] or "").strip(),
        robots_status=str(raw["robots_status"]).strip().casefold(),
        discovery_method=str(raw["discovery_method"]).strip(),
        exact_sku_supported=bool(raw["exact_sku_supported"]),
        catalog_pdf_supported=bool(raw["catalog_pdf_supported"]),
        enabled=enabled,
        rights_status=rights,
        notes=str(raw.get("notes") or "").strip(),
    )


def source_priority_key(source: SourceDeclaration) -> tuple[int, str]:
    return (SOURCE_CLASS_ORDER.index(source.source_class), source.source_id)


def sort_sources(sources: Iterable[SourceDeclaration]) -> list[SourceDeclaration]:
    return sorted(sources, key=source_priority_key)


def load_registry(path: Path) -> list[SourceDeclaration]:
    if not path.is_file():
        raise MultisourceError("registry", f"registry file missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        rows = payload.get("sources")
    else:
        rows = payload
    if not isinstance(rows, list) or not rows:
        raise MultisourceError("registry", "registry must contain a non-empty sources list")
    sources = [parse_source(row) for row in rows]
    ids = [s.source_id for s in sources]
    if len(ids) != len(set(ids)):
        raise MultisourceError("registry", "duplicate source_id in registry")
    return sort_sources(sources)


def builtin_known_host_registry() -> list[SourceDeclaration]:
    """Known hosts only (Dasqua / TOSAG / SAN OU). Enabled flags start false until calibration."""
    raw = [
        {
            "source_id": "dasqua_official",
            "source_class": "S1",
            "brand_keys": ["dasqua"],
            "allowed_page_hosts": ["www.dasquatools.com", "dasquatools.com"],
            "allowed_asset_hosts": [
                "www.dasquatools.com",
                "dasquatools.com",
                "cdn.shopify.com",
            ],
            "country": "CN",
            "authorization_status": "official",
            "authorization_evidence": "IMG-02B official manufacturer adapter path",
            "robots_status": "unknown_pending_calibration",
            "discovery_method": "official_product_page",
            "exact_sku_supported": True,
            "catalog_pdf_supported": False,
            "enabled": False,
            "rights_status": "review_required",
            "notes": "IMG-02B calibration_failed; require fresh ≤20 calibration before enable",
        },
        {
            "source_id": "insize_tosag",
            "source_class": "S3",
            "brand_keys": ["insize"],
            "allowed_page_hosts": ["www.tosag.ch", "tosag.ch"],
            "allowed_asset_hosts": ["www.tosag.ch", "tosag.ch"],
            "country": "CH",
            "authorization_status": "authorized_candidate",
            "authorization_evidence": "IMG-01/IMG-02B TOSAG authorized-distributor candidate",
            "robots_status": "unknown_pending_calibration",
            "discovery_method": "authorized_distributor_search",
            "exact_sku_supported": True,
            "catalog_pdf_supported": False,
            "enabled": False,
            "rights_status": "review_required",
            "notes": "Do not redownload IMG-02B-R2 stable seed assets unnecessarily",
        },
        {
            "source_id": "sanou_official",
            "source_class": "S1",
            "brand_keys": ["san_ou"],
            "allowed_page_hosts": [
                "www.sanouchuck.com",
                "sanouchuck.com",
                "en.sanouchuck.com",
            ],
            "allowed_asset_hosts": [
                "www.sanouchuck.com",
                "sanouchuck.com",
                "en.sanouchuck.com",
            ],
            "country": "CN",
            "authorization_status": "official",
            "authorization_evidence": "IMG-02B official manufacturer adapter path",
            "robots_status": "unknown_pending_calibration",
            "discovery_method": "official_product_page",
            "exact_sku_supported": True,
            "catalog_pdf_supported": False,
            "enabled": False,
            "rights_status": "review_required",
            "notes": "IMG-02B site-shape parser_drift; require fresh ≤20 calibration before enable",
        },
        {
            "source_id": "example_unknown_disabled",
            "source_class": "S5",
            "brand_keys": ["insize"],
            "allowed_page_hosts": ["example.invalid"],
            "allowed_asset_hosts": ["cdn.example.invalid"],
            "country": "IR",
            "authorization_status": "unknown",
            "authorization_evidence": "",
            "robots_status": "not_checked",
            "discovery_method": "none",
            "exact_sku_supported": False,
            "catalog_pdf_supported": False,
            "enabled": False,
            "rights_status": "review_required",
            "notes": "Sentinel: unknown authorization must remain disabled",
        },
    ]
    return sort_sources(parse_source(row) for row in raw)


def write_registry_snapshot(sources: list[SourceDeclaration], path: Path) -> None:
    payload = {
        "schema_version": 1,
        "task_id": "IMG-02C",
        "node_id": "IMG-02C-01-MULTISOURCE-BATCH-001",
        "sources": [s.to_dict() for s in sort_sources(sources)],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def prefer_higher_priority(
    existing_class: str,
    challenger_class: str,
) -> bool:
    """Return True if challenger may displace existing evidence by source class only.

    Lower-priority sources must not displace valid higher-priority evidence.
    """
    if existing_class not in SOURCE_CLASS_ORDER or challenger_class not in SOURCE_CLASS_ORDER:
        raise MultisourceError("registry", "invalid class for priority comparison")
    return SOURCE_CLASS_ORDER.index(challenger_class) < SOURCE_CLASS_ORDER.index(
        existing_class
    )
