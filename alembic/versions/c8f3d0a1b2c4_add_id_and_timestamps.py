"""add_id_and_timestamps

Revision ID: c8f3d0a1b2c4
Revises: b6bf2e96bab3
Create Date: 2026-06-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c8f3d0a1b2c4'
down_revision: Union[str, None] = 'b6bf2e96bab3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade: Add id and timestamps to products table."""
    
    # Step 1: Add new columns
    op.add_column('products', sa.Column('id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('products', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))
    op.add_column('products', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()))
    op.add_column('products', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    
    # Step 2: Generate UUIDs for existing rows (if any)
    op.execute("""
        UPDATE products 
        SET id = gen_random_uuid() 
        WHERE id IS NULL
    """)
    
    # Step 3: Set timestamps for existing rows
    op.execute("""
        UPDATE products 
        SET created_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL
    """)
    
    # Step 4: Make id and timestamps NOT NULL
    op.alter_column('products', 'id', nullable=False)
    op.alter_column('products', 'created_at', nullable=False)
    op.alter_column('products', 'updated_at', nullable=False)
    
    # Step 5: Drop old primary key constraint
    op.drop_constraint('products_pkey', 'products', type_='primary')
    
    # Step 6: Add new primary key on id
    op.create_primary_key('products_pkey', 'products', ['id'])
    
    # Step 7: Create unique constraint on sku
    op.create_unique_constraint('uq_products_sku', 'products', ['sku'])
    
    # Step 8: Create indexes
    op.create_index(op.f('ix_products_deleted_at'), 'products', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_products_created_at'), 'products', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade: Remove id and timestamps from products table."""
    
    # Drop indexes
    op.drop_index(op.f('ix_products_created_at'), table_name='products')
    op.drop_index(op.f('ix_products_deleted_at'), table_name='products')
    
    # Drop unique constraint
    op.drop_constraint('uq_products_sku', 'products', type_='unique')
    
    # Drop new primary key
    op.drop_constraint('products_pkey', 'products', type_='primary')
    
    # Add old primary key back
    op.create_primary_key('products_pkey', 'products', ['sku'])
    
    # Drop new columns
    op.drop_column('products', 'deleted_at')
    op.drop_column('products', 'updated_at')
    op.drop_column('products', 'created_at')
    op.drop_column('products', 'id')
