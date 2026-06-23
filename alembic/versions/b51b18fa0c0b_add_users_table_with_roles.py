"""Add users table with roles

Revision ID: b51b18fa0c0b
Revises: 9bbd02b667e6
Create Date: 2026-06-17 16:40:31.471169

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b51b18fa0c0b'
down_revision: Union[str, None] = '9bbd02b667e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('phone_number', sa.String(length=15), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=100), nullable=True),
    sa.Column('role', sa.Enum('SUPER_ADMIN', 'B2B_CUSTOMER', 'B2C_CUSTOMER', name='userrole'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_phone_number'), 'users', ['phone_number'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_phone_number'), table_name='users')
    op.drop_table('users')
