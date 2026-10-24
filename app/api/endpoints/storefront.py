"""Storefront endpoints aggregator."""

from fastapi import APIRouter

from app.api.endpoints import checkout, hero_design, storefront_content

router = APIRouter()

# Content routes first (blog/articles/hero/contact), then checkout — same order as original.
router.include_router(storefront_content.router)
router.include_router(hero_design.storefront_router)
router.include_router(checkout.router)
