"""Normalize product specifications between DB storage and API response shapes.

Contract (intentional dual shape):
- DB / admin write path: nested dicts via ``specifications_for_storage``
- Admin API responses: dict maps for technical_specs / dimensions
- Storefront API responses: arrays of {key, value} items for filters/UI
"""

from typing import Any


def _dict_to_spec_items(data: Any) -> list[dict[str, str]]:
    if not isinstance(data, dict):
        return []
    items: list[dict[str, str]] = []
    for key, value in data.items():
        if value is None:
            continue
        items.append({"key": str(key), "value": str(value)})
    return items


def normalize_specifications_for_api(
    specs: dict[str, Any] | None,
    *,
    audience: str = "storefront",
) -> dict[str, Any]:
    """Return API shape for specifications; arrays for storefront, dicts for admin."""
    if not specs:
        empty = {"technical_specs": [] if audience == "storefront" else {}, "dimensions": [] if audience == "storefront" else {}, "features": {}}
        return empty

    specs = dict(specs)
    technical = specs.get("technical_specs")
    if isinstance(technical, list):
        if audience == "storefront":
            technical_specs = [
                {"key": str(row.get("key", "")), "value": str(row.get("value", ""))}
                for row in technical
                if isinstance(row, dict)
            ]
        else:
            technical_specs = {
                str(row.get("key", "")): row.get("value")
                for row in technical
                if isinstance(row, dict) and row.get("key")
            }
    elif isinstance(technical, dict):
        if audience == "storefront":
            technical_specs = _dict_to_spec_items(technical)
        else:
            technical_specs = {str(k): v for k, v in technical.items()}
    else:
        technical_specs = [] if audience == "storefront" else {}

    dimensions_raw = specs.get("dimensions")
    if isinstance(dimensions_raw, list):
        if audience == "storefront":
            dimensions = [
                {"key": str(row.get("key", "")), "value": str(row.get("value", ""))}
                for row in dimensions_raw
                if isinstance(row, dict)
            ]
        else:
            dimensions = {
                str(row.get("key", "")): row.get("value")
                for row in dimensions_raw
                if isinstance(row, dict) and row.get("key")
            }
    elif isinstance(dimensions_raw, dict):
        if audience == "storefront":
            dimensions = _dict_to_spec_items(dimensions_raw)
        else:
            dimensions = {str(k): v for k, v in dimensions_raw.items()}
    else:
        dimensions = [] if audience == "storefront" else {}

    features_raw = specs.get("features")
    if isinstance(features_raw, dict):
        features = {
            str(key): value
            for key, value in features_raw.items()
            if isinstance(value, bool | str | int | float)
        }
    else:
        features = {}

    result = {
        "technical_specs": technical_specs,
        "dimensions": dimensions,
        "features": features,
    }
    known = {"technical_specs", "dimensions", "features", "optional_accessories"}
    for key, value in specs.items():
        if key not in known:
            result[key] = value
    return result


def specifications_for_storage(specs: dict[str, Any] | None) -> dict[str, Any]:
    """Accept either nested dict or array form from admin; persist nested dict."""
    specs = dict(specs or {})
    normalized = normalize_specifications_for_api(specs, audience="admin")

    technical_specs = normalized["technical_specs"] if isinstance(normalized["technical_specs"], dict) else {
        row["key"]: row["value"] for row in normalized["technical_specs"] if row.get("key")
    }
    dimensions = normalized["dimensions"] if isinstance(normalized["dimensions"], dict) else {
        row["key"]: row["value"] for row in normalized["dimensions"] if row.get("key")
    }

    result = {
        "technical_specs": technical_specs,
        "dimensions": dimensions,
        "features": normalized["features"],
        "optional_accessories": specs.get("optional_accessories", []),
    }
    known = {"technical_specs", "dimensions", "features", "optional_accessories"}
    for key, value in specs.items():
        if key not in known:
            result[key] = value
    return result
