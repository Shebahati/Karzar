"""Add updated_at triggers to commerce/content tables and rating check constraint.

Revision ID: i5j6k7l8m9n0
Revises: h4i5j6k7l8m9
Create Date: 2026-07-09 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = "i5j6k7l8m9n0"
down_revision: Union[str, None] = "h4i5j6k7l8m9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UPDATED_AT_TABLES = (
    "orders",
    "order_items",
    "articles",
    "hero_slides",
    "product_comments",
    "contact_submissions",
    "otp_codes",
)


def upgrade() -> None:
    # set_updated_at() is created by revision g3h4i5j6k7l8; reuse it here.
    for table in _UPDATED_AT_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
            """
        )

    op.create_check_constraint(
        "ck_product_comments_rating_range",
        "product_comments",
        "rating BETWEEN 1 AND 5",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_product_comments_rating_range", "product_comments", type_="check"
    )
    for table in reversed(_UPDATED_AT_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
