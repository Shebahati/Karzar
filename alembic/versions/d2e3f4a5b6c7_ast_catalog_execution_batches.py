"""AST one-time catalog execution batch journal (#552)

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-10-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ast_catalog_execution_batches",
        sa.Column("batch_id", sa.String(length=128), nullable=False),
        sa.Column("execution_state", sa.String(length=32), nullable=False),
        sa.Column("cohort", sa.String(length=16), nullable=False),
        sa.Column("mutation_plan", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mutation_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("post_commit_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("batch_id"),
    )


def downgrade() -> None:
    op.drop_table("ast_catalog_execution_batches")
