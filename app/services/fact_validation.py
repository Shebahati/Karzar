"""Fact value / unit / constraint validation (Prompt 12).

Consumes Property Dictionary datatypes and PT-W2 narrowing override keys.
Does not write Facts or touch products.specifications.
"""

from __future__ import annotations

from typing import Any

from fastapi import status

from app.core.errors import ErrorCode, api_error
from app.db.models.knowledge import KnowledgePropertyDefinition, KnowledgeUnit
from app.db.models.product_type import (
    LENGTH_BOUND_DATA_TYPES,
    NUMERIC_BOUND_DATA_TYPES,
)
from app.services.product_type_definition_service import _canonical_enum_codes


def _fail(field: str, message: str, *, code: str | ErrorCode = ErrorCode.VALIDATION_FAILED) -> None:
    raise api_error(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        error_code=code,
        message=message,
        details=[{"field": field, "message": message}],
    )


def _is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int | float)


def validate_fact_value_shape(data_type: str, value: Any) -> Any:
    """Validate and return normalized Fact value for the Property data_type."""
    if data_type == "boolean":
        if not isinstance(value, bool):
            _fail("value", "boolean Fact requires a JSON boolean")
        return value

    if data_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            _fail("value", "integer Fact requires an integer (not bool/float)")
        return value

    if data_type == "number":
        if not _is_number(value):
            _fail("value", "number Fact requires a numeric value (not bool)")
        return float(value) if isinstance(value, float) else value

    if data_type == "quantity":
        if not isinstance(value, dict):
            _fail("value", "quantity Fact requires {magnitude, qualifier?}")
        if "magnitude" not in value:
            _fail("value.magnitude", "quantity.magnitude required")
        if not _is_number(value["magnitude"]):
            _fail("value.magnitude", "quantity.magnitude must be numeric")
        out: dict[str, Any] = {"magnitude": value["magnitude"]}
        if "qualifier" in value and value["qualifier"] is not None:
            if not isinstance(value["qualifier"], str):
                _fail("value.qualifier", "quantity.qualifier must be a string")
            out["qualifier"] = value["qualifier"]
        extras = set(value) - {"magnitude", "qualifier"}
        if extras:
            _fail("value", f"unknown quantity keys: {sorted(extras)}")
        return out

    if data_type == "range":
        if not isinstance(value, dict):
            _fail("value", "range Fact requires {min, max}")
        if "min" not in value or "max" not in value:
            _fail("value", "range requires min and max")
        if not _is_number(value["min"]) or not _is_number(value["max"]):
            _fail("value", "range min/max must be numeric")
        if float(value["min"]) > float(value["max"]):
            _fail("value", "range min must be <= max")
        extras = set(value) - {"min", "max"}
        if extras:
            _fail("value", f"unknown range keys: {sorted(extras)}")
        return {"min": value["min"], "max": value["max"]}

    if data_type == "enum":
        if not isinstance(value, str) or not value:
            _fail("value", "enum Fact requires a non-empty string code")
        return value

    if data_type == "string":
        if not isinstance(value, str):
            _fail("value", "string Fact requires a string")
        return value

    if data_type == "string_array":
        if not isinstance(value, list) or not all(isinstance(i, str) for i in value):
            _fail("value", "string_array Fact requires an array of strings")
        return value

    if data_type in ("ref_standard", "ref_document"):
        # Target rows do not exist yet — accept non-empty string reference id.
        if not isinstance(value, str) or not value.strip():
            _fail("value", f"{data_type} Fact requires a non-empty string reference id")
        return value.strip()

    _fail("value", f"unsupported data_type '{data_type}'")


def _numeric_probe(data_type: str, value: Any) -> float | None:
    if data_type in ("integer", "number"):
        return float(value)
    if data_type == "quantity" and isinstance(value, dict):
        return float(value["magnitude"])
    if data_type == "range" and isinstance(value, dict):
        # Both ends must satisfy bounds.
        return None
    return None


def _as_bound_number(raw: Any, *, field: str) -> float:
    if not _is_number(raw):
        _fail("validation", f"canonical validation.{field} must be numeric")
    return float(raw)


def _resolve_lower_bound(canon: dict[str, Any]) -> tuple[float, bool] | None:
    """Return (bound, exclusive) using the strictest lower constraint."""
    candidates: list[tuple[float, bool]] = []
    if "min" in canon and canon["min"] is not None:
        candidates.append((_as_bound_number(canon["min"], field="min"), False))
    if "exclusive_min" in canon and canon["exclusive_min"] is not None:
        candidates.append(
            (_as_bound_number(canon["exclusive_min"], field="exclusive_min"), True)
        )
    if not candidates:
        return None
    best = candidates[0]
    for cand in candidates[1:]:
        if cand[0] > best[0] or (cand[0] == best[0] and cand[1] and not best[1]):
            best = cand
    return best


