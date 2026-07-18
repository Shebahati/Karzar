"""Product endpoints aggregator. Sub-routers preserve relative path matching."""

from fastapi import APIRouter

from app.api.endpoints import (
    products_admin,
    products_catalog,
    products_images,
    products_reviews,
)

router = APIRouter()

# Order mirrors the original product.py registration sequence as closely as
# possible with split modules: create (admin) first, then catalog reads,
# reviews, images. Remaining admin write/stock routes live on products_admin
# and are registered with that module (methods/paths do not collide with catalog).
router.include_router(products_admin.router)
router.include_router(products_catalog.router)
router.include_router(products_reviews.router)
router.include_router(products_images.router)
