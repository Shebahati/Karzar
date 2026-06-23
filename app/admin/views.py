"""SQLAdmin model view registrations for the admin panel."""

from sqladmin import ModelView

from app.db.models.product import Brand, Category, Product, ProductImage
from app.db.models.user import User


class CategoryAdmin(ModelView, model=Category):
    column_list = [Category.id, Category.name, Category.parent_id]
    column_searchable_list = [Category.name]
    icon = "fa-solid fa-folder-tree"
    name = "Category"
    name_plural = "Categories"


class BrandAdmin(ModelView, model=Brand):
    column_list = [Brand.id, Brand.name, Brand.country]
    column_searchable_list = [Brand.name]
    icon = "fa-solid fa-copyright"
    name = "Brand"
    name_plural = "Brands"


class ProductAdmin(ModelView, model=Product):
    column_list = [Product.id, Product.sku, Product.name, Product.category, Product.brand]
    column_searchable_list = [Product.sku, Product.name]
    icon = "fa-solid fa-box"
    name = "Product"
    name_plural = "Products"


class ProductImageAdmin(ModelView, model=ProductImage):
    column_list = [ProductImage.id, ProductImage.product, ProductImage.is_primary]
    icon = "fa-solid fa-image"
    name = "Product Image"
    name_plural = "Product Images"


class UserAdmin(ModelView, model=User):
    can_create = False
    can_delete = False
    column_list = [User.id, User.phone_number, User.full_name, User.role, User.is_active]
    column_searchable_list = [User.phone_number, User.full_name]
    form_columns = [User.phone_number, User.full_name, User.role, User.is_active]
    form_widget_args = {User.phone_number: {"readonly": True}}
    icon = "fa-solid fa-users"
    name = "User"
    name_plural = "Users"
