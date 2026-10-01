"""Phase 2B — read-only canonical naming preview (no Product writes)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import product as crud_product
from app.db.models.product_type import ProductType
from app.domain.product_naming import (
    NamingGovernanceContext,
    NamingResult,
    brand_display_is_governed,
    build_product_name_v1,
    resolve_naming_profile_v1,
)
from app.services import knowledge_fact_service

_BRAND_REGISTRY_PATH = (
    Path(__file__).resolve().parents[2]
    / "audit"
    / "product-naming-v1"
    / "BRAND_DISPLAY_REGISTRY.csv"
)

_PUBLIC_FACT_STATUSES = frozenset({"published"})


def _load_brand_registry() -> dict[str, dict[str, str]]:
    """Map brand_id / brand_raw_name → registry row."""
    out: dict[str, dict[str, str]] = {}
    if not _BRAND_REGISTRY_PATH.exists():
        return out
    with _BRAND_REGISTRY_PATH.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            bid = (row.get("brand_id") or "").strip()
            raw = (row.get("brand_raw_name") or "").strip()
            if bid:
                out[bid] = row
            if raw:
                out[raw.upper()] = row
                # Also index Latin side before |
                latin = raw.split("|", 1)[0].strip().upper()
                if latin:
                    out[latin] = row
    return out


_BRAND_REGISTRY = _load_brand_registry()


def _registry_for_brand(brand_id: int | None, brand_name: str | None) -> dict[str, str] | None:
    if brand_id is not None and str(brand_id) in _BRAND_REGISTRY:
        return _BRAND_REGISTRY[str(brand_id)]
    if brand_name:
        key = brand_name.strip().upper()
        if key in _BRAND_REGISTRY:
            return _BRAND_REGISTRY[key]
        latin = brand_name.split("|", 1)[0].strip().upper()
        if latin in _BRAND_REGISTRY:
            return _BRAND_REGISTRY[latin]
    return None


async def _governed_facts_for_product(
    db: AsyncSession, product_id: int
) -> tuple[dict[str, Any], bool]:
    """Return (facts_dict, all_used_facts_governed_flag_for_preview).

    Only Facts with public/approved statuses are treated as governed evidence.
    Heuristic/title-parsed values are never injected here.
    """
    try:
        facts = await knowledge_fact_service.list_facts_for_product(db, product_id)
    except Exception:
        return {}, False

    out: dict[str, Any] = {}
    any_fact = False
    all_gov = True
    for fact in facts or []:
        status = str(getattr(fact, "status", "") or "").lower()
        # Prefer property key via relationship when present.
        key = None
        prop = getattr(fact, "property_definition", None) or getattr(fact, "definition", None)
        if prop is not None:
            key = getattr(prop, "key", None)
        if not key:
            def_id = getattr(fact, "definition_id", None) or getattr(
                fact, "property_definition_id", None
            )
            if isinstance(def_id, str) and def_id.startswith("def."):
                key = def_id[4:]
        if not key:
            continue
        value = getattr(fact, "value", None)
        if isinstance(value, dict):
            # Common KB shapes: {"min":0,"max":150} or {"value": ...}
            if "min" in value and "max" in value:
                out["range_min_mm"] = value["min"]
                out["range_max_mm"] = value["max"]
                out["measurement_range"] = (value["min"], value["max"])
            elif "value" in value:
                out[key] = value["value"]
            else:
                out[key] = value
        else:
            out[key] = value
        any_fact = True
        if status not in _PUBLIC_FACT_STATUSES:
            all_gov = False
    if not any_fact:
        return {}, False
    return out, all_gov


async def build_persisted_naming_preview(
    db: AsyncSession, product_id: int
) -> dict[str, Any] | None:
    """Compose read-only preview from persisted Product identity only.

    Does not parse title for OEM. Null manufacturer_code → HOLD.
    Returns None if product missing.
    """
    product = await crud_product.get_product_by_id(db, product_id)
    if product is None:
        return None

    # Snapshot identity for mutation-boundary tests (caller may compare).
    before = {
        "name": product.name,
        "sku": product.sku,
        "slug": product.slug,
        "manufacturer_code": product.manufacturer_code,
    }

    brand = product.brand
    brand_name = brand.name if brand else None
    registry = _registry_for_brand(product.brand_id, brand_name)

    pt: ProductType | None = product.product_type
    if pt is None and product.product_type_id is not None:
        # Relationship may be unloaded — fetch lightly via assignment path later
        from sqlalchemy import select

        pt = (
            await db.execute(
                select(ProductType).where(ProductType.id == product.product_type_id)
            )
        ).scalar_one_or_none()

    pt_code = pt.code if pt else None
    pt_fa = pt.name_fa if pt else None
    profile_code, profile_resolution = resolve_naming_profile_v1(pt_code)

    facts, facts_gov = await _governed_facts_for_product(db, product_id)

    oem = (product.manufacturer_code or "").strip() or None
    oem_gov = bool(oem)  # Phase 2A invariant: non-null column ⇒ verified canonical
    pt_gov = product.product_type_id is not None and pt is not None
    brand_gov = brand_display_is_governed(registry)
    profile_gov = profile_resolution == "PROFILE_GOVERNED"

    governance = NamingGovernanceContext(
        product_type_governed=pt_gov,
        manufacturer_code_governed=oem_gov,
        brand_display_governed=brand_gov,
        naming_profile_governed=profile_gov,
        variant_facts_governed=facts_gov,
        identity_qualifiers_governed=False,
    )

    result: NamingResult = build_product_name_v1(
        product_type=pt_fa or pt_code,
        product_type_fa=pt_fa,
        brand=brand_name,
        brand_raw=brand_name,
        manufacturer_code=oem,
        facts=facts,
        naming_profile=profile_code,
        brand_registry_row=registry,
        current_name=product.name,
        governance=governance,
        profile_resolution=profile_resolution,
    )

    # Refresh product to ensure no accidental dirty state (read-only path).
    await db.refresh(product)
    after = {
        "name": product.name,
        "sku": product.sku,
        "slug": product.slug,
        "manufacturer_code": product.manufacturer_code,
    }

    return {
        "product_id": product.id,
        "preview_source": "persisted_canonical",
        "current_name": product.name,
        "proposed_name": result.name,
        "state": result.state,
        "confidence": result.confidence,
        "naming_standard_version": result.naming_standard_version,
        "profile": result.profile,
        "profile_resolution": result.profile_resolution or profile_resolution,
        "warnings": list(result.warnings),
        "reason_codes": list(result.reason_codes),
        "used_fields": list(result.used_fields),
        "omitted_fields": list(result.omitted_fields),
        "governance": result.governance or governance.as_dict(),
        "product_type": (
            {
                "id": pt.id,
                "code": pt.code,
                "name_fa": pt.name_fa,
                "name_en": pt.name_en,
                "status": pt.status,
            }
            if pt
            else None
        ),
        "brand": (
            {"id": brand.id, "name": brand.name, "display_governed": brand_gov}
            if brand
            else None
        ),
        "manufacturer_code": oem,
        "manufacturer_code_status": "verified" if oem else "unset",
        "mutation_check": {"before": before, "after": after, "unchanged": before == after},
    }
