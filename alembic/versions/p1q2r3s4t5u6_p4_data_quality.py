"""P4 data quality: require category_id on products, add admin_note on orders.

Revision ID: p1q2r3s4t5u6
Revises: o0p1q2r3s4t5
Create Date: 2026-07-12 13:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "p1q2r3s4t5u6"
down_revision: Union[str, None] = "o0p1q2r3s4t5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("admin_note", sa.Text(), nullable=True))

    # Backfill legacy payment metadata from order.note into dedicated columns.
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, note, payment_authority, payment_ref_id "
            "FROM orders WHERE note IS NOT NULL"
        )
    ).fetchall()
    for row in rows:
        order_id, note, authority, ref_id = row
        if not note:
            continue
        updates: dict[str, str] = {}
        if not authority and "authority=" in note:
            for part in note.replace("|", " ").split():
                if part.startswith("authority="):
                    updates["payment_authority"] = part.split("=", 1)[1]
                    break
        if not ref_id and "ref_id=" in note:
            for part in note.replace("|", " ").split():
                if part.startswith("ref_id="):
                    updates["payment_ref_id"] = part.split("=", 1)[1]
                    break
        if updates:
            conn.execute(
                sa.text(
                    "UPDATE orders SET "
                    + ", ".join(f"{k} = :{k}" for k in updates)
                    + " WHERE id = :id"
                ),
                {**updates, "id": order_id},
            )

    # Assign uncategorizable products to the first depth-3 leaf category when available.
    leaf = conn.execute(
        sa.text(
            """
            SELECT c3.id
            FROM categories c3
            JOIN categories c2 ON c3.parent_id = c2.id
            JOIN categories c1 ON c2.parent_id = c1.id
            WHERE c1.parent_id IS NULL
              AND NOT EXISTS (SELECT 1 FROM categories child WHERE child.parent_id = c3.id)
            ORDER BY c3.id
            LIMIT 1
            """
        )
    ).fetchone()
    if leaf is not None:
        conn.execute(
            sa.text("UPDATE products SET category_id = :cid WHERE category_id IS NULL"),
            {"cid": leaf[0]},
        )

    remaining = conn.execute(
        sa.text("SELECT COUNT(*) FROM products WHERE category_id IS NULL")
    ).scalar()
    if remaining and int(remaining) > 0:
        raise RuntimeError(
            "Cannot enforce NOT NULL on products.category_id: "
            f"{remaining} products still lack a category. Create a depth-3 category first."
        )

    op.alter_column(
        "products",
        "category_id",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "products",
        "category_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.drop_column("orders", "admin_note")
