"""Emalls product extraction service (read-only)."""

from __future__ import annotations

import math
import time
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.product import Product
from app.schemas.emalls import EmallsProductsResponse
from app.services.emalls.client import EmallsClient, get_emalls_client
from app.services.emalls.exceptions import (
    EmallsTokenInvalidError,
    EmallsValidationUnavailableError,
)
from app.services.emalls.presenter import present_emalls_products, safe_request_summary
from app.services.emalls.token_cache import (
    EmallsTokenCache,
    get_emalls_token_cache,
    token_cache_key,
)
from app.utils.public_catalog import (
    filter_storefront_public_products,
    storefront_public_product_filters,
)

logger = get_logger(__name__)


def _load_options() -> tuple[Any, ...]:
    return (
        selectinload(Product.images),
        selectinload(Product.category),
    )


async def ensure_emalls_token(
    token: str,
    *,
    client: EmallsClient | None = None,
    cache: EmallsTokenCache | None = None,
) -> bool:
    """Validate Emalls token with positive cache (fail closed on upstream outage).

    Returns True when the request was served from cache (cache_hit).
    """
    cache = cache or get_emalls_token_cache()
    client = client or get_emalls_client()
    key = token_cache_key(token, settings.EMALLS_SHOP_DOMAIN)

    if await cache.get_valid(key):
        logger.info(
            "integration=emalls cache_hit=true validation_result=cached_valid"
        )
        return True

    logger.info("integration=emalls cache_hit=false validation_result=miss")
    try:
        await client.validate_token(token)
    except EmallsTokenInvalidError:
        raise
    except EmallsValidationUnavailableError:
        raise

    await cache.set_valid(key, settings.EMALLS_TOKEN_CACHE_TTL_SECONDS)
    return False


async def _count_and_page(
    db: AsyncSession,
    *,
    skip: int,
    limit: int,
) -> tuple[list[Product], int]:
    """List storefront-public products ordered by Product.id DESC (stable pages)."""
    filters = storefront_public_product_filters()
    where_clause = and_(*filters) if filters else True
    materialized = bool(settings.STOREFRONT_REQUIRE_MATERIALIZED_IMAGES)

    if materialized:
        # Match catalog list semantics: SQL eligibility then on-disk image filter.
        all_stmt = (
            select(Product)
            .where(where_clause)
            .options(*_load_options())
            .order_by(Product.id.desc())
        )
        candidates = list((await db.execute(all_stmt)).scalars().all())
        eligible = filter_storefront_public_products(candidates)
        total = len(eligible)
        return eligible[skip : skip + limit], total

    count_stmt = select(func.count(Product.id)).where(where_clause)
    total = int((await db.execute(count_stmt)).scalar() or 0)

    page_stmt = (
        select(Product)
        .where(where_clause)
        .options(*_load_options())
        .order_by(Product.id.desc())
        .offset(skip)
        .limit(limit)
    )
    products = list((await db.execute(page_stmt)).scalars().all())
    return products, total


async def list_emalls_products(
    db: AsyncSession,
    *,
    token: str,
    page: int,
    limit: int,
    client: EmallsClient | None = None,
    cache: EmallsTokenCache | None = None,
) -> EmallsProductsResponse:
    """Authenticate via Emalls token, then return one page of public products."""
    started = time.perf_counter()
    cache_hit = await ensure_emalls_token(token, client=client, cache=cache)
    # Official v1.3.0: fresh remote validation → NeedSession=true; cache hit → false.
    need_session = not cache_hit

    skip = (page - 1) * limit
    products, total = await _count_and_page(db, skip=skip, limit=limit)
    max_pages = math.ceil(total / limit) if total > 0 else 0
    payload = present_emalls_products(products)

    duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "%s",
        safe_request_summary(
            page=page,
            limit=limit,
            product_count=len(payload),
            count=total,
            max_pages=max_pages,
            cache_hit=cache_hit,
            NeedSession=need_session,
            validation_result="ok",
            duration_ms=duration_ms,
            adapter_software_version=settings.EMALLS_ADAPTER_SOFTWARE_VERSION,
            compat_version=settings.EMALLS_COMPAT_VERSION,
        ),
    )

    return EmallsProductsResponse(
        count=total,
        max_pages=max_pages,
        products=payload,
        Version=settings.EMALLS_COMPAT_VERSION,
        NeedSession=need_session,
    )
