"""Phase 2D — canonical name candidate dry-run (pure, deterministic).

Uses shared ``build_product_name_v1`` from ``product_naming``; never parses
current Product.name for identity. Classification is mutually exclusive.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.domain.product_naming import (
    NAMING_PROFILES,
    NAMING_STANDARD_VERSION,
    PROFILE_GOVERNED,
    PROFILE_MISSING,
    NamingGovernanceContext,
    NamingProfile,
    NamingResult,
    brand_display_for_title,
    brand_display_is_governed,
    build_product_name_v1,
    compare_product_name_v1,
    lint_product_name_v1,
    normalize_persian_text,
    resolve_naming_profile_v1,
)

PHASE2C_FROZEN_SHA256 = (
    "43620d24842b946652f8e2a0256aa75e45fbdf1b591b0374dcb84dea21417b03"
)
PHASE2C_FROZEN_ROWS = 1350

# Owner-frozen manufacturer identity cohort brands (Phase 2C charter).
PHASE2D_COHORT_BRAND_IDS: frozenset[int] = frozenset({3, 4, 5})  # INSIZE, DASQUA, TERMA

PUBLIC_FACT_STATUSES = frozenset({"published"})

TERMINAL_CLASSIFICATIONS: tuple[str, ...] = (
    "READY_NO_CHANGE",
    "READY_RENAME",
    "HOLD_MISSING_PRODUCT_TYPE",
    "HOLD_UNGOVERNED_PRODUCT_TYPE",
    "HOLD_PRODUCT_TYPE_DISPLAY",
    "HOLD_PRODUCT_TYPE_NAMING_POLICY",
    "HOLD_PRODUCT_TYPE_TITLE_LABEL_UNAPPROVED",
    "HOLD_BRAND_DISPLAY_UNGOVERNED",
    "HOLD_VARIANT_POLICY_UNDEFINED",
    "HOLD_MISSING_VARIANT_FACT",
    "HOLD_AMBIGUOUS_VARIANT_FACT",
    "HOLD_IDENTITY_DRIFT",
    "HOLD_NAME_COLLISION",
    "HOLD_STRUCTURAL_CONFLICT",
    "HOLD_POLICY_REVIEW_BLOCKED",
    "HOLD_OTHER",
)

_BROAD_PT_LABELS = frozenset(
    {
        "ابزار اندازه‌گیری",
        "ابزار اندازه گیری",
        "محصول",
        "متفرقه",
        "سایر",
        "ابزار",
    }
)
_LEGACY_ACCURACY_KEYS = frozenset({"accuracy", "دقت"})

AUTHORITATIVE_CANONICAL_POLICY_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "architecture"
    / "specs"
    / "product-naming-v1"
    / "PRODUCT_TYPE_CANONICAL_NAMING_POLICY.csv"
)

CANONICAL_CANDIDATE_FIELDNAMES: tuple[str, ...] = (
    "product_id",
    "sku",
    "proposed_name",
    "manufacturer_code",
    "product_type_code",
    "canonical_title_fa",
    "variant_policy_status",
    "variant_property_code",
    "variant_formatted_value",
)


@dataclass(frozen=True)
class CanonicalProductTypePolicy:
    product_type_code: str
    canonical_title_fa: str
    title_label_status: str
    title_hold_reason: str
    naming_profile_code: str
    variant_policy: str
    primary_variant_property: str
    formatter: str
    policy_basis: str


def authoritative_policy_path() -> Path:
    return AUTHORITATIVE_CANONICAL_POLICY_PATH


def load_authoritative_canonical_policy(
    path: Path | None = None,
) -> dict[str, CanonicalProductTypePolicy]:
    src = path or AUTHORITATIVE_CANONICAL_POLICY_PATH
    out: dict[str, CanonicalProductTypePolicy] = {}
    if not src.is_file():
        return out
    with src.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            code = (row.get("product_type_code") or "").strip()
            if not code:
                continue
            out[code] = CanonicalProductTypePolicy(
                product_type_code=code,
                canonical_title_fa=(row.get("canonical_title_fa") or "").strip(),
                title_label_status=(row.get("title_label_status") or "HOLD").strip().upper(),
                title_hold_reason=(row.get("title_hold_reason") or "").strip(),
                naming_profile_code=(row.get("naming_profile_code") or "generic.v1").strip(),
                variant_policy=(row.get("variant_policy") or "HOLD_VARIANT_POLICY_UNDEFINED").strip(),
                primary_variant_property=(row.get("primary_variant_property") or "").strip(),
                formatter=(row.get("formatter") or "").strip(),
                policy_basis=(row.get("policy_basis") or "").strip(),
            )
    return out


CANONICAL_POLICY: dict[str, CanonicalProductTypePolicy] = load_authoritative_canonical_policy()


def _property_key_group(property_code: str) -> tuple[str, ...]:
    if property_code == "measurement_range":
        return ("measurement_range", "range", "range_min_mm")
    if property_code == "nominal_size":
        return ("nominal_size",)
    if property_code:
        return (property_code,)
    return ()


def _profile_for_canonical_policy(pol: CanonicalProductTypePolicy) -> NamingProfile:
    base = NAMING_PROFILES.get(pol.naming_profile_code, NAMING_PROFILES["generic.v1"])
    keys = _property_key_group(pol.primary_variant_property)
    variant_required = pol.variant_policy == "VARIANT_REQUIRED"
    max_attrs = 1 if keys and pol.variant_policy == "VARIANT_REQUIRED" else 0
    return NamingProfile(
        code=base.code,
        manufacturer_code_required=base.manufacturer_code_required,
        brand_required=base.brand_required,
        product_type_required=base.product_type_required,
        primary_variant_fact_keys=keys if keys else base.primary_variant_fact_keys,
        max_variant_attributes=max_attrs if keys else 0,
        brand_policy=base.brand_policy,
        allow_identity_qualifiers=base.allow_identity_qualifiers,
        variant_required=variant_required,
    )


def resolve_naming_profile_phase2d(
    product_type_code: str | None,
) -> tuple[str, str, NamingProfile, CanonicalProductTypePolicy | None]:
    """Resolve naming profile from authoritative canonical policy registry only."""
    code = (product_type_code or "").strip()
    pol = CANONICAL_POLICY.get(code)
    if pol is None:
        base_code, resolution = resolve_naming_profile_v1(product_type_code)
        return base_code, resolution, NAMING_PROFILES.get(base_code, NAMING_PROFILES["generic.v1"]), None
    profile = _profile_for_canonical_policy(pol)
    if pol.naming_profile_code == "generic.v1":
        return pol.naming_profile_code, PROFILE_MISSING, profile, pol
    return pol.naming_profile_code, PROFILE_GOVERNED, profile, pol

_FORBIDDEN_WRITE_FLAGS = frozenset(
    {
        "--apply",
        "--rename",
        "--commit",
        "--force",
        "--write-db",
    }
)


@dataclass(frozen=True)
class VariantFactTrace:
    property_code: str | None
    raw_value: str | None
    formatted_value: str | None
    fact_id: int | None
    published: bool
    policy_status: str


@dataclass
class Phase2DProductInput:
    product_id: int
    current_name: str
    sku: str
    brand_id: int | None
    brand_name: str | None
    manufacturer_code: str
    product_type_id: int | None
    product_type_code: str | None
    product_type_name_fa: str | None
    product_type_status: str | None
    product_type_has_active_definition: bool
    meta_title: str | None
    is_active: bool
    is_available: bool
    priced: bool
    has_image: bool
    storefront_visible: bool
    sellable: bool
    frozen_sku: str | None = None
    frozen_brand_id: int | None = None
    frozen_manufacturer_code: str | None = None
    kb_facts: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Phase2DAuditRow:
    product_id: int
    sku: str
    brand_id: int | None
    brand_name: str
    brand_display: str
    manufacturer_code: str
    product_type_id: int | None
    product_type_code: str
    product_type_name_fa: str
    canonical_title_fa: str
    canonical_title_status: str
    product_type_governed: bool
    variant_policy: str
    variant_policy_basis: str
    variant_policy_status: str
    policy_review_status: str
    variant_property_code: str
    variant_raw_value: str
    variant_formatted_value: str
    variant_fact_id: str
    variant_fact_published: str
    current_name: str
    proposed_name: str
    comparison_normalized_current: str
    comparison_normalized_proposed: str
    terminal_classification: str
    classification_reason: str
    name_quality_flags: str
    proposed_collision: str
    collision_product_ids: str
    meta_title_present: str
    seo_title_impact: str
    is_active: str
    is_available: str
    priced: str
    has_image: str
    storefront_visible: str
    sellable: str


def reject_forbidden_cli_args(argv: Sequence[str]) -> None:
    for arg in argv:
        base = arg.split("=", 1)[0]
        if base in _FORBIDDEN_WRITE_FLAGS:
            raise SystemExit(2)


def brand_display_governed_phase2d(brand_id: int | None, registry_row: Mapping[str, Any] | None) -> bool:
    """Cohort owner-approved brands + registry GOVERNED/APPROVED/CANONICAL."""
    if brand_id is not None and brand_id in PHASE2D_COHORT_BRAND_IDS:
        return True
    return brand_display_is_governed(registry_row)


def product_type_display_approved(name_fa: str | None) -> bool:
    label = normalize_persian_text(name_fa)
    return bool(label) and len(label) >= 2


def product_type_naming_policy_blocked(name_fa: str | None) -> bool:
    label = normalize_persian_text(name_fa)
    if not label:
        return True
    if label in _BROAD_PT_LABELS:
        return True
    if "عمومی" in label:
        return True
    if len(label) < 4 and label not in {"کولیس", "گیج"}:
        return True
    return False


def product_type_is_governed(
    *,
    product_type_id: int | None,
    product_type_code: str | None,
    product_type_status: str | None,
    product_type_name_fa: str | None,
    has_active_definition: bool,
    canonical_policy: CanonicalProductTypePolicy | None = None,
) -> bool:
    if product_type_id is None:
        return False
    code = (product_type_code or "").strip()
    if not code:
        return False
    if (product_type_status or "").strip().lower() != "active":
        return False
    if not has_active_definition:
        return False
    pol = canonical_policy or CANONICAL_POLICY.get(code)
    if pol is None:
        return False
    if pol.title_label_status != "APPROVED" or not pol.canonical_title_fa:
        return False
    if pol.variant_policy == "HOLD_VARIANT_POLICY_UNDEFINED":
        return False
    _, resolution, _, _ = resolve_naming_profile_phase2d(code)
    return resolution == PROFILE_GOVERNED


def parse_kb_fact_value(value: Any) -> Any:
    if isinstance(value, dict):
        if "min" in value and "max" in value:
            return value
        if "value" in value:
            return value["value"]
    return value


def build_facts_from_kb_rows(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return (facts dict for builder, per-fact trace rows)."""
    traces: list[dict[str, Any]] = []
    facts: dict[str, Any] = {}
    for row in rows:
        key = (row.get("property_key") or row.get("key") or "").strip()
        if not key:
            continue
        status = str(row.get("status") or "").lower()
        raw = row.get("value")
        parsed = parse_kb_fact_value(raw)
        traces.append(
            {
                "property_key": key,
                "fact_id": row.get("fact_id"),
                "status": status,
                "raw": raw,
                "parsed": parsed,
            }
        )
        if status not in PUBLIC_FACT_STATUSES:
            continue
        if key in _LEGACY_ACCURACY_KEYS:
            continue
        if isinstance(parsed, dict) and "min" in parsed and "max" in parsed:
            facts["range_min_mm"] = parsed["min"]
            facts["range_max_mm"] = parsed["max"]
            facts["measurement_range"] = (parsed["min"], parsed["max"])
            facts[key] = parsed
        else:
            facts[key] = parsed
    return facts, traces


