from enum import Enum
from typing import Any, List, Optional, Union

from fastapi import HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.schemas.errors import ErrorDetail


class ErrorCode(str, Enum):
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    STEP_UP_REQUIRED = "STEP_UP_REQUIRED"
    STEP_UP_INVALID = "STEP_UP_INVALID"
    STEP_UP_MISMATCH = "STEP_UP_MISMATCH"
    STEP_UP_NOT_CONFIGURED = "STEP_UP_NOT_CONFIGURED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


_STATUS_TO_DEFAULT_CODE = {
    HTTP_400_BAD_REQUEST: ErrorCode.BAD_REQUEST,
    HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
    HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
    HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
    HTTP_409_CONFLICT: ErrorCode.CONFLICT,
    HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.VALIDATION_FAILED,
    HTTP_500_INTERNAL_SERVER_ERROR: ErrorCode.INTERNAL_ERROR,
}


def _normalize_details(details: Optional[Union[List[ErrorDetail], List[dict], List[Any]]]) -> List[dict]:
    if not details:
        return []
    normalized: List[dict] = []
    for item in details:
        if isinstance(item, ErrorDetail):
            normalized.append(item.model_dump())
        elif isinstance(item, dict):
            normalized.append(
                {
                    "field": item.get("field"),
                    "message": item.get("message", ""),
                }
            )
        else:
            normalized.append({"field": None, "message": str(item)})
    return normalized


def build_error_payload(
    *,
    error_code: Union[ErrorCode, str],
    message: str,
    details: Optional[Union[List[ErrorDetail], List[dict]]] = None,
) -> dict:
    return {
        "error_code": error_code.value if isinstance(error_code, ErrorCode) else error_code,
        "message": message,
        "details": _normalize_details(details),
    }


def api_error(
    status_code: int,
    *,
    error_code: Union[ErrorCode, str],
    message: str,
    details: Optional[Union[List[ErrorDetail], List[dict]]] = None,
    headers: Optional[dict] = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=build_error_payload(error_code=error_code, message=message, details=details),
        headers=headers,
    )


def normalize_http_exception_detail(status_code: int, detail: Any) -> dict:
    if isinstance(detail, dict) and "error_code" in detail and "message" in detail:
        return {
            "error_code": detail["error_code"],
            "message": detail["message"],
            "details": detail.get("details", []),
        }

    if isinstance(detail, list):
        return build_error_payload(
            error_code=ErrorCode.VALIDATION_FAILED,
            message="Request validation failed",
            details=[
                {
                    "field": ".".join(str(part) for part in item.get("loc", []) if part != "body"),
                    "message": item.get("msg", "Invalid value"),
                }
                for item in detail
            ],
        )

    default_code = _STATUS_TO_DEFAULT_CODE.get(status_code, ErrorCode.INTERNAL_ERROR)
    return build_error_payload(
        error_code=default_code,
        message=str(detail),
        details=[],
    )