def _resolve_upper_bound(canon: dict[str, Any]) -> tuple[float, bool] | None:
    """Return (bound, exclusive) using the strictest upper constraint."""
    candidates: list[tuple[float, bool]] = []
    if "max" in canon and canon["max"] is not None:
        candidates.append((_as_bound_number(canon["max"], field="max"), False))
    if "exclusive_max" in canon and canon["exclusive_max"] is not None:
        candidates.append(
            (_as_bound_number(canon["exclusive_max"], field="exclusive_max"), True)
        )
    if not candidates:
        return None
    best = candidates[0]
    for cand in candidates[1:]:
        if cand[0] < best[0] or (cand[0] == best[0] and cand[1] and not best[1]):
            best = cand
    return best


def _assert_bounds_consistent(
    lower: tuple[float, bool] | None,
    upper: tuple[float, bool] | None,
) -> None:
    if lower is None or upper is None:
        return
    lo, lo_ex = lower
    hi, hi_ex = upper
    if lo > hi:
        _fail(
            "validation",
            f"canonical lower/upper bounds contradict (lower={lo}, upper={hi})",
        )
    if lo == hi and (lo_ex or hi_ex):
        _fail(
            "validation",
            "canonical exclusive bounds leave an empty numeric domain",
        )


def _check_probe_against_bounds(
    probe: float,
    *,
    lower: tuple[float, bool] | None,
    upper: tuple[float, bool] | None,
) -> None:
    if lower is not None:
        bound, exclusive = lower
        if exclusive:
            if probe <= bound:
                _fail("value", f"value {probe} must be > exclusive_min={bound}")
        elif probe < bound:
            _fail("value", f"value {probe} below effective min={bound}")
    if upper is not None:
        bound, exclusive = upper
        if exclusive:
            if probe >= bound:
                _fail("value", f"value {probe} must be < exclusive_max={bound}")
        elif probe > bound:
            _fail("value", f"value {probe} above effective max={bound}")


def apply_bound_constraints(
    *,
    data_type: str,
    value: Any,
    canonical_validation: dict[str, Any],
    overrides: dict[str, Any] | None,
) -> None:
    """Apply canonical Property constraints then PT-W2 narrowing overrides.

    Canonical operators: min, max, exclusive_min, exclusive_max.
    PT-W2 override operators remain: min, max (narrowing only; no exclusive_*).
    """
    overrides = overrides if isinstance(overrides, dict) else {}
    canon = canonical_validation if isinstance(canonical_validation, dict) else {}

    if data_type in NUMERIC_BOUND_DATA_TYPES:
        lower = _resolve_lower_bound(canon)
        upper = _resolve_upper_bound(canon)
        _assert_bounds_consistent(lower, upper)

        # PT-W2 min/max further narrow (intersection). exclusive_* not overridable.
        if "min" in overrides and overrides["min"] is not None:
            ov_min = float(overrides["min"])
            if lower is None:
                lower = (ov_min, False)
            else:
                lo, _lo_ex = lower
                if ov_min > lo:
                    lower = (ov_min, False)
                # ov_min == lo with exclusive lower: keep exclusive (stricter)
        if "max" in overrides and overrides["max"] is not None:
            ov_max = float(overrides["max"])
            if upper is None:
                upper = (ov_max, False)
            else:
                hi, _hi_ex = upper
                if ov_max < hi:
                    upper = (ov_max, False)
                # ov_max == hi with exclusive upper: keep exclusive (stricter)

        _assert_bounds_consistent(lower, upper)

        probes: list[float] = []
        if data_type == "range" and isinstance(value, dict):
            probes = [float(value["min"]), float(value["max"])]
        else:
            probe = _numeric_probe(data_type, value)
            if probe is not None:
                probes = [probe]

        for probe in probes:
            _check_probe_against_bounds(probe, lower=lower, upper=upper)

    if data_type in LENGTH_BOUND_DATA_TYPES:
        eff_min_len = canon.get("min_length")
        eff_max_len = canon.get("max_length")
        if "min_length" in overrides:
            eff_min_len = overrides["min_length"]
        if "max_length" in overrides:
            eff_max_len = overrides["max_length"]

        lengths: list[int] = []
        if data_type == "string" and isinstance(value, str):
            lengths = [len(value)]
        elif data_type == "string_array" and isinstance(value, list):
            lengths = [len(s) for s in value]

        for length in lengths:
            if eff_min_len is not None and length < int(eff_min_len):
                _fail("value", f"length {length} below effective min_length={eff_min_len}")
            if eff_max_len is not None and length > int(eff_max_len):
                _fail("value", f"length {length} above effective max_length={eff_max_len}")