def _profile_variant_keys(profile: NamingProfile) -> tuple[str, ...]:
    return profile.primary_variant_fact_keys


def resolve_variant_from_canonical_policy(
    pol: CanonicalProductTypePolicy,
    profile: NamingProfile,
    facts: Mapping[str, Any],
    kb_traces: Sequence[Mapping[str, Any]],
) -> VariantFactTrace:
    if pol.variant_policy == "HOLD_VARIANT_POLICY_UNDEFINED":
        return VariantFactTrace(None, None, None, None, False, "HOLD_VARIANT_POLICY_UNDEFINED")
    if pol.variant_policy == "VARIANT_NOT_REQUIRED_APPROVED":
        return VariantFactTrace(
            None,
            None,
            None,
            None,
            False,
            "VARIANT_NOT_REQUIRED_APPROVED",
        )

    keys = _property_key_group(pol.primary_variant_property)
    if not keys:
        return VariantFactTrace(None, None, None, None, False, "HOLD_VARIANT_POLICY_UNDEFINED")
    return _resolve_required_variant_trace(keys, profile, facts, kb_traces)


def _resolve_required_variant_trace(
    keys: tuple[str, ...],
    profile: NamingProfile,
    facts: Mapping[str, Any],
    kb_traces: Sequence[Mapping[str, Any]],
) -> VariantFactTrace:
    published_traces = [
        t
        for t in kb_traces
        if str(t.get("status") or "").lower() in PUBLIC_FACT_STATUSES
        and (t.get("property_key") or "") in keys
        and (t.get("property_key") or "") not in _LEGACY_ACCURACY_KEYS
    ]
    if profile.variant_required and not published_traces:
        return VariantFactTrace(
            keys[0] if keys else None,
            None,
            None,
            None,
            False,
            "HOLD_MISSING_VARIANT_FACT",
        )

    formatted_values: list[str] = []
    used_trace: dict[str, Any] | None = None
    for key in keys:
        if key not in facts:
            continue
        probe_facts = dict(facts)
        from app.domain.product_naming import _format_variant  # noqa: PLC0415

        fmt = _format_variant(keys, facts.get(key), probe_facts)
        if fmt:
            formatted_values.append(fmt)
            if used_trace is None:
                for t in published_traces:
                    if t.get("property_key") == key:
                        used_trace = t
                        break

    if len(set(formatted_values)) > 1:
        return VariantFactTrace(
            keys[0],
            json.dumps(facts, ensure_ascii=False),
            formatted_values[0] if formatted_values else None,
            int(used_trace["fact_id"]) if used_trace and used_trace.get("fact_id") else None,
            True,
            "HOLD_AMBIGUOUS_VARIANT_FACT",
        )

    if profile.variant_required and not formatted_values:
        return VariantFactTrace(
            keys[0],
            None,
            None,
            None,
            False,
            "HOLD_MISSING_VARIANT_FACT",
        )

    if formatted_values:
        raw_repr = None
        fid = None
        if used_trace:
            raw_repr = json.dumps(used_trace.get("parsed"), ensure_ascii=False)
            fid = used_trace.get("fact_id")
        return VariantFactTrace(
            keys[0],
            raw_repr,
            formatted_values[0],
            int(fid) if fid is not None else None,
            True,
            "SUFFIX_GOVERNED",
        )

    return VariantFactTrace(None, None, None, None, False, "HOLD_MISSING_VARIANT_FACT")


