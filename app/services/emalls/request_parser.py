"""Parse Emalls extraction requests across JSON, form, and query params.

Mirrors WP_REST_Request::get_param resolution used by the official Emalls
WordPress plugin (JSON body, application/x-www-form-urlencoded, and query).
Never logs the raw body or token.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import Request
from pydantic import ValidationError
from starlette import status

from app.core.errors import ErrorCode, api_error
from app.schemas.emalls import EmallsProductsRequest

_JSON_TYPES = {"application/json", "application/vnd.api+json"}
_FORM_TYPES = {
    "application/x-www-form-urlencoded",
    "multipart/form-data",
}


def _content_type_base(request: Request) -> str:
    return (request.headers.get("content-type") or "").split(";", 1)[0].strip().lower()


def _merge_param(target: dict[str, Any], key: str, value: Any) -> None:
    if value is None:
        return
    target[key] = value


def _overlay_mapping(raw: dict[str, Any], mapping: dict[str, Any]) -> None:
    for key, value in mapping.items():
        _merge_param(raw, str(key), value)


async def extract_emalls_raw_params(request: Request) -> dict[str, Any]:
    """Collect Emalls params: query first, then body overlays (WP-compatible)."""
    raw: dict[str, Any] = {}
    for key, value in request.query_params.multi_items():
        _merge_param(raw, key, value)

    content_type = _content_type_base(request)

    if content_type in _JSON_TYPES:
        body = await request.body()
        if not body:
            return raw
        try:
            parsed = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="Request validation failed",
                details=[{"field": "body", "message": "invalid JSON body"}],
            ) from exc
        if not isinstance(parsed, dict):
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="Request validation failed",
                details=[{"field": "body", "message": "JSON body must be an object"}],
            )
        _overlay_mapping(raw, parsed)
        return raw

    if content_type in _FORM_TYPES or content_type == "":
        # Official Emalls crawler posts form-urlencoded; empty CT still allows form/query.
        try:
            form = await request.form()
        except Exception as exc:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="Request validation failed",
                details=[{"field": "body", "message": "invalid form body"}],
            ) from exc
        for key, value in form.multi_items():
            if hasattr(value, "filename") and hasattr(value, "file"):
                continue
            _merge_param(raw, str(key), value)
        return raw

    raise api_error(
        status.HTTP_422_UNPROCESSABLE_CONTENT,
        error_code=ErrorCode.VALIDATION_FAILED,
        message="Request validation failed",
        details=[
            {
                "field": "content-type",
                "message": (
                    "must be application/json or application/x-www-form-urlencoded"
                ),
            }
        ],
    )


def validate_emalls_products_request(raw: dict[str, Any]) -> EmallsProductsRequest:
    """Validate extracted params through the shared Pydantic contract."""
    try:
        return EmallsProductsRequest.model_validate(raw)
    except ValidationError as exc:
        details = []
        for err in exc.errors():
            loc = err.get("loc") or ()
            field = ".".join(str(part) for part in loc if part != "body") or None
            details.append({"field": field, "message": err.get("msg", "Invalid value")})
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Request validation failed",
            details=details,
        ) from exc


async def parse_emalls_products_request(request: Request) -> EmallsProductsRequest:
    """FastAPI dependency: parse JSON/form/query Emalls params, then validate."""
    raw = await extract_emalls_raw_params(request)
    return validate_emalls_products_request(raw)