def apply_qualifier_constraints(
    *,
    data_type: str,
    value: Any,
    canonical_validation: dict[str, Any],
) -> None:
    """Enforce allow_qualifier allowlist from canonical Property validation.

    Presence of allow_qualifier does not require a qualifier; when present, the
    qualifier must be a member of the Property-defined allowlist.
    """
    if data_type != "quantity" or not isinstance(value, dict):
        return
    canon = canonical_validation if isinstance(canonical_validation, dict) else {}
    if "allow_qualifier" not in canon:
        return
    allowed = canon["allow_qualifier"]
    if not isinstance(allowed, list) or not all(isinstance(i, str) for i in allowed):
        _fail(
            "validation.allow_qualifier",
            "canonical allow_qualifier must be a list of strings",
        )
    if "qualifier" not in value or value["qualifier"] is None:
        return
    qualifier = value["qualifier"]
    if qualifier not in allowed:
        _fail(
            "value.qualifier",
            f"qualifier {qualifier!r} not in allow_qualifier={allowed}",
        )


def apply_enum_constraints(
    property_definition: KnowledgePropertyDefinition,
    value: str,
    overrides: dict[str, Any] | None,
) -> None:
    overrides = overrides if isinstance(overrides, dict) else {}
    codes = _canonical_enum_codes(property_definition.enum_values)
    if "enum_subset" in overrides:
        subset = overrides["enum_subset"]
        if not isinstance(subset, list):
            _fail("validation_overrides.enum_subset", "must be a list")
        codes = set(subset)
    if value not in codes:
        _fail("value", f"enum code '{value}' not in allowed set {sorted(codes)}")


def normalize_fact_unit(
    *,
    property_definition: KnowledgePropertyDefinition,
    unit_input: str | None,
    units: list[KnowledgeUnit],
    for_publish: bool,
) -> str | None:
    """Resolve Fact unit to an active canonical code for the Property dimension."""
    dimension = property_definition.unit_dimension
    if not dimension:
        if unit_input:
            _fail("unit", "Property is dimensionless; unit must be omitted")
        return None

    active = [u for u in units if u.dimension == dimension and u.status == "active"]
    if for_publish:
        candidates = active
    else:
        # Asserted: allow active units only (draft/deprecated rejected for writes).
        candidates = active

    by_canonical = {u.canonical_code: u for u in candidates}
    alias_to_canonical: dict[str, str] = {}
    for u in candidates:
        alias_to_canonical[u.canonical_code.casefold()] = u.canonical_code
        for alias in u.aliases or []:
            if isinstance(alias, str) and alias.strip():
                alias_to_canonical[alias.strip().casefold()] = u.canonical_code

    if unit_input is None or not str(unit_input).strip():
        default = property_definition.default_unit
        if default and default in by_canonical:
            return default
        _fail("unit", f"unit required for dimension '{dimension}'")

    key = str(unit_input).strip()
    resolved = alias_to_canonical.get(key.casefold())
    if resolved is None:
        # Wrong dimension / unknown / non-active
        _fail(
            "unit",
            f"unit '{key}' is not an active canonical/alias unit for dimension '{dimension}'",
        )
    return resolved


def validate_fact_payload(
    *,
    property_definition: KnowledgePropertyDefinition,
    value: Any,
    unit: str | None,
    units: list[KnowledgeUnit],
    overrides: dict[str, Any] | None,
    for_publish: bool,
) -> tuple[Any, str | None]:
    """Full datatype + constraint + unit validation. Returns (value, unit)."""
    if property_definition.status != "active":
        _fail(
            "definition_id",
            f"Property Definition status must be active (got '{property_definition.status}')",
        )
    normalized = validate_fact_value_shape(property_definition.data_type, value)
    apply_bound_constraints(
        data_type=property_definition.data_type,
        value=normalized,
        canonical_validation=property_definition.validation or {},
        overrides=overrides,
    )
    apply_qualifier_constraints(
        data_type=property_definition.data_type,
        value=normalized,
        canonical_validation=property_definition.validation or {},
    )
    if property_definition.data_type == "enum":
        apply_enum_constraints(property_definition, normalized, overrides)
    resolved_unit = normalize_fact_unit(
        property_definition=property_definition,
        unit_input=unit,
        units=units,
        for_publish=for_publish,
    )
    return normalized, resolved_unit