def resolve_variant_policy(
    profile: NamingProfile,
    profile_resolution: str,
    facts: Mapping[str, Any],
    kb_traces: Sequence[Mapping[str, Any]],
    *,
    pol: CanonicalProductTypePolicy | None = None,
) -> VariantFactTrace:
    if pol is not None:
        return resolve_variant_from_canonical_policy(pol, profile, facts, kb_traces)
    if profile_resolution == PROFILE_MISSING or profile.code == "generic.v1":
        return VariantFactTrace(None, None, None, None, False, "HOLD_VARIANT_POLICY_UNDEFINED")

    keys = _profile_variant_keys(profile)
    if not keys or profile.max_variant_attributes <= 0:
        return VariantFactTrace(None, None, None, None, False, "VARIANT_NOT_REQUIRED_APPROVED")

    return _resolve_required_variant_trace(keys, profile, facts, kb_traces)


def identity_drift(input_row: Phase2DProductInput) -> bool:
    if input_row.frozen_manufacturer_code is None:
        return True
    if (input_row.manufacturer_code or "") != (input_row.frozen_manufacturer_code or ""):
        return True
    if input_row.frozen_sku is not None and (input_row.sku or "") != input_row.frozen_sku:
        return True
    if (
        input_row.frozen_brand_id is not None
        and input_row.brand_id is not None
        and int(input_row.brand_id) != int(input_row.frozen_brand_id)
    ):
        return True
    return False


