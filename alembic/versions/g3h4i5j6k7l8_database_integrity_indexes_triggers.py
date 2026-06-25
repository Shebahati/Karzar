"""Database integrity: indexes, constraints, triggers, and category template keys.

Revision ID: g3h4i5j6k7l8
Revises: f1a2b3c4d5e6
Create Date: 2026-06-25 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "g3h4i5j6k7l8"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UPDATED_AT_TABLES = ("brands", "categories", "product_images", "products", "users")


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("spec_template_key", sa.String(length=50), nullable=True),
    )

    op.drop_index("ix_products_sku", table_name="products")
    op.create_index("ix_products_sku", "products", ["sku"], unique=False)
    op.create_index(
        "uq_products_sku_active",
        "products",
        ["sku"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"], unique=False)
    op.create_index("ix_products_brand_id", "products", ["brand_id"], unique=False)
    op.create_index(
        "ix_products_active_list",
        "products",
        ["is_active", "deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_products_specifications_gin",
        "products",
        ["specifications"],
        unique=False,
        postgresql_using="gin",
    )

    op.create_index("ix_categories_parent_id", "categories", ["parent_id"], unique=False)
    op.create_unique_constraint(
        "uq_categories_parent_name",
        "categories",
        ["parent_id", "name"],
        postgresql_nulls_not_distinct=True,
    )

    op.create_index(
        "uq_product_images_one_primary",
        "product_images",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_primary IS TRUE"),
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in _UPDATED_AT_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )


def downgrade() -> None:
    for table in reversed(_UPDATED_AT_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    op.drop_index("uq_product_images_one_primary", table_name="product_images")
    op.drop_constraint("uq_categories_parent_name", "categories", type_="unique")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_index("ix_products_specifications_gin", table_name="products")
    op.drop_index("ix_products_active_list", table_name="products")
    op.drop_index("ix_products_brand_id", table_name="products")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_index("uq_products_sku_active", table_name="products")
    op.drop_index("ix_products_sku", table_name="products")
    op.create_index("ix_products_sku", "products", ["sku"], unique=True)

    op.drop_column("categories", "spec_template_key")
