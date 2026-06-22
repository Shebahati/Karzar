# app/api/v1/__init__.py
from fastapi import APIRouter
from app.api.endpoints import auth, product, category

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(product.router, prefix="/products", tags=["Products"])
api_router.include_router(category.router, prefix="/categories", tags=["Categories"])
