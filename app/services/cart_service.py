"""Server-side cart persistence for purchase and inquiry lanes."""


from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import platform as crud_platform
from app.crud import product as crud_product
from app.db.models.platform import CartLane
from app.db.models.user import User, UserRole
from app.schemas.cart import CartItemResponse, CartResponse


def _lane_from_mode(mode: str) -> CartLane:
    return CartLane.INQUIRY if mode == "inquiry" else CartLane.PURCHASE


async def get_cart_response(
    db: AsyncSession,
    *,
    lane: CartLane,
    user: User | None = None,
    guest_token: str | None = None,
) -> CartResponse:
    cart = await crud_platform.get_cart_with_items(
        db, lane=lane, user_id=user.id if user else None, guest_token=guest_token
    )
    if cart is None or not cart.items:
        return CartResponse(lane=lane.value, items=[], item_count=0)

    product_ids = [item.product_id for item in cart.items]
    products = await crud_product.get_products_by_ids(db, product_ids)
    items: list[CartItemResponse] = []
    for item in cart.items:
        product = products.get(item.product_id)
        if product is None or not product.is_active:
            continue
        items.append(
            CartItemResponse(
                product_id=item.product_id,
                quantity=item.quantity,
                product_name=product.name,
                base_price=str(product.base_price) if product.base_price is not None else None,
                stock_quantity=product.stock_quantity,
            )
        )
    return CartResponse(
        lane=lane.value,
        items=items,
        item_count=sum(row.quantity for row in items),
    )


async def upsert_item(
    db: AsyncSession,
    *,
    lane: CartLane,
    product_id: int,
    quantity: int,
    user: User | None = None,
    guest_token: str | None = None,
) -> CartResponse:
    product = await crud_product.get_product_by_id(db, product_id)
    if not product or not product.is_active:
        raise ValueError(f"Product {product_id} is not available")

    if lane == CartLane.PURCHASE and product.base_price is None:
        raise ValueError("Priced products only belong in the purchase cart")

    cart = await crud_platform.get_or_create_cart(
        db,
        lane=lane,
        user_id=user.id if user else None,
        guest_token=guest_token,
    )
    await crud_platform.upsert_cart_item(db, cart, product_id=product_id, quantity=quantity)
    await db.commit()
    return await get_cart_response(db, lane=lane, user=user, guest_token=guest_token)


async def remove_item(
    db: AsyncSession,
    *,
    lane: CartLane,
    product_id: int,
    user: User | None = None,
    guest_token: str | None = None,
) -> CartResponse:
    cart = await crud_platform.get_cart_with_items(
        db, lane=lane, user_id=user.id if user else None, guest_token=guest_token
    )
    if cart is None:
        return CartResponse(lane=lane.value, items=[], item_count=0)
    await crud_platform.remove_cart_item(db, cart, product_id)
    await db.commit()
    return await get_cart_response(db, lane=lane, user=user, guest_token=guest_token)


async def clear_lane(
    db: AsyncSession,
    *,
    lane: CartLane,
    user: User | None = None,
    guest_token: str | None = None,
) -> None:
    cart = await crud_platform.get_cart_with_items(
        db, lane=lane, user_id=user.id if user else None, guest_token=guest_token
    )
    if cart is None:
        return
    await crud_platform.clear_cart_items(db, cart)
    await db.commit()


async def merge_guest_into_user(
    db: AsyncSession,
    *,
    guest_token: str,
    user: User,
    lane: CartLane | None = None,
) -> list[CartResponse]:
    lanes = [lane] if lane is not None else [CartLane.PURCHASE, CartLane.INQUIRY]
    responses: list[CartResponse] = []
    for cart_lane in lanes:
        await crud_platform.merge_guest_cart_into_user(
            db,
            guest_token=guest_token,
            user_id=user.id,
            lane=cart_lane,
        )
        responses.append(await get_cart_response(db, lane=cart_lane, user=user))
    await db.commit()
    return responses


def resolve_checkout_defaults(
    user: User | None,
    payload_mode: str,
    company_name: str | None,
) -> tuple[str, str | None]:
    """Prefill B2B company name from the customer profile when omitted."""
    resolved_company = company_name
    if user is not None and user.role == UserRole.B2B_CUSTOMER:
        if not resolved_company and user.company_name:
            resolved_company = user.company_name
    return payload_mode, resolved_company


async def clear_cart_for_checkout(
    db: AsyncSession,
    *,
    mode: str,
    user: User | None = None,
    guest_token: str | None = None,
) -> None:
    lane = _lane_from_mode(mode)
    await clear_lane(db, lane=lane, user=user, guest_token=guest_token)
