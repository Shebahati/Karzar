"""Karzar Product Naming Standard v1 — pure deterministic engine.

No network, no DB writes, no AI. Structured identity → display name.

Phase 2B: HIGH requires every input used in the generated title to be
governed (PT, OEM, brand display, naming profile, and any used variant
facts / identity qualifiers). Heuristic candidates never become governed.
generic.v1 cannot produce HIGH.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from app.utils.seo_descriptions import display_brand_name, split_bilingual_label

NAMING_STANDARD_VERSION = "karzar_product_naming_v1"
OEM_LABEL_FA = "کد"
SOFT_LENGTH_TARGET = 120
HARD_LENGTH_LIMIT = 255

PROHIBITED_TERMS: tuple[str, ...] = (
    "بهترین",
    "حرفه‌ای",
    "حرفه ای",
    "با کیفیت",
    "باکیفیت",
    "اورجینال",
    "اصل چین",
    "اصل",
    "ویژه",
    "پرفروش",
    "ارزان",
    "فوق‌العاده",
    "فوق العاده",
    "تضمینی",
    "قیمت ویژه",
    "موجود",
    "ناموجود",
    "ارسال فوری",
    "تخفیف",
    "فروش ویژه",
    "خرید",
    "قیمت",
    "فروش",
    "کارزار",
)

_ARABIC_YE = "ي"
_PERSIAN_YE = "ی"
_ARABIC_KE = "ك"
_PERSIAN_KE = "ک"
_WS_RE = re.compile(r"\s+")
_MODEL_LABEL_RE = re.compile(r"(?:^|[\s،,])مدل\s+", re.UNICODE)
_CODE_LABEL_RE = re.compile(r"(?:^|[\s،,])کد\s+", re.UNICODE)
_RANGE_IN_SPECS_RE = re.compile(
    r"(?P<min>\d+(?:\.\d+)?)\s*[-–~to]+\s*(?P<max>\d+(?:\.\d+)?)\s*(?:mm|میلی\s*متر)?",
    re.IGNORECASE,
)
_DIAMETER_RE = re.compile(r"(?:Ø|⌀|phi|diameter|قطر)?\s*(?P<d>\d+(?:\.\d+)?)\s*mm", re.I)
_THREAD_RE = re.compile(r"\bM(?P<size>\d+(?:\.\d+)?)\s*[x×]\s*(?P<pitch>\d+(?:\.\d+)?)\b", re.I)
_CAPACITY_MM_RE = re.compile(r"(?P<n>\d+)\s*mm\b", re.I)
_LATIN_PREF_BRANDS = frozenset({"ZCC.CT", "ZCC"})


@dataclass(frozen=True)
class NamingProfile:
    code: str
    manufacturer_code_required: bool = True
    brand_required: bool = True
    product_type_required: bool = True
    primary_variant_fact_keys: tuple[str, ...] = ()
    max_variant_attributes: int = 1
    brand_policy: str = "prefer_fa"  # prefer_fa | prefer_en | registry
    allow_identity_qualifiers: bool = True
    variant_required: bool = True


PROFILES: dict[str, NamingProfile] = {
    "metrology.caliper.v1": NamingProfile(
        code="metrology.caliper.v1",
        primary_variant_fact_keys=("measurement_range", "range", "range_min_mm"),
    ),
    "metrology.micrometer.v1": NamingProfile(
        code="metrology.micrometer.v1",
        primary_variant_fact_keys=("measurement_range", "range", "range_min_mm"),
    ),
    "cutting.turning_insert.v1": NamingProfile(
        code="cutting.turning_insert.v1",
        primary_variant_fact_keys=(),
        max_variant_attributes=0,
        brand_policy="prefer_en",
        variant_required=False,
    ),
    "cutting.solid_tool.v1": NamingProfile(
        code="cutting.solid_tool.v1",
        primary_variant_fact_keys=("cutting_diameter", "diameter", "diameter_mm"),
        max_variant_attributes=1,
        brand_policy="prefer_en",
        variant_required=False,
    ),
    "workholding.chuck.v1": NamingProfile(
        code="workholding.chuck.v1",
        primary_variant_fact_keys=("capacity", "capacity_mm", "diameter"),
        variant_required=False,
    ),
    "thread_repair.insert.v1": NamingProfile(
        code="thread_repair.insert.v1",
        primary_variant_fact_keys=("thread_size",),
        variant_required=False,
    ),
    "fluids.lubricant.v1": NamingProfile(
        code="fluids.lubricant.v1",
        primary_variant_fact_keys=("volume",),
        variant_required=False,
    ),
    "machines.equipment.v1": NamingProfile(
        code="machines.equipment.v1",
        primary_variant_fact_keys=(),
        max_variant_attributes=0,
        variant_required=False,
    ),
    "toolholding.holder.v1": NamingProfile(
        code="toolholding.holder.v1",
        primary_variant_fact_keys=("interface",),
        max_variant_attributes=1,
        brand_policy="prefer_en",
        variant_required=False,
    ),
    "generic.v1": NamingProfile(
        code="generic.v1",
        primary_variant_fact_keys=(),
        max_variant_attributes=0,
        variant_required=False,
    ),
}

# Public alias
NAMING_PROFILES = PROFILES

# Deterministic ProductType.code → naming profile (from PRODUCT_TYPE_NAMING_PROFILES.csv).
# Unmapped codes resolve to generic.v1 with PROFILE_MISSING (cannot yield HIGH).
PRODUCT_TYPE_CODE_TO_PROFILE: dict[str, str] = {
    "PROVISIONAL_METROLOGY_CALIPER": "metrology.caliper.v1",
    "PROVISIONAL_METROLOGY_MICROMETER": "metrology.micrometer.v1",
    "PROVISIONAL_CUTTING_TURNING_INSERT": "cutting.turning_insert.v1",
    "PROVISIONAL_CUTTING_SOLID_TOOL": "cutting.solid_tool.v1",
    "PROVISIONAL_WORKHOLDING_CHUCK": "workholding.chuck.v1",
    "PROVISIONAL_THREAD_REPAIR_INSERT": "thread_repair.insert.v1",
    "PROVISIONAL_FLUIDS_LUBRICANT": "fluids.lubricant.v1",
    "PROVISIONAL_MACHINES_EQUIPMENT": "machines.equipment.v1",
    "PROVISIONAL_TOOLHOLDING_HOLDER": "toolholding.holder.v1",
    "PROVISIONAL_GENERIC": "generic.v1",
}

PROFILE_GOVERNED = "PROFILE_GOVERNED"
PROFILE_PROPOSED = "PROFILE_PROPOSED"
PROFILE_MISSING = "PROFILE_MISSING"


@dataclass(frozen=True)
class NamingGovernanceContext:
    """Explicit governance contract — value-exists ≠ governed-for-auto-rename."""

    product_type_governed: bool = False
    manufacturer_code_governed: bool = False
    brand_display_governed: bool = False
    naming_profile_governed: bool = False
    variant_facts_governed: bool = False
    identity_qualifiers_governed: bool = False

    def as_dict(self) -> dict[str, bool]:
        return {
            "product_type": self.product_type_governed,
            "manufacturer_code": self.manufacturer_code_governed,
            "brand_display": self.brand_display_governed,
            "naming_profile": self.naming_profile_governed,
            "variant_facts": self.variant_facts_governed,
            "identity_qualifiers": self.identity_qualifiers_governed,
        }


@dataclass(frozen=True)
class NamingResult:
    name: str | None
    confidence: str
    warnings: list[str] = field(default_factory=list)
    used_fields: list[str] = field(default_factory=list)
    omitted_fields: list[str] = field(default_factory=list)
    profile: str | None = None
    state: str = "MANUAL_REVIEW"
    reason_codes: list[str] = field(default_factory=list)
    naming_standard_version: str = NAMING_STANDARD_VERSION
    governance: dict[str, bool] = field(default_factory=dict)
    profile_resolution: str | None = None

    @property
    def version(self) -> str:
        return self.naming_standard_version


def resolve_naming_profile_v1(
    product_type_code: str | None,
) -> tuple[str, str]:
    """Map ProductType.code → (profile_code, resolution_status).

    Never guesses from Product.name. Unmapped / generic → PROFILE_MISSING.
    """
    code = (product_type_code or "").strip()
    if not code:
        return "generic.v1", PROFILE_MISSING
    mapped = PRODUCT_TYPE_CODE_TO_PROFILE.get(code)
    if mapped is None:
        return "generic.v1", PROFILE_MISSING
    if mapped == "generic.v1" or mapped not in PROFILES:
        return "generic.v1", PROFILE_MISSING
    return mapped, PROFILE_GOVERNED


def brand_display_is_governed(registry_row: Mapping[str, Any] | None) -> bool:
    """True when Brand Display Registry status is explicitly GOVERNed."""
    if not registry_row:
        return False
    status = str(registry_row.get("status") or "").strip().upper()
    return status in {"GOVERNED", "APPROVED", "CANONICAL"}


def normalize_persian_text(text: str | None) -> str:
    """Normalize Persian display text (not OEM codes)."""
    if not text:
        return ""
    out = text.replace(_ARABIC_YE, _PERSIAN_YE).replace(_ARABIC_KE, _PERSIAN_KE)
    out = _WS_RE.sub(" ", out).strip()
    return out


# Back-compat alias used by earlier drafts / audit notes.
normalize_persian_display = normalize_persian_text


def brand_display_for_title(
    brand_raw: str | None,
    preferred_form: str | None = None,
    registry_row: Mapping[str, Any] | None = None,
) -> str:
    """Resolve brand token for product titles.

    preferred_form: fa | en | mixed | exact override string | None (auto)
    registry_row may supply display_fa / display_en / preferred_product_title_form
    """
    if preferred_form and preferred_form.strip().lower() not in {"", "fa", "en", "mixed", "auto"}:
        return preferred_form.strip()

    if registry_row:
        form = (preferred_form or registry_row.get("preferred_product_title_form") or "").strip().lower()
        fa = (registry_row.get("display_fa") or "").strip()
        en = (registry_row.get("display_en") or "").strip()
        if form == "en" and en:
            return en
        if form == "fa" and fa:
            return normalize_persian_text(fa)
        if form == "mixed" and en:
            return en
        if fa:
            return normalize_persian_text(fa)
        if en:
            return en

    latin, persian = split_bilingual_label(brand_raw)
    form = (preferred_form or "").strip().lower()
    if form == "en":
        return (latin or brand_raw or "").strip()
    if form == "fa":
        return normalize_persian_text(persian or display_brand_name(brand_raw) or latin or "")

    # Auto: Latin trademark preferred for known cutting brands (e.g. ZCC.CT).
    if latin and latin.strip().upper() in {b.upper() for b in _LATIN_PREF_BRANDS}:
        return latin.strip()

    return normalize_persian_text(display_brand_name(brand_raw) or latin or brand_raw or "")


def format_measurement_range_mm(min_v: float | int | str, max_v: float | int | str) -> str:
    return f"{_num(min_v)}–{_num(max_v)} میلی‌متر"


def format_diameter_mm(d: float | int | str) -> str:
    return f"Ø{_num(d)} میلی‌متر"


def format_metric_thread(size: float | int | str, pitch: float | int | str) -> str:
    size_s = str(size).strip()
    if size_s.upper().startswith("M"):
        size_s = size_s[1:]
    return f"M{_num(size_s)}×{_num(pitch)}"


def _num(v: float | int | str) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, str):
        s = v.strip()
        try:
            f = float(s)
            if f.is_integer():
                return str(int(f))
            return s
        except ValueError:
            return s
    return str(v)


def extract_manufacturer_code_candidates(
    name: str | None = None,
    sku: str | None = None,
    specs: Mapping[str, Any] | None = None,
) -> list[tuple[str, str]]:
    """Return (code, evidence) audit candidates.

    Never implies governed/canonical identity. Candidates must not be written
    to products.manufacturer_code without a separate Phase 2C authority path.
    """
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(code: str | None, evidence: str) -> None:
        c = (code or "").strip()
        if not c or c in seen:
            return
        seen.add(c)
        out.append((c, evidence))

    specs = specs or {}
    for key in ("manufacturer_code", "part_number", "model", "oem_model", "official_model"):
        val = specs.get(key)
        if isinstance(val, str) and val.strip():
            add(val.strip(), f"specs.{key}")

    text = name or ""
    for rx, label in ((_CODE_LABEL_RE, "name_label"), (_MODEL_LABEL_RE, "name_label")):
        m = rx.search(text)
        if m:
            tail = text[m.end() :].strip()
            token = re.split(r"[،,]", tail, maxsplit=1)[0].strip()
            # Drop trailing Persian prose after the code token group.
            token = re.split(r"\s+برای\s+", token, maxsplit=1)[0].strip()
            token = re.sub(r"\s{2,}", " ", token)
            if token:
                add(token, label)

    if sku and str(sku).strip():
        add(str(sku).strip(), "sku")

    return out


def manufacturer_code_is_governed(
    *,
    manufacturer_code: str | None,
    manufacturer_code_governed: bool,
) -> bool:
    """True only when an explicit governed flag is set for a non-empty code.

    extract_manufacturer_code_candidates() output never satisfies this alone.
    """
    code = (manufacturer_code or "").strip()
    return bool(code) and bool(manufacturer_code_governed)


def lint_product_name_v1(
    name: str | None,
    *,
    brand_raw: str | None = None,
    manufacturer_code: str | None = None,
) -> list[str]:
    """Return reason codes for title quality issues."""
    reasons: list[str] = []
    if name is None or not str(name).strip():
        return ["EMPTY_NAME"]
    if name != name.strip():
        reasons.append("leading_trailing_whitespace")
    if "  " in name:
        reasons.append("repeated_whitespace")
    # Flag Arabic ye/kaf outside the OEM code segment.
    probe = name
    if manufacturer_code and manufacturer_code in probe:
        probe = probe.replace(manufacturer_code, "")
    if _ARABIC_YE in probe or _ARABIC_KE in probe:
        reasons.append("ARABIC_YE_OR_KAF")
    for term in PROHIBITED_TERMS:
        if term in name:
            reasons.append(f"PROHIBITED_TERM:{term}")
    if brand_raw:
        latin, persian = split_bilingual_label(brand_raw)
        if latin and persian and latin in name and persian in name:
            reasons.append("duplicated_brand")
        if "|" in name and latin and persian:
            reasons.append("bilingual_brand_in_title")
    if manufacturer_code:
        compact = manufacturer_code.replace("-", "").replace(" ", "")
        if (
            "-" in manufacturer_code
            and manufacturer_code not in name
            and compact in name.replace("-", "").replace(" ", "")
        ):
            reasons.append("code_normalization_suspected")
    if len(name) > HARD_LENGTH_LIMIT:
        reasons.append("HARD_LENGTH_EXCEEDED")
    elif len(name) > SOFT_LENGTH_TARGET:
        reasons.append("SOFT_LENGTH_EXCEEDED")
    if len(name) < 8:
        reasons.append("title_too_short")
    if "مدل" in name:
        reasons.append("USES_MODEL_LABEL")
    if "|" in name:
        reasons.append("BILINGUAL_BRAND_DUMP")
    return reasons


def compare_product_name_v1(current: str | None, proposed: str | None) -> dict[str, Any]:
    cur_n = normalize_persian_text(current)
    prop_n = normalize_persian_text(proposed)
    equal = bool(prop_n) and cur_n == prop_n
    return {
        "current": current,
        "proposed": proposed,
        "equal": equal,
        "equal_normalized": equal,
        "classification": "EXACT" if equal else "DIFFERS",
        "current_len": len(current or ""),
        "proposed_len": len(proposed or ""),
        "delta_len": len(proposed or "") - len(current or ""),
    }


def _fact_value(facts: Mapping[str, Any] | None, keys: tuple[str, ...]) -> Any:
    if not facts:
        return None
    for k in keys:
        if k in facts and facts[k] not in (None, ""):
            return facts[k]
    return None


def _resolve_range_pair(facts: Mapping[str, Any] | None) -> tuple[Any, Any] | None:
    if not facts:
        return None
    if "range_min_mm" in facts and "range_max_mm" in facts:
        return facts["range_min_mm"], facts["range_max_mm"]
    if "min" in facts and "max" in facts:
        return facts["min"], facts["max"]
    raw = facts.get("measurement_range") or facts.get("range") or facts.get("measuring_range")
    if isinstance(raw, dict) and {"min", "max"} <= set(raw.keys()):
        return raw["min"], raw["max"]
    if isinstance(raw, list | tuple) and len(raw) == 2:
        return raw[0], raw[1]
    if isinstance(raw, str):
        m = _RANGE_IN_SPECS_RE.search(raw.replace("/", " "))
        if m:
            return m.group("min"), m.group("max")
    return None


def _format_variant(key_group: tuple[str, ...], value: Any, facts: Mapping[str, Any] | None) -> str | None:
    if any(k in key_group for k in ("measurement_range", "range", "range_min_mm", "measuring_range")):
        pair = _resolve_range_pair(facts)
        if pair:
            return format_measurement_range_mm(pair[0], pair[1])
        if isinstance(value, dict) and {"min", "max"} <= set(value.keys()):
            return format_measurement_range_mm(value["min"], value["max"])
        if isinstance(value, list | tuple) and len(value) == 2:
            return format_measurement_range_mm(value[0], value[1])
        if isinstance(value, str):
            m = _RANGE_IN_SPECS_RE.search(value.replace("/", " "))
            if m:
                return format_measurement_range_mm(m.group("min"), m.group("max"))

    if "thread_size" in key_group:
        facts = facts or {}
        size = facts.get("thread_size") or value
        pitch = facts.get("thread_pitch")
        if size is not None and pitch is not None:
            return format_metric_thread(size, pitch)
        if isinstance(value, str):
            tm = _THREAD_RE.search(value)
            if tm:
                return format_metric_thread(tm.group("size"), tm.group("pitch"))
            if value.strip().upper().startswith("M"):
                return value.strip()

    if any(k in key_group for k in ("capacity", "capacity_mm")):
        # Prefer capacity wording (no Ø) when capacity facts are present.
        cap = None
        if facts:
            cap = facts.get("capacity_mm")
            if cap is None:
                cap = facts.get("capacity")
        if cap is None and value is not None:
            cap = value
        if isinstance(cap, int | float):
            return f"{_num(cap)} میلی‌متر"
        if isinstance(cap, str) and cap.strip():
            cm = _CAPACITY_MM_RE.search(cap) or re.search(r"(?P<n>\d+(?:\.\d+)?)", cap)
            if cm:
                return f"{_num(cm.group('n'))} میلی‌متر"

    if any(k in key_group for k in ("diameter", "cutting_diameter", "diameter_mm")):
        if isinstance(value, int | float | str) and str(value).strip():
            try:
                float(str(value).replace("mm", "").strip())
                return format_diameter_mm(str(value).replace("mm", "").strip())
            except ValueError:
                pass
        if isinstance(value, str):
            dm = _DIAMETER_RE.search(value)
            if dm:
                return format_diameter_mm(dm.group("d"))

    if "volume" in key_group and value not in (None, ""):
        return f"{_num(value)} لیتر" if not str(value).endswith("لیتر") else str(value)

    if "interface" in key_group and value not in (None, ""):
        return str(value).strip()

    return None


def build_product_name_v1(
    *,
    product_type: str | None = None,
    product_type_fa: str | None = None,
    brand: str | None = None,
    brand_raw: str | None = None,
    manufacturer_code: str | None = None,
    facts: Mapping[str, Any] | None = None,
    naming_profile: str | NamingProfile | None = "generic.v1",
    identity_qualifiers: list[str] | None = None,
    registry_brand: Mapping[str, Any] | None = None,
    brand_registry_row: Mapping[str, Any] | None = None,
    preferred_brand_form: str | None = None,
    current_name: str | None = None,
    product_type_governed: bool = True,
    manufacturer_code_governed: bool = False,
    brand_display_governed: bool | None = None,
    naming_profile_governed: bool | None = None,
    variant_facts_governed: bool = False,
    identity_qualifiers_governed: bool = False,
    governance: NamingGovernanceContext | None = None,
    profile_resolution: str | None = None,
) -> NamingResult:
    """Build a deterministic display name or HOLD.

    HIGH requires every input used in the title to be governed. Defaults keep
    manufacturer_code_governed=False so heuristic OEM candidates cannot reach HIGH.
    generic.v1 never yields HIGH (naming_profile_not_governed).
    """
    if isinstance(naming_profile, NamingProfile):
        profile = naming_profile
        profile_code = profile.code
    else:
        profile_code = naming_profile or "generic.v1"
        profile = PROFILES.get(profile_code, PROFILES["generic.v1"])

    warnings: list[str] = []
    used: list[str] = []
    omitted: list[str] = []
    reasons: list[str] = []

    if governance is not None:
        product_type_governed = governance.product_type_governed
        manufacturer_code_governed = governance.manufacturer_code_governed
        brand_gov = governance.brand_display_governed
        profile_gov = governance.naming_profile_governed
        variant_gov = governance.variant_facts_governed
        qual_gov = governance.identity_qualifiers_governed
    else:
        brand_gov = (
            brand_display_governed
            if brand_display_governed is not None
            else False
        )
        profile_gov = (
            naming_profile_governed
            if naming_profile_governed is not None
            else False
        )
        variant_gov = variant_facts_governed
        qual_gov = identity_qualifiers_governed

    # generic.v1 is never a governed profile for automatic rename.
    if profile.code == "generic.v1":
        profile_gov = False
        if profile_resolution is None:
            profile_resolution = PROFILE_MISSING

    pt = normalize_persian_text(product_type_fa if product_type_fa is not None else product_type)
    brand_in = brand_raw if brand_raw is not None else brand
    registry = brand_registry_row if brand_registry_row is not None else registry_brand
    preferred = preferred_brand_form
    if preferred is None and profile.brand_policy == "prefer_en":
        preferred = "en"
    elif preferred is None and profile.brand_policy == "prefer_fa":
        preferred = "fa"

    brand_token = brand_display_for_title(
        brand_in,
        preferred_form=preferred,
        registry_row=registry,
    )
    code = (manufacturer_code or "").strip()

    gov_snapshot = NamingGovernanceContext(
        product_type_governed=bool(product_type_governed),
        manufacturer_code_governed=bool(manufacturer_code_governed),
        brand_display_governed=bool(brand_gov),
        naming_profile_governed=bool(profile_gov),
        variant_facts_governed=bool(variant_gov),
        identity_qualifiers_governed=bool(qual_gov),
    ).as_dict()

    if profile.product_type_required and not pt:
        return NamingResult(
            name=None,
            confidence="none",
            warnings=warnings,
            used_fields=used,
            omitted_fields=omitted,
            profile=profile.code,
            state="HOLD_MISSING_PRODUCT_TYPE",
            reason_codes=["missing_product_type"],
            governance=gov_snapshot,
            profile_resolution=profile_resolution,
        )
    if profile.brand_required and not brand_token:
        return NamingResult(
            name=None,
            confidence="none",
            warnings=warnings,
            used_fields=used,
            omitted_fields=omitted,
            profile=profile.code,
            state="HOLD_MISSING_BRAND",
            reason_codes=["missing_brand"],
            governance=gov_snapshot,
            profile_resolution=profile_resolution,
        )
    if profile.manufacturer_code_required and not code:
        return NamingResult(
            name=None,
            confidence="none",
            warnings=warnings,
            used_fields=used,
            omitted_fields=omitted,
            profile=profile.code,
            state="HOLD_MISSING_MANUFACTURER_CODE",
            reason_codes=["missing_manufacturer_code"],
            governance=gov_snapshot,
            profile_resolution=profile_resolution,
        )

    # Preserve OEM code exactly — never run Persian normalization on it.
    parts: list[str] = [pt]
    used.append("product_type_fa")
    if identity_qualifiers and profile.allow_identity_qualifiers:
        for q in identity_qualifiers:
            qn = normalize_persian_text(q)
            if qn and qn not in pt:
                parts.append(qn)
                used.append("identity_qualifier")
    parts.append(brand_token)
    used.append("brand_display")
    parts.append(OEM_LABEL_FA)
    parts.append(code)
    used.append("manufacturer_code")

    variant_bits: list[str] = []
    facts = facts or {}
    if profile.max_variant_attributes > 0 and profile.primary_variant_fact_keys:
        # Treat the profile key group as one attribute slot family.
        key_group = profile.primary_variant_fact_keys
        raw = _fact_value(facts, key_group)
        formatted = _format_variant(key_group, raw, facts)
        if formatted:
            variant_bits.append(formatted)
            used.append(f"fact:{key_group[0]}")
        else:
            for key in key_group:
                omitted.append(key)
            # surface noise omissions for generic callers
            for extra_key in facts:
                if extra_key not in key_group and extra_key not in (
                    "range_max_mm",
                    "thread_pitch",
                    "measuring_range",
                ):
                    omitted.append(extra_key)
                    warnings.append(f"OMITTED_NOISE:{extra_key}")

    elif profile.code == "generic.v1":
        for extra_key in facts:
            omitted.append(extra_key)
            warnings.append(f"OMITTED_NOISE:{extra_key}")

    if (
        profile.variant_required
        and profile.primary_variant_fact_keys
        and profile.max_variant_attributes > 0
        and not variant_bits
    ):
        return NamingResult(
            name=None,
            confidence="none",
            warnings=warnings,
            used_fields=used,
            omitted_fields=omitted,
            profile=profile.code,
            state="HOLD_MISSING_VARIANT_ATTRIBUTE",
            reason_codes=["missing_primary_variant_attribute"],
            governance=gov_snapshot,
            profile_resolution=profile_resolution,
        )

    head = " ".join(parts)
    name = head
    if variant_bits:
        name = f"{head}، {'، '.join(variant_bits)}"

    if len(name) > HARD_LENGTH_LIMIT:
        return NamingResult(
            name=None,
            confidence="none",
            warnings=["would_exceed_hard_length"],
            used_fields=used,
            omitted_fields=omitted,
            profile=profile.code,
            state="HOLD_NAME_TOO_LONG",
            reason_codes=["proposed_name_too_long"],
            governance=gov_snapshot,
            profile_resolution=profile_resolution,
        )

    lint = lint_product_name_v1(name, brand_raw=brand_in, manufacturer_code=code)
    warnings.extend(
        [
            c
            for c in lint
            if c.startswith("exceeds_")
            or c in {"SOFT_LENGTH_EXCEEDED", "HARD_LENGTH_EXCEEDED"}
        ]
    )

    oem_governed = manufacturer_code_is_governed(
        manufacturer_code=code,
        manufacturer_code_governed=manufacturer_code_governed,
    )
    used_variant = any(u.startswith("fact:") for u in used)
    used_qualifier = "identity_qualifier" in used

    if not product_type_governed:
        reasons.append("product_type_not_fk_verified")
    if not oem_governed:
        reasons.append("manufacturer_code_not_governed")
        if manufacturer_code_governed and not code:
            warnings.append("manufacturer_code_governed_without_code")
        elif not manufacturer_code_governed:
            warnings.append("manufacturer_identity_ungoverned")
    if not brand_gov:
        reasons.append("brand_display_not_governed")
        warnings.append("brand_display_ungoverned")
    if not profile_gov:
        reasons.append("naming_profile_not_governed")
        warnings.append("naming_profile_ungoverned")
    if used_variant and not variant_gov:
        reasons.append("variant_facts_not_governed")
        warnings.append("variant_facts_ungoverned")
    if used_qualifier and not qual_gov:
        reasons.append("identity_qualifiers_not_governed")
        warnings.append("identity_qualifiers_ungoverned")

    # HIGH only when every input used in the generated title is governed.
    high_ok = (
        bool(product_type_governed)
        and oem_governed
        and bool(brand_gov)
        and bool(profile_gov)
        and (bool(variant_gov) if used_variant else True)
        and (bool(qual_gov) if used_qualifier else True)
    )
    confidence = "high" if high_ok else "medium"

    # Refresh snapshot after effective generic-profile demotion.
    gov_snapshot = NamingGovernanceContext(
        product_type_governed=bool(product_type_governed),
        manufacturer_code_governed=oem_governed,
        brand_display_governed=bool(brand_gov),
        naming_profile_governed=bool(profile_gov),
        variant_facts_governed=bool(variant_gov),
        identity_qualifiers_governed=bool(qual_gov),
    ).as_dict()

    if current_name and compare_product_name_v1(current_name, name)["equal"]:
        return NamingResult(
            name=name,
            confidence=confidence,
            warnings=warnings,
            used_fields=used,
            omitted_fields=omitted,
            profile=profile.code,
            state="EXACT",
            reason_codes=reasons + ["matches_current"],
            governance=gov_snapshot,
            profile_resolution=profile_resolution,
        )

    return NamingResult(
        name=name,
        confidence=confidence,
        warnings=warnings
        + (["pt_fk_unverified"] if not product_type_governed else [])
        + (["oem_identity_ungoverned"] if not oem_governed else []),
        used_fields=used,
        omitted_fields=omitted,
        profile=profile.code,
        state="RENAME_SAFE",
        reason_codes=reasons + ["structured_proposal"],
        governance=gov_snapshot,
        profile_resolution=profile_resolution,
    )
