"""Canonical Property validation operators for Fact runtime (P1 readiness)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from app.services.fact_validation import validate_fact_payload
from fastapi import HTTPException


def _prop(
    *,
    data_type: str,
    validation: dict[str, Any],
    unit_dimension: str | None = "length",
    default_unit: str | None = "mm",
) -> Any:
    return SimpleNamespace(
        status="active",
        data_type=data_type,
        validation=validation,
        unit_dimension=unit_dimension,
        default_unit=default_unit,
        enum_values=None,
    )


def _unit(code: str = "mm", dimension: str = "length") -> Any:
    return SimpleNamespace(
        dimension=dimension,
        canonical_code=code,
        aliases=["میلی‌متر", "mm"],
        status="active",
    )


def _validate(prop, value, unit="mm", overrides=None):
    return validate_fact_payload(
        property_definition=prop,
        value=value,
        unit=unit,
        units=[_unit()],
        overrides=overrides,
        for_publish=False,
    )


def test_resolution_exclusive_min_rejects_zero_and_negative():
    prop = _prop(
        data_type="number",
        validation={"type": "number", "exclusive_min": 0},
    )
    with pytest.raises(HTTPException) as neg:
        _validate(prop, -0.01)
    assert neg.value.status_code == 422

    with pytest.raises(HTTPException) as zero:
        _validate(prop, 0)
    assert zero.value.status_code == 422

    normalized, unit = _validate(prop, 0.01)
    assert normalized == 0.01
    assert unit == "mm"


def test_accuracy_allow_qualifier_from_canonical_validation():
    prop = _prop(
        data_type="quantity",
        validation={
            "type": "quantity",
            "allow_qualifier": ["±", "+", "-", "approx", "max"],
        },
    )
    ok, unit = _validate(prop, {"magnitude": 0.02, "qualifier": "±"})
    assert ok == {"magnitude": 0.02, "qualifier": "±"}
    assert unit == "mm"

    with pytest.raises(HTTPException) as bad:
        _validate(prop, {"magnitude": 0.02, "qualifier": "foo"})
    assert bad.value.status_code == 422

    # allow_qualifier is an allowlist, not a required-presence rule
    no_q, _ = _validate(prop, {"magnitude": 0.02})
    assert no_q == {"magnitude": 0.02}


def test_combined_canonical_bounds_use_strictest_lower():
    prop = _prop(
        data_type="number",
        validation={"min": 0, "exclusive_min": 5},
    )
    with pytest.raises(HTTPException):
        _validate(prop, 5)
    normalized, _ = _validate(prop, 5.1)
    assert normalized == 5.1


def test_contradictory_canonical_bounds_fail():
    prop = _prop(
        data_type="number",
        validation={"exclusive_min": 10, "max": 10},
    )
    with pytest.raises(HTTPException) as exc:
        _validate(prop, 10.1)
    assert exc.value.status_code == 422


def test_pt_w2_min_override_still_narrows_without_exclusive_override_keys():
    prop = _prop(
        data_type="number",
        validation={"min": 0, "max": 100},
    )
    with pytest.raises(HTTPException):
        _validate(prop, 5, overrides={"min": 10})
    normalized, _ = _validate(prop, 10, overrides={"min": 10})
    assert normalized == 10


def test_insize_core_payloads_pass_seed_semantics():
    """Reviewed INSIZE 1108-150 core Fact shapes against seed validation."""
    range_prop = _prop(
        data_type="range",
        validation={
            "type": "range",
            "min_inclusive": True,
            "max_inclusive": True,
            "require_min_le_max": True,
        },
    )
    resolution_prop = _prop(
        data_type="number",
        validation={"type": "number", "exclusive_min": 0},
    )
    accuracy_prop = _prop(
        data_type="quantity",
        validation={
            "type": "quantity",
            "allow_qualifier": ["±", "+", "-", "approx", "max"],
        },
    )

    r, u = _validate(range_prop, {"min": 0, "max": 150})
    assert r == {"min": 0, "max": 150} and u == "mm"

    res, u = _validate(resolution_prop, 0.01)
    assert res == 0.01 and u == "mm"

    acc, u = _validate(accuracy_prop, {"magnitude": 0.02, "qualifier": "±"})
    assert acc == {"magnitude": 0.02, "qualifier": "±"} and u == "mm"

    with pytest.raises(HTTPException) as zero_res:
        _validate(resolution_prop, 0)
    assert zero_res.value.status_code == 422