def audit_name_quality_flags(
    *,
    current_name: str,
    proposed_name: str | None,
    product_type_name_fa: str | None,
    brand_display: str,
    manufacturer_code: str,
) -> list[str]:
    flags: list[str] = []
    cur = current_name or ""
    prop = proposed_name or ""
    if prop and compare_product_name_v1(cur, prop)["equal"]:
        flags.append("already_canonical")
    pt_fa = normalize_persian_text(product_type_name_fa)
    if pt_fa and pt_fa not in normalize_persian_text(cur):
        flags.append("wrong_product_type")
    if brand_display and brand_display not in cur:
        flags.append("brand_missing")
    if brand_display and cur.count(brand_display) > 1:
        flags.append("brand_duplicated")
    if manufacturer_code and manufacturer_code not in cur:
        flags.append("manufacturer_code_missing")
    elif manufacturer_code and cur.count(manufacturer_code) > 1:
        flags.append("manufacturer_code_duplicated")
    if "مدل" in cur and "کد" in prop:
        flags.append("model_to_code_candidate")
    if "مدل" in cur and "کد" not in cur:
        flags.append("uses_model_label")
    for term in ("موجود", "ناموجود", "تخفیف", "قیمت"):
        if term in cur:
            flags.append("marketing_or_status_text")
    lint_cur = lint_product_name_v1(cur, manufacturer_code=manufacturer_code)
    lint_prop = lint_product_name_v1(prop, manufacturer_code=manufacturer_code) if prop else []
    if any("ARABIC" in x for x in lint_cur):
        flags.append("persian_normalization_needed")
    if prop and cur != prop and compare_product_name_v1(cur, prop)["equal"]:
        flags.append("formatting_only_difference")
    if any(c == "USES_MODEL_LABEL" for c in lint_cur):
        flags.append("uses_model_label")
    if prop and lint_prop:
        flags.extend([f"proposed:{x}" for x in lint_prop if x not in flags])
    return sorted(set(flags))


def validate_proposed_name(
    name: str | None,
    *,
    product_type_name_fa: str | None,
    brand_display: str,
    manufacturer_code: str,
) -> list[str]:
    issues: list[str] = []
    if not name or not str(name).strip():
        issues.append("empty_name")
        return issues
    pt = normalize_persian_text(product_type_name_fa)
    if pt and not normalize_persian_text(name).startswith(pt):
        issues.append("product_type_not_prefix")
    if brand_display:
        if name.count(brand_display) != 1:
            issues.append("brand_count_not_one")
    if manufacturer_code:
        if name.count(manufacturer_code) != 1:
            issues.append("manufacturer_code_count_not_one")
        if f"کد {manufacturer_code}" not in name and f"کد{manufacturer_code}" not in name:
            issues.append("code_label_missing")
    issues.extend(lint_product_name_v1(name, manufacturer_code=manufacturer_code))
    return issues


def classify_product_phase2d(
    row: Phase2DProductInput,
    *,
    brand_registry_row: Mapping[str, Any] | None,
    collision_product_ids: Sequence[int] = (),
) -> tuple[Phase2DAuditRow, NamingResult | None]:
    brand_display = brand_display_for_title(row.brand_name, registry_row=brand_registry_row)
    comp_cur = normalize_persian_text(row.current_name)
    meta_explicit = bool((row.meta_title or "").strip())
    seo_impact = "NO_DIRECT_TITLE_FALLBACK" if meta_explicit else "YES"

    base_kwargs = {
        "product_id": row.product_id,
        "sku": row.sku,
        "brand_id": row.brand_id,
        "brand_name": row.brand_name or "",
        "brand_display": brand_display,
        "manufacturer_code": row.manufacturer_code or "",
        "product_type_id": row.product_type_id,
        "product_type_code": row.product_type_code or "",
        "product_type_name_fa": row.product_type_name_fa or "",
        "canonical_title_fa": "",
        "canonical_title_status": "",
        "product_type_governed": False,
        "variant_policy": "",
        "variant_policy_basis": "",
        "policy_review_status": "",
        "current_name": row.current_name,
        "proposed_name": "",
        "comparison_normalized_current": comp_cur,
        "comparison_normalized_proposed": "",
        "terminal_classification": "HOLD_OTHER",
        "classification_reason": "",
        "name_quality_flags": "",
        "proposed_collision": "no",
        "collision_product_ids": ",".join(str(i) for i in collision_product_ids),
        "meta_title_present": "yes" if meta_explicit else "no",
        "seo_title_impact": seo_impact,
        "is_active": "yes" if row.is_active else "no",
        "is_available": "yes" if row.is_available else "no",
        "priced": "yes" if row.priced else "no",
        "has_image": "yes" if row.has_image else "no",
        "storefront_visible": "yes" if row.storefront_visible else "no",
        "sellable": "yes" if row.sellable else "no",
        "variant_policy_status": "",
        "variant_property_code": "",
        "variant_raw_value": "",
        "variant_formatted_value": "",
        "variant_fact_id": "",
        "variant_fact_published": "",
    }

    def finish(
        terminal: str,
        reason: str,
        proposed: str | None = None,
        naming: NamingResult | None = None,
        variant: VariantFactTrace | None = None,
        pol: CanonicalProductTypePolicy | None = None,
    ) -> tuple[Phase2DAuditRow, NamingResult | None]:
        prop_n = proposed or ""
        flags = audit_name_quality_flags(
            current_name=row.current_name,
            proposed_name=prop_n or None,
            product_type_name_fa=row.product_type_name_fa,
            brand_display=brand_display,
            manufacturer_code=row.manufacturer_code,
        )
        audit = Phase2DAuditRow(
            **{
                **base_kwargs,
                "canonical_title_fa": pol.canonical_title_fa if pol else "",
                "canonical_title_status": pol.title_label_status if pol else "",
                "variant_policy": pol.variant_policy if pol else "",
                "variant_policy_basis": pol.policy_basis if pol else "",
                "product_type_governed": product_type_is_governed(
                    product_type_id=row.product_type_id,
                    product_type_code=row.product_type_code,
                    product_type_status=row.product_type_status,
                    product_type_name_fa=row.product_type_name_fa,
                    has_active_definition=row.product_type_has_active_definition,
                    canonical_policy=pol,
                ),
                "proposed_name": prop_n,
                "comparison_normalized_proposed": normalize_persian_text(prop_n),
                "terminal_classification": terminal,
                "classification_reason": reason,
                "name_quality_flags": "|".join(flags),
                "variant_policy_status": (variant.policy_status if variant else ""),
                "variant_property_code": (variant.property_code if variant and variant.property_code else ""),
                "variant_raw_value": (variant.raw_value if variant and variant.raw_value else ""),
                "variant_formatted_value": (
                    variant.formatted_value if variant and variant.formatted_value else ""
                ),
                "variant_fact_id": str(variant.fact_id) if variant and variant.fact_id else "",
                "variant_fact_published": "yes" if variant and variant.published else "no",
            }
        )
        return audit, naming

    if identity_drift(row):
        return finish("HOLD_IDENTITY_DRIFT", "live_identity_ne_frozen_phase2c")

    if row.product_type_id is None:
        return finish("HOLD_MISSING_PRODUCT_TYPE", "product_type_id_null")

    pol = CANONICAL_POLICY.get((row.product_type_code or "").strip())
    if pol is None:
        return finish("HOLD_UNGOVERNED_PRODUCT_TYPE", "missing_canonical_policy_row")

    if pol.title_label_status != "APPROVED" or not pol.canonical_title_fa:
        terminal = "HOLD_PRODUCT_TYPE_TITLE_LABEL_UNAPPROVED"
        if pol.title_hold_reason in {"synonym_or_slash_label", "generic_product_type_label"}:
            terminal = "HOLD_PRODUCT_TYPE_NAMING_POLICY"
        return finish(terminal, pol.title_hold_reason or "title_label_not_approved", pol=pol)

    if not brand_display_governed_phase2d(row.brand_id, brand_registry_row):
        return finish("HOLD_BRAND_DISPLAY_UNGOVERNED", "brand_display_not_in_owner_cohort_or_registry", pol=pol)

    if (row.product_type_status or "").strip().lower() != "active" or not row.product_type_has_active_definition:
        return finish("HOLD_UNGOVERNED_PRODUCT_TYPE", "product_type_inactive_or_no_active_definition", pol=pol)

    profile_code, profile_resolution, profile, _ = resolve_naming_profile_phase2d(row.product_type_code)
    if profile_resolution != PROFILE_GOVERNED:
        return finish("HOLD_UNGOVERNED_PRODUCT_TYPE", "naming_profile_not_governed", pol=pol)

    facts, kb_traces = build_facts_from_kb_rows(row.kb_facts)

    variant_trace = resolve_variant_policy(profile, profile_resolution, facts, kb_traces, pol=pol)
    if variant_trace.policy_status == "HOLD_VARIANT_POLICY_UNDEFINED":
        return finish(
            "HOLD_VARIANT_POLICY_UNDEFINED",
            pol.policy_basis or "variant_policy_undefined",
            variant=variant_trace,
            pol=pol,
        )
    if variant_trace.policy_status == "HOLD_MISSING_VARIANT_FACT":
        return finish(
            "HOLD_MISSING_VARIANT_FACT",
            "required_published_variant_fact_missing",
            variant=variant_trace,
            pol=pol,
        )
    if variant_trace.policy_status == "HOLD_AMBIGUOUS_VARIANT_FACT":
        return finish("HOLD_AMBIGUOUS_VARIANT_FACT", "conflicting_variant_facts", variant=variant_trace, pol=pol)

    published_used = [
        t
        for t in kb_traces
        if str(t.get("status") or "").lower() in PUBLIC_FACT_STATUSES
        and (t.get("property_key") or "") in profile.primary_variant_fact_keys
        and (t.get("property_key") or "") not in _LEGACY_ACCURACY_KEYS
    ]
    variant_facts_gov = (
        pol.variant_policy == "VARIANT_NOT_REQUIRED_APPROVED"
        or not profile.primary_variant_fact_keys
        or (
            bool(published_used)
            and all(str(t.get("status") or "").lower() in PUBLIC_FACT_STATUSES for t in published_used)
        )
    )
    if profile.variant_required and profile.primary_variant_fact_keys and not variant_facts_gov:
        return finish("HOLD_MISSING_VARIANT_FACT", "variant_fact_not_published", variant=variant_trace, pol=pol)

    oem_gov = bool((row.manufacturer_code or "").strip())
    brand_gov = brand_display_governed_phase2d(row.brand_id, brand_registry_row)
    governance = NamingGovernanceContext(
        product_type_governed=True,
        manufacturer_code_governed=oem_gov,
        brand_display_governed=brand_gov,
        naming_profile_governed=profile_resolution == PROFILE_GOVERNED,
        variant_facts_governed=variant_facts_gov if profile.primary_variant_fact_keys else True,
        identity_qualifiers_governed=False,
    )

    naming = build_product_name_v1(
        product_type_fa=pol.canonical_title_fa,
        brand_raw=row.brand_name,
        manufacturer_code=row.manufacturer_code,
        facts=facts,
        naming_profile=profile_code,
        brand_registry_row=brand_registry_row,
        current_name=row.current_name,
        governance=governance,
        profile_resolution=profile_resolution,
    )

    proposed = naming.name
    if not proposed:
        terminal = "HOLD_STRUCTURAL_CONFLICT"
        if naming.state == "HOLD_MISSING_VARIANT_ATTRIBUTE":
            terminal = "HOLD_MISSING_VARIANT_FACT"
        elif naming.state in TERMINAL_CLASSIFICATIONS:
            terminal = naming.state
        elif any("variant" in c for c in naming.reason_codes):
            terminal = "HOLD_MISSING_VARIANT_FACT"
        return finish(
            terminal,
            ";".join(naming.reason_codes) or naming.state,
            proposed="",
            naming=naming,
            variant=variant_trace,
        )

    structural = validate_proposed_name(
        proposed,
        product_type_name_fa=pol.canonical_title_fa,
        brand_display=brand_display,
        manufacturer_code=row.manufacturer_code,
    )
    if any(
        x in structural
        for x in (
            "empty_name",
            "product_type_not_prefix",
            "brand_count_not_one",
            "manufacturer_code_count_not_one",
        )
    ):
        return finish(
            "HOLD_STRUCTURAL_CONFLICT",
            ";".join(structural),
            proposed=proposed,
            naming=naming,
            variant=variant_trace,
        )

    if collision_product_ids:
        return finish(
            "HOLD_NAME_COLLISION",
            "proposed_name_collision",
            proposed=proposed,
            naming=naming,
            variant=variant_trace,
        )

    if naming.state == "EXACT" or compare_product_name_v1(row.current_name, proposed)["equal"]:
        return finish(
            "READY_NO_CHANGE",
            "canonical_name_matches_current",
            proposed=proposed,
            naming=naming,
            variant=variant_trace,
        )

    if naming.confidence != "high" or naming.state != "RENAME_SAFE":
        return finish(
            "HOLD_STRUCTURAL_CONFLICT",
            ";".join(naming.reason_codes) or naming.state,
            proposed=proposed,
            naming=naming,
            variant=variant_trace,
        )

    return finish(
        "READY_RENAME",
        "governed_canonical_name_ready",
        proposed=proposed,
        naming=naming,
        variant=variant_trace,
        pol=pol,
    )


