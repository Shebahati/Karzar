"""Emalls read-only product extraction API.

Dedicated marketplace compatibility adapter — not the public storefront product API.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.core.request_throttle import enforce_public_throttle
from app.db.database import get_db
from app.schemas.emalls import EmallsProductsRequest, EmallsProductsResponse
from app.services.emalls.exceptions import (
    EmallsTokenInvalidError,
    EmallsValidationUnavailableError,
)
from app.services.emalls.service import list_emalls_products

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/products",
    response_model=EmallsProductsResponse,
    summary="Emalls product extraction (read-only)",
    responses={
        401: {"description": "Invalid Emalls token"},
        422: {"description": "Invalid page/limit/request body"},
        429: {"description": "Rate limited"},
        502: {"description": "Emalls validation service unavailable"},
        503: {"description": "Emalls validation service unavailable"},
    },
)
async def emalls_products(
    request: Request,
    body: EmallsProductsRequest,
    db: AsyncSession = Depends(get_db),
) -> EmallsProductsResponse:
    """Export public storefront products in Emalls-compatible shape.

    Authenticated solely via Emalls token validation (cached). Performs no
    catalog, price, availability, image, or KB writes.
    """
    await enforce_public_throttle(
        request,
        scope="emalls_products",
        max_requests=settings.PUBLIC_THROTTLE_EMALLS_MAX,
        window_seconds=settings.PUBLIC_THROTTLE_EMALLS_WINDOW,
    )

    logger.info(
        "integration=emalls request_accepted page=%s limit=%s",
        body.page,
        body.limit,
    )

    try:
        return await list_emalls_products(
            db,
            token=body.token,
            page=body.page,
            limit=body.limit,
        )
    except EmallsTokenInvalidError as exc:
        raise api_error(
            status.HTTP_401_UNAUTHORIZED,
            error_code=ErrorCode.UNAUTHORIZED,
            message="Emalls token is invalid",
        ) from exc
    except EmallsValidationUnavailableError as exc:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.INTERNAL_ERROR,
            message="Emalls token validation service is temporarily unavailable",
        ) from exc
