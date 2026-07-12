"""API v1 router aggregating all endpoint modules."""

from fastapi import APIRouter

from app.api.endpoints import (
    auth,
    brand,
    cart,
    category,
    cms,
    order,
    payment,
    product,
    storefront,
    users,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(product.router, prefix="/products", tags=["Products"])
api_router.include_router(category.router, prefix="/categories", tags=["Categories"])
api_router.include_router(brand.router, prefix="/brands", tags=["Brands"])
api_router.include_router(cart.router, prefix="/cart", tags=["Cart"])
api_router.include_router(order.router, prefix="/orders", tags=["Orders"])
api_router.include_router(payment.router, prefix="/payments", tags=["Payments"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(cms.router, prefix="/cms", tags=["CMS"])
api_router.include_router(storefront.router, tags=["Storefront"])