def detect_collisions(
    audits: Sequence[Phase2DAuditRow],
    catalog_names: Mapping[int, str],
) -> dict[str, Any]:
    """Collision groups for proposed READY names and identity keys."""
    proposed_by_name: dict[str, list[int]] = defaultdict(list)
    proposed_by_norm: dict[str, list[int]] = defaultdict(list)
    brand_code: dict[tuple[int, str], list[int]] = defaultdict(list)
    pt_code: dict[tuple[int, str], list[int]] = defaultdict(list)

    for a in audits:
        if a.terminal_classification != "READY_RENAME" or not a.proposed_name:
            continue
        proposed_by_name[a.proposed_name].append(a.product_id)
        proposed_by_norm[normalize_persian_text(a.proposed_name)].append(a.product_id)
        if a.brand_id is not None and a.manufacturer_code:
            brand_code[(a.brand_id, a.manufacturer_code)].append(a.product_id)
        if a.product_type_id is not None and a.manufacturer_code:
            pt_code[(a.product_type_id, a.manufacturer_code)].append(a.product_id)

    cohort_name_dupes = {k: v for k, v in proposed_by_name.items() if len(v) > 1}
    cohort_norm_dupes = {k: v for k, v in proposed_by_norm.items() if len(v) > 1}

    catalog_collisions: dict[str, list[int]] = {}
    for a in audits:
        if not a.proposed_name or a.terminal_classification not in (
            "READY_RENAME",
            "READY_NO_CHANGE",
        ):
            continue
        for pid, existing in catalog_names.items():
            if pid == a.product_id:
                continue
            if existing == a.proposed_name:
                catalog_collisions.setdefault(a.proposed_name, []).append(pid)

    brand_code_dupes = {f"{k[0]}|{k[1]}": v for k, v in brand_code.items() if len(v) > 1}
    pt_code_dupes = {f"{k[0]}|{k[1]}": v for k, v in pt_code.items() if len(v) > 1}

    ready_affected = []
    for a in audits:
        if a.terminal_classification != "READY_RENAME":
            continue
        if a.proposed_name in cohort_name_dupes or normalize_persian_text(a.proposed_name) in cohort_norm_dupes:
            ready_affected.append(a.product_id)
        elif a.proposed_name in catalog_collisions:
            ready_affected.append(a.product_id)

    return {
        "exact_proposed_within_cohort": cohort_name_dupes,
        "normalized_proposed_within_cohort": cohort_norm_dupes,
        "versus_existing_catalog": catalog_collisions,
        "brand_manufacturer_code": brand_code_dupes,
        "product_type_manufacturer_code": pt_code_dupes,
        "ready_rename_affected": sorted(set(ready_affected)),
    }


