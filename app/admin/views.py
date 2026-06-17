# app/admin/views.py
from sqladmin import ModelView
from app.db.models.product import Product, Category, Brand, ProductImage

class CategoryAdmin(ModelView, model=Category):
    column_list = [Category.id, Category.name, Category.parent_id]
    column_searchable_list = [Category.name]
    icon = "fa-solid fa-folder-tree"
    name = "دسته‌بندی"
    name_plural = "دسته‌بندی‌ها"

class BrandAdmin(ModelView, model=Brand):
    column_list = [Brand.id, Brand.name, Brand.country]
    column_searchable_list = [Brand.name]
    icon = "fa-solid fa-copyright"
    name = "برند"
    name_plural = "برندها"

class ProductAdmin(ModelView, model=Product):
    # اینجا می‌گوییم اسم دسته‌بندی و برند را هم در لیست محصولات نشان بده
    column_list = [Product.id, Product.sku, Product.name, Product.category, Product.brand]
    column_searchable_list = [Product.sku, Product.name]
    icon = "fa-solid fa-box"
    name = "محصول"
    name_plural = "محصولات"

class ProductImageAdmin(ModelView, model=ProductImage):
    column_list = [ProductImage.id, ProductImage.product, ProductImage.is_primary]
    icon = "fa-solid fa-image"
    name = "تصویر محصول"
    name_plural = "تصاویر محصولات"