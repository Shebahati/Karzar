"""Admin abandoned-cart queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.commerce import Order, OrderMode, PaymentStatus
from app.db.models.platform import Cart, CartItem, CartLane
from app.db.models.product import Product
from app.db.models.user import User


async def list_abandoned_carts(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    inactive_hours: int = 24,
) -> tuple[list[dict], int]:
    """Authenticated, non-empty carts inactive ≥ inactive_hours without a paid purchase order."""
    cutoff = datetime.now(UTC) - timedelta(hours=inactive_hours)

    converted_subq = (
        select(Order.user_id)
        .where(
            Order.deleted_at.is_(None),
            Order.mode == OrderMode.PURCHASE,
            Order.payment_status == PaymentStatus.PAID.value,
            Order.user_id.isnot(None),
        )
        .distinct()
    )

    base_filters = [
        Cart.user_id.isnot(None),
        Cart.lane == CartLane.PURCHASE,
        Cart.updated_at <= cutoff,
        Cart.user_id.notin_(converted_subq),
    ]

    count_stmt = (
        select(func.count(func.distinct(Cart.id)))
        .select_from(Cart)
        .join(CartItem, CartItem.cart_id == Cart.id)
        .where(*base_filters)
    )
    total = int((await db.execute(count_stmt)).scalar_one() or 0)

    stmt = (
        select(Cart)
        .join(CartItem, CartItem.cart_id == Cart.id)
        .where(*base_filters)
        .options(
            selectinload(Cart.items).selectinload(CartItem.cart),
            selectinload(Cart.items),
        )
        .order_by(Cart.updated_at.asc())
        .offset(skip)
        .limit(limit)
        .distinct()
    )
    carts = list((await db.execute(stmt)).scalars().unique().all())
    if not carts:
        return [], total

    user_ids = [cart.user_id for cart in carts if cart.user_id is not None]
    users_by_id: dict[int, User] = {}
    if user_ids:
        user_rows = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_by_id = {user.id: user for user in user_rows.scalars().all()}

    product_ids = {item.product_id for cart in carts for item in cart.items}
    products_by_id: dict[int, Product] = {}
    if product_ids:
        product_rows = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        products_by_id = {product.id: product for product in product_rows.scalars().all()}

    rows: list[dict] = []
    for cart in carts:
        user = users_by_id.get(cart.user_id) if cart.user_id else None
        item_count = sum(item.quantity for item in cart.items)
        if item_count <= 0:
            continue
        cart_value = Decimal("0")
        for item in cart.items:
            product = products_by_id.get(item.product_id)
            if product and product.base_price is not None:
                cart_value += Decimal(str(product.base_price)) * item.quantity
        rows.append(
            {
                "cart_id": cart.id,
                "user_id": cart.user_id,
                "customer_name": (user.full_name if user else None) or "—",
                "customer_phone": user.phone_number if user else None,
                "item_count": item_count,
                "cart_value": cart_value,
                "last_activity_at": cart.updated_at,
                "items": [
                    {
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                        "product_name": products_by_id.get(item.product_id).name
                        if products_by_id.get(item.product_id)
                        else None,
                        "product_sku": products_by_id.get(item.product_id).sku
                        if products_by_id.get(item.product_id)
                        else None,
                    }
                    for item in cart.items
                ],
            }
        )
    return rows, total