def apply_collision_holds(
    audits: list[Phase2DAuditRow],
    collision_report: Mapping[str, Any],
) -> None:
    cohort_exact = collision_report.get("exact_proposed_within_cohort") or {}
    cohort_norm = collision_report.get("normalized_proposed_within_cohort") or {}
    catalog = collision_report.get("versus_existing_catalog") or {}

    for a in audits:
        if a.terminal_classification != "READY_RENAME":
            continue
        peers: list[int] = []
        if a.proposed_name in cohort_exact:
            peers.extend([p for p in cohort_exact[a.proposed_name] if p != a.product_id])
        norm = normalize_persian_text(a.proposed_name)
        if norm in cohort_norm:
            peers.extend([p for p in cohort_norm[norm] if p != a.product_id])
        if a.proposed_name in catalog:
            peers.extend(catalog[a.proposed_name])
        if peers:
            a.terminal_classification = "HOLD_NAME_COLLISION"
            a.classification_reason = "proposed_name_collision"
            a.proposed_collision = "yes"
            a.collision_product_ids = ",".join(str(p) for p in sorted(set(peers)))


def reconcile_classifications(audits: Sequence[Phase2DAuditRow]) -> dict[str, Any]:
    counts = Counter(a.terminal_classification for a in audits)
    total = len(audits)
    unknown = [c for c in counts if c not in TERMINAL_CLASSIFICATIONS]
    return {
        "total": total,
        "counts": dict(counts),
        "reconciles": total == PHASE2C_FROZEN_ROWS and sum(counts.values()) == total and not unknown,
        "unknown_classifications": unknown,
    }


def deterministic_human_review_sample(
    audits: Sequence[Phase2DAuditRow],
) -> list[Phase2DAuditRow]:
    """Stratified sample: 10 READY_RENAME per cohort brand + HOLD exemplars."""
    brand_map = {3: "INSIZE", 4: "DASQUA", 5: "TERMA"}
    sample: list[Phase2DAuditRow] = []
    seen: set[int] = set()

    def pick_strata(rows: list[Phase2DAuditRow], n: int) -> None:
        if not rows:
            return
        rows = sorted(rows, key=lambda r: r.product_id)
        if len(rows) <= n:
            chosen = rows
        else:
            thirds = [rows[0], rows[len(rows) // 2], rows[-1]]
            remaining = [r for r in rows if r not in thirds]
            chosen = thirds + remaining[: max(0, n - 3)]
            chosen = chosen[:n]
        for r in chosen:
            if r.product_id not in seen:
                seen.add(r.product_id)
                sample.append(r)

    for bid, _ in brand_map.items():
        ready = [a for a in audits if a.brand_id == bid and a.terminal_classification == "READY_RENAME"]
        pick_strata(ready, 10)

    hold_buckets = sorted({a.terminal_classification for a in audits if a.terminal_classification.startswith("HOLD_")})
    for bucket in hold_buckets:
        rows = [a for a in audits if a.terminal_classification == bucket]
        pick_strata(rows, min(3, len(rows)))

    return sorted(sample, key=lambda r: (r.terminal_classification, r.product_id))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_logic_fingerprint(domain_path: Path, script_path: Path) -> str:
    h = hashlib.sha256()
    h.update(domain_path.read_bytes())
    h.update(script_path.read_bytes())
    h.update(NAMING_STANDARD_VERSION.encode())
    h.update(authoritative_policy_path().read_bytes())
    return h.hexdigest()


def canonical_candidate_rows(audits: Sequence[Phase2DAuditRow]) -> list[dict[str, str]]:
    ready = [a for a in audits if a.terminal_classification == "READY_RENAME"]
    ready.sort(key=lambda a: a.product_id)
    return [
        {
            "product_id": str(a.product_id),
            "sku": a.sku,
            "proposed_name": a.proposed_name,
            "manufacturer_code": a.manufacturer_code,
            "product_type_code": a.product_type_code,
            "canonical_title_fa": a.canonical_title_fa,
            "variant_policy_status": a.variant_policy_status,
            "variant_property_code": a.variant_property_code,
            "variant_formatted_value": a.variant_formatted_value,
        }
        for a in ready
    ]


def canonical_candidate_bytes(rows: Sequence[Mapping[str, str]]) -> bytes:
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(CANONICAL_CANDIDATE_FIELDNAMES), lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in CANONICAL_CANDIDATE_FIELDNAMES})
    return buf.getvalue().encode("utf-8")


def canonical_candidate_sha256(rows: Sequence[Mapping[str, str]]) -> str:
    return sha256_bytes(canonical_candidate_bytes(rows))


def write_canonical_candidate_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_candidate_bytes(rows))


def build_policy_review_sample(audits: Sequence[Phase2DAuditRow]) -> list[Phase2DAuditRow]:
    """Deterministic per-Product-Type policy review sample for READY cohort."""
    ready = [
        a
        for a in audits
        if a.terminal_classification in ("READY_RENAME", "HOLD_POLICY_REVIEW_BLOCKED")
    ]
    by_pt: dict[str, list[Phase2DAuditRow]] = defaultdict(list)
    for a in ready:
        by_pt[a.product_type_code or "NO_PT"].append(a)

    chosen: list[Phase2DAuditRow] = []
    seen: set[int] = set()

    def add(row: Phase2DAuditRow) -> None:
        if row.product_id not in seen:
            seen.add(row.product_id)
            chosen.append(row)

    for code in sorted(by_pt):
        rows = sorted(by_pt[code], key=lambda r: r.product_id)
        if len(rows) == 1:
            add(rows[0])
            continue
        add(rows[0])
        add(rows[len(rows) // 2])
        add(rows[-1])

    for a in ready:
        title = a.canonical_title_fa or ""
        if any(ch in title for ch in ("/", "|")):
            add(a)
        if a.variant_policy == "VARIANT_NOT_REQUIRED_APPROVED":
            add(a)

    return sorted(chosen, key=lambda r: (r.product_type_code, r.product_id))


def evaluate_policy_review_status(row: Phase2DAuditRow) -> tuple[str, str]:
    """Deterministic policy review for one READY representative row."""
    if row.terminal_classification not in ("READY_RENAME", "HOLD_POLICY_REVIEW_BLOCKED"):
        return "REVIEW", "not_ready_rename"
    if row.canonical_title_status != "APPROVED":
        return "FAIL", "canonical_title_not_approved"
    if any(ch in (row.canonical_title_fa or "") for ch in ("/", "|")):
        return "FAIL", "slash_or_alternative_in_canonical_title"
    if row.manufacturer_code and row.manufacturer_code not in (row.proposed_name or ""):
        return "FAIL", "manufacturer_code_not_exact_in_proposed"
    if (row.proposed_name or "").count("کد") != 1:
        return "FAIL", "code_label_count"
    canon = normalize_persian_text(row.canonical_title_fa)
    if canon and not normalize_persian_text(row.proposed_name or "").startswith(canon):
        return "FAIL", "canonical_title_not_prefix"
    if row.variant_policy == "VARIANT_REQUIRED" and row.variant_policy_status not in {
        "SUFFIX_GOVERNED",
    }:
        return "FAIL", "required_variant_not_governed"
    return "PASS", "policy_checks_ok"


def apply_policy_review_holds(audits: list[Phase2DAuditRow]) -> dict[str, Any]:
    """Demote READY rows when their Product Type policy review is not PASS."""
    ready_pts = {a.product_type_code for a in audits if a.terminal_classification == "READY_RENAME"}
    sample = build_policy_review_sample(audits)
    pt_status: dict[str, str] = {}
    pt_notes: dict[str, str] = {}
    for pt in sorted(ready_pts):
        reps = [r for r in sample if r.product_type_code == pt]
        if not reps:
            fallback = [
                a
                for a in audits
                if a.terminal_classification == "READY_RENAME" and a.product_type_code == pt
            ]
            fallback.sort(key=lambda r: r.product_id)
            reps = [fallback[len(fallback) // 2]]
        verdicts = [evaluate_policy_review_status(r) for r in reps]
        statuses = [v[0] for v in verdicts]
        if any(s == "FAIL" for s in statuses):
            pt_status[pt] = "FAIL"
            pt_notes[pt] = next(n for s, n in verdicts if s == "FAIL")
        elif any(s == "REVIEW" for s in statuses):
            pt_status[pt] = "REVIEW"
            pt_notes[pt] = next(n for s, n in verdicts if s == "REVIEW")
        else:
            pt_status[pt] = "PASS"
            pt_notes[pt] = verdicts[0][1]

    fail_pts = {pt for pt, st in pt_status.items() if st != "PASS"}
    for a in audits:
        a.policy_review_status = pt_status.get(a.product_type_code, "N/A")
        if a.terminal_classification == "READY_RENAME" and a.product_type_code in fail_pts:
            a.terminal_classification = "HOLD_POLICY_REVIEW_BLOCKED"
            a.classification_reason = pt_notes.get(a.product_type_code, "policy_review_failed")

    counts = Counter(pt_status.values())
    return {
        "product_type_status": pt_status,
        "PASS": counts.get("PASS", 0),
        "FAIL": counts.get("FAIL", 0),
        "REVIEW": counts.get("REVIEW", 0),
    }


def compute_freeze_status(
    *,
    reconciles: bool,
    identity_drift: int,
    replay_identical: bool,
    ready_collision_count: int,
    policy_review: Mapping[str, Any],
    read_only_ok: bool,
) -> str:
    if identity_drift or not reconciles or not replay_identical or not read_only_ok:
        return "BLOCKED"
    if policy_review.get("FAIL") or policy_review.get("REVIEW"):
        return "PARTIAL"
    if ready_collision_count:
        return "BLOCKED"
    return "READY_FOR_OWNER_RENAME_REVIEW"


AUDIT_CSV_FIELDS: tuple[str, ...] = tuple(
    [
        "product_id",
        "sku",
        "brand_id",
        "brand_name",
        "brand_display",
        "manufacturer_code",
        "product_type_id",
        "product_type_code",
        "product_type_name_fa",
        "canonical_title_fa",
        "canonical_title_status",
        "product_type_governed",
        "variant_policy",
        "variant_policy_basis",
        "variant_policy_status",
        "policy_review_status",
        "variant_property_code",
        "variant_raw_value",
        "variant_formatted_value",
        "variant_fact_id",
        "variant_fact_published",
        "current_name",
        "proposed_name",
        "comparison_normalized_current",
        "comparison_normalized_proposed",
        "terminal_classification",
        "classification_reason",
        "name_quality_flags",
        "proposed_collision",
        "collision_product_ids",
        "meta_title_present",
        "seo_title_impact",
        "is_active",
        "is_available",
        "priced",
        "has_image",
        "storefront_visible",
        "sellable",
    ]
)
