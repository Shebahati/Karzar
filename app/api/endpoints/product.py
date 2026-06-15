# app/api/endpoints/product.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.database import get_db
from app.schemas.product import ProductCreate, ProductResponse
from app.crud import product as crud_product

router = APIRouter()

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_new_product(product_in: ProductCreate, db: AsyncSession = Depends(get_db)):
    return await crud_product.create_product(db=db, product_in=product_in)

@router.get("/", response_model=List[ProductResponse])
async def read_products(db: AsyncSession = Depends(get_db)):
    return await crud_product.get_products(db=db)