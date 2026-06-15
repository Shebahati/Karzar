# app/main.py
from fastapi import FastAPI

# ایمپورت صحیح روتر محصولات
from app.api.endpoints.product import router as product_router

app = FastAPI(title="Industrial Lathe Tools API")

# ثبت روتر با نامی که ایمپورت کردیم
app.include_router(product_router, prefix="/api/v1/products", tags=["Products"])

@app.get("/")
async def root():
    return {"message": "Karzar API is running smoothly!"}