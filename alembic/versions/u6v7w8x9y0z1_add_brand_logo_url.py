"""Add brands.logo_url for storefront brand strip.

Revision ID: u6v7w8x9y0z1
Revises: t5u6v7w8x9y0
Create Date: 2026-07-25 11:30:00.000000
"""

import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op

_ALEMBIC_DIR = Path(__file__).resolve().parents[1]
if str(_ALEMBIC_DIR) not in sys.path:
    sys.path.insert(0, str(_ALEMBIC_DIR))

from brand_logo_url_guard import (  # noqa: E402
    downgrade_brands_logo_url,
    upgrade_brands_logo_url,
)

revision: str = "u6v7w8x9y0z1"
down_revision: Union[str, None] = "t5u6v7w8x9y0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    upgrade_brands_logo_url()


def downgrade() -> None:
    downgrade_brands_logo_url()
