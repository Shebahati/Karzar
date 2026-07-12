"""JSONB specification filter builders for product list queries."""

import json
from typing import Any

from fastapi import Request
from sqlalchemy import ColumnElement, String, cast, func

from app.core.errors import ErrorCode, api_error
from app.db.models.product import Product


def _json_path_accessor(path: str):
    """Resolve a dot-separated path into a chained SQLAlchemy JSON accessor."""
    parts = [part.strip() for part in path.split(".") if part.strip()]
    if not parts:
        raise ValueError("Filter path cannot be empty")

    accessor = Product.specifications
    for part in parts[:-1]:
        accessor = accessor[part]
    return accessor[parts[-1]]


def _sqlite_json_path(path: str) -> str:
    return "$." + path


def _coerce_filter_value(raw_value: Any) -> Any:
    """Normalize string booleans from query parameters to Python bools."""
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        lowered = raw_value.strip().lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
    return raw_value


def build_specification_filters(
    spec_filters: dict[str, Any],
    *,
    dialect_name: str = "postgresql",
) -> list[ColumnElement[bool]]:
    """Translate a spec filter dict into SQLAlchemy WHERE clauses.

    Supports exact match and ``__icontains`` suffix for case-insensitive search.
    PostgreSQL uses JSONB ``astext``; SQLite uses ``json_extract`` for tests.
    """
    conditions: list[ColumnElement[bool]] = []
    use_sqlite = dialect_name == "sqlite"

    for raw_path, raw_value in spec_filters.items():
        icontains = False
        path = raw_path.strip()
        if not path:
            raise ValueError("Filter path cannot be empty")

        if path.endswith("__icontains"):
            icontains = True
            path = path[: -len("__icontains")].strip()
            if not path:
                raise ValueError("Filter path cannot be empty")

        value = _coerce_filter_value(raw_value)

        if use_sqlite:
            json_path = _sqlite_json_path(path)
            extracted = func.json_extract(Product.specifications, json_path)
            if icontains:
                conditions.append(cast(extracted, String).ilike(f"%{value}%"))
            elif isinstance(value, bool):
                conditions.append(extracted == value)
            else:
                conditions.append(cast(extracted, String) == str(value))
            continue

        accessor = _json_path_accessor(path)
        if icontains:
            conditions.append(accessor.astext.ilike(f"%{value}%"))
        elif isinstance(value, bool):
            conditions.append(accessor.astext == str(value).lower())
        else:
            conditions.append(accessor.astext == str(value))

    return conditions


def parse_filters_query_param(filters: str | None) -> dict[str, Any]:
    """Parse the ``filters`` JSON query parameter into a flat dict."""
    if not filters:
        return {}
    try:
        parsed = json.loads(filters)
    except json.JSONDecodeError as exc:
        raise api_error(
            400,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Invalid filters JSON",
            details=[{"field": "filters", "message": str(exc)}],
        ) from exc

    if not isinstance(parsed, dict):
        raise api_error(
            400,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="filters must be a JSON object",
            details=[{"field": "filters", "message": "Expected an object"}],
        )
    return parsed


def parse_spec_prefixed_params(request: Request) -> dict[str, Any]:
    """Parse ``spec_``-prefixed query params into dot-notation filter paths.

    Examples:
        spec_brand=insize  ->  {"brand": "insize"}
        spec_technical_specs__range=0-150mm  ->  {"technical_specs.range": "0-150mm"}
    """
    spec_filters: dict[str, Any] = {}
    for key, value in request.query_params.multi_items():
        if not key.startswith("spec_"):
            continue
        path = key[5:].replace("__", ".")
        if not path:
            raise api_error(
                400,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="Invalid spec filter key",
                details=[{"field": key, "message": "Spec filter path cannot be empty"}],
            )
        spec_filters[path] = value
    return spec_filters


def merge_spec_filters(
    *,
    filters_json: str | None,
    request: Request,
) -> dict[str, Any]:
    """Combine JSON ``filters`` param with ``spec_``-prefixed query params."""
    merged: dict[str, Any] = {}
    merged.update(parse_filters_query_param(filters_json))
    merged.update(parse_spec_prefixed_params(request))
    return merged
