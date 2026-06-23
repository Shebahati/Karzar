"""fix enums numeric columns and defaults

Revision ID: e7f8a9b0c1d2
Revises: d4552516cd6a
Create Date: 2026-06-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "d4552516cd6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ALTER COLUMN stock_unit TYPE VARCHAR(20) USING stock_unit::text")
    op.execute(
        """
        UPDATE products
        SET stock_unit = CASE lower(stock_unit)
            WHEN 'piece' THEN 'piece'
            WHEN 'kg' THEN 'kg'
            WHEN 'meter' THEN 'meter'
            WHEN 'pack' THEN 'pack'
            ELSE 'piece'
        END
        """
    )
    op.execute("DROP TYPE IF EXISTS stockunitenum")
    op.execute("CREATE TYPE stockunitenum AS ENUM ('piece', 'kg', 'meter', 'pack')")
    op.execute(
        "ALTER TABLE products ALTER COLUMN stock_unit TYPE stockunitenum "
        "USING stock_unit::stockunitenum"
    )
    op.execute("ALTER TABLE products ALTER COLUMN stock_unit SET DEFAULT 'piece'")

    op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(30) USING role::text")
    op.execute(
        """
        UPDATE users
        SET role = CASE lower(role)
            WHEN 'super_admin' THEN 'super_admin'
            WHEN 'b2b_customer' THEN 'b2b_customer'
            WHEN 'b2c_customer' THEN 'b2c_customer'
            ELSE 'b2c_customer'
        END
        """
    )
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("CREATE TYPE userrole AS ENUM ('super_admin', 'b2b_customer', 'b2c_customer')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'b2c_customer'")
    op.execute("ALTER TABLE users ALTER COLUMN is_active SET DEFAULT true")

    op.alter_column(
        "products",
        "base_price",
        existing_type=sa.Float(),
        type_=sa.Numeric(15, 2),
        existing_nullable=True,
        postgresql_using="base_price::numeric(15,2)",
    )
    op.alter_column(
        "products",
        "stock_quantity",
        existing_type=sa.Float(),
        type_=sa.Numeric(12, 2),
        existing_nullable=False,
        postgresql_using="stock_quantity::numeric(12,2)",
    )
    op.alter_column(
        "products",
        "weight_grams",
        existing_type=sa.Float(),
        type_=sa.Numeric(12, 2),
        existing_nullable=True,
        postgresql_using="weight_grams::numeric(12,2)",
    )
    op.alter_column(
        "products",
        "tax_percent",
        existing_type=sa.Float(),
        type_=sa.Numeric(5, 2),
        existing_nullable=False,
        postgresql_using="tax_percent::numeric(5,2)",
    )


def downgrade() -> None:
    op.alter_column(
        "products",
        "tax_percent",
        existing_type=sa.Numeric(5, 2),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using="tax_percent::double precision",
    )
    op.alter_column(
        "products",
        "weight_grams",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Float(),
        existing_nullable=True,
        postgresql_using="weight_grams::double precision",
    )
    op.alter_column(
        "products",
        "stock_quantity",
        existing_type=sa.Numeric(12, 2),
        type_=sa.Float(),
        existing_nullable=False,
        postgresql_using="stock_quantity::double precision",
    )
    op.alter_column(
        "products",
        "base_price",
        existing_type=sa.Numeric(15, 2),
        type_=sa.Float(),
        existing_nullable=True,
        postgresql_using="base_price::double precision",
    )

    op.execute("ALTER TABLE users ALTER COLUMN is_active DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE VARCHAR(30) USING role::text")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("CREATE TYPE userrole AS ENUM ('SUPER_ADMIN', 'B2B_CUSTOMER', 'B2C_CUSTOMER')")
    op.execute(
        """
        ALTER TABLE users ALTER COLUMN role TYPE userrole USING (
            CASE role
                WHEN 'super_admin' THEN 'SUPER_ADMIN'
                WHEN 'b2b_customer' THEN 'B2B_CUSTOMER'
                ELSE 'B2C_CUSTOMER'
            END
        )::userrole
        """
    )

    op.execute("ALTER TABLE products ALTER COLUMN stock_unit DROP DEFAULT")
    op.execute("ALTER TABLE products ALTER COLUMN stock_unit TYPE VARCHAR(20) USING stock_unit::text")
    op.execute("DROP TYPE IF EXISTS stockunitenum")
    op.execute("CREATE TYPE stockunitenum AS ENUM ('PIECE', 'KG', 'METER', 'PACK')")
    op.execute(
        """
        ALTER TABLE products ALTER COLUMN stock_unit TYPE stockunitenum USING (
            CASE lower(stock_unit)
                WHEN 'piece' THEN 'PIECE'
                WHEN 'kg' THEN 'KG'
                WHEN 'meter' THEN 'METER'
                WHEN 'pack' THEN 'PACK'
                ELSE 'PIECE'
            END
        )::stockunitenum
        """
    )
