"""Emalls read-only product extraction API.

Two intentionally separate contracts under the same router prefix:

- ``POST /products`` — WordPress extraction-plugin compatibility (token auth)
- ``GET|POST /feed`` — direct Emalls PDF feed (query params; no invented auth)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorCode, api_error
from app.core.logging import get_logger
from app.core.request_throttle import enforce_public_throttle
from app.db.database import get_db
from app.schemas.emalls import EmallsProductsRequest, EmallsProductsResponse
from app.schemas.emalls_pdf_feed import (
    EMALLS_PDF_DEFAULT_ITEM_PER_PAGE,
    EMALLS_PDF_DEFAULT_PAGE,
    EMALLS_PDF_MAX_ITEM_PER_PAGE,
    EmallsPdfFeedResponse,
)
from app.services.emalls.exceptions import (
    EmallsTokenInvalidError,
    EmallsValidationUnavailableError,
)
from app.services.emalls.pdf_feed import list_emalls_pdf_feed
from app.services.emalls.request_parser import parse_emalls_products_request
from app.services.emalls.service import list_emalls_products

logger = get_logger(__name__)

router = APIRouter()

_REQUEST_SCHEMA = EmallsProductsRequest.model_json_schema()


async def _throttle_emalls(request: Request, *, scope: str) -> None:
    await enforce_public_throttle(
        request,
        scope=scope,
        max_requests=settings.PUBLIC_THROTTLE_EMALLS_MAX,
        window_seconds=settings.PUBLIC_THROTTLE_EMALLS_WINDOW,
    )


@router.post(
    "/products",
    response_model=EmallsProductsResponse,
    summary="Emalls product extraction (read-only)",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": _REQUEST_SCHEMA},
                "application/x-www-form-urlencoded": {"schema": _REQUEST_SCHEMA},
            },
            "description": (
                "Emalls-compatible params (`token`, `page`, `limit`, `variation`). "
                "Accepts JSON or form-urlencoded bodies; query params are also merged "
                "(WordPress WP_REST_Request::get_param parity)."
            ),
        }
    },
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
    body: EmallsProductsRequest = Depends(parse_emalls_products_request),
    db: AsyncSession = Depends(get_db),
) -> EmallsProductsResponse:
    """Export public storefront products in Emalls WordPress-compatible shape.

    Authenticated solely via Emalls token validation (cached). Performs no
    catalog, price, availability, image, or KB writes.
    """
    await _throttle_emalls(request, scope="emalls_products")

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


async def _emalls_pdf_feed(
    request: Request,
    *,
    page: int,
    item_per_page: int,
    db: AsyncSession,
) -> EmallsPdfFeedResponse:
    await _throttle_emalls(request, scope="emalls_pdf_feed")
    logger.info(
        "integration=emalls_pdf_feed request_accepted page=%s item_per_page=%s",
        page,
        item_per_page,
    )
    return await list_emalls_pdf_feed(db, page=page, item_per_page=item_per_page)


@router.get(
    "/feed",
    response_model=EmallsPdfFeedResponse,
    summary="Emalls PDF product feed (read-only)",
    responses={
        422: {"description": "Invalid page/item_per_page"},
        429: {"description": "Rate limited"},
    },
)
async def emalls_pdf_feed_get(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = Query(
        EMALLS_PDF_DEFAULT_PAGE,
        ge=1,
        description="1-based page number (Emalls PDF query string)",
    ),
    item_per_page: int = Query(
        EMALLS_PDF_DEFAULT_ITEM_PER_PAGE,
        ge=1,
        le=EMALLS_PDF_MAX_ITEM_PER_PAGE,
        description=(
            "Products per page (Emalls PDF). "
            f"Karzar operational safety cap={EMALLS_PDF_MAX_ITEM_PER_PAGE} "
            "(not specified by the Emalls PDF)."
        ),
    ),
) -> EmallsPdfFeedResponse:
    """Direct Emalls PDF feed. Auth not specified by PDF — no invented token."""
    return await _emalls_pdf_feed(
        request, page=page, item_per_page=item_per_page, db=db
    )


@router.post(
    "/feed",
    response_model=EmallsPdfFeedResponse,
    summary="Emalls PDF product feed (read-only, POST)",
    openapi_extra={
        "requestBody": {
            "required": False,
            "content": {},
            "description": (
                "No body is required. Emalls PDF specifies query string parameters "
                "only (`page`, `item_per_page`). Empty POST body is valid."
            ),
        }
    },
    responses={
        422: {"description": "Invalid page/item_per_page"},
        429: {"description": "Rate limited"},
    },
)
async def emalls_pdf_feed_post(
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = Query(
        EMALLS_PDF_DEFAULT_PAGE,
        ge=1,
        description="1-based page number (Emalls PDF query string)",
    ),
    item_per_page: int = Query(
        EMALLS_PDF_DEFAULT_ITEM_PER_PAGE,
        ge=1,
        le=EMALLS_PDF_MAX_ITEM_PER_PAGE,
        description=(
            "Products per page (Emalls PDF). "
            f"Karzar operational safety cap={EMALLS_PDF_MAX_ITEM_PER_PAGE} "
            "(not specified by the Emalls PDF)."
        ),
    ),
) -> EmallsPdfFeedResponse:
    """POST parity for GET /feed. Query parameters only; body optional/ignored."""
    return await _emalls_pdf_feed(
        request, page=page, item_per_page=item_per_page, db=db
    )
