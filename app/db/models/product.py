# app/db/models/product.py
import enum
from typing import Any, List, Optional
from sqlalchemy import String, Integer, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from app.db.models.base import Base

# 1. تعریف Enum برای واحدهای اندازه‌گیری (جلوگیری از تایپ اشتباه در فرانت‌اند)
class StockUnitEnum(str, enum.Enum):
    PIECE = "piece"       # عدد / قطعه
    KG = "kg"             # کیلوگرم
    METER = "meter"       # متر
    PACK = "pack"         # بسته

# 2. جدول دسته‌بندی‌ها (با قابلیت Self-Referential برای ساختار درختی نامحدود)
class Category(Base):
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # اگر parent_id خالی باشد، یعنی این دسته اصلی (سطح 1) است
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"))
    
    # روابط (Relationships)
    subcategories: Mapped[List["Category"]] = relationship("Category", back_populates="parent")
    parent: Mapped[Optional["Category"]] = relationship("Category", back_populates="subcategories", remote_side=[id])
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")

# 3. جدول برندها
class Brand(Base):
    __tablename__ = "brands"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(50))
    
    products: Mapped[List["Product"]] = relationship("Product", back_populates="brand")

# 4. جدول اصلی محصولات (هسته مرکزی)
class Product(Base):
    __tablename__ = "products"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    
    # کلیدهای خارجی
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    brand_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brands.id"))
    
    # اطلاعات مالی و موجودی
    base_price: Mapped[Optional[float]] = mapped_column(Float) # می‌تواند برای B2B خالی باشد
    stock_quantity: Mapped[float] = mapped_column(Float, default=0.0) # اعشاری برای متراژ و وزن
    stock_unit: Mapped[StockUnitEnum] = mapped_column(Enum(StockUnitEnum), default=StockUnitEnum.PIECE)
    
    # کاتالوگ و مشخصات فنی (شاه‌کلید دیتابیس ما)
    pdf_catalog_url: Mapped[Optional[str]] = mapped_column(String(500))
    specifications: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # روابط
    category: Mapped["Category"] = relationship("Category", back_populates="products")
    brand: Mapped[Optional["Brand"]] = relationship("Brand", back_populates="products")
    # cascade="all, delete-orphan" یعنی اگر محصول پاک شد، عکس‌هایش هم از دیتابیس پاک شوند
    images: Mapped[List["ProductImage"]] = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")

# 5. جدول تصاویر محصولات
class ProductImage(Base):
    __tablename__ = "product_images"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False) # عکس اصلی (کاور)

    product: Mapped["Product"] = relationship("Product", back_populates="images")