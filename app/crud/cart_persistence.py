"""CRUD for cart persistence."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.platform import Cart, CartItem, CartLane


async def get_or_create_cart(
    db: AsyncSession,
    *,
    lane: CartLane,
    user_id: int | None = None,
    guest_token: str | None = None,
) -> Cart:
    if user_id is not None:
        stmt = select(Cart).where(Cart.user_id == user_id, Cart.lane == lane)
    elif guest_token:
        stmt = select(Cart).where(Cart.guest_token == guest_token, Cart.lane == lane)
    else:
        raise ValueError("Either user_id or guest_token is required")

    result = await db.execute(stmt.options(selectinload(Cart.items)))
    cart = result.scalar_one_or_none()
    if cart is not None:
        return cart

    cart = Cart(user_id=user_id, guest_token=guest_token, lane=lane)
    db.add(cart)
    await db.flush()
    await db.refresh(cart, attribute_names=["items"])
    return cart


async def get_cart_with_items(
    db: AsyncSession,
    *,
    lane: CartLane,
    user_id: int | None = None,
    guest_token: str | None = None,
) -> Cart | None:
    if user_id is not None:
        stmt = select(Cart).where(Cart.user_id == user_id, Cart.lane == lane)
    elif guest_token:
        stmt = select(Cart).where(Cart.guest_token == guest_token, Cart.lane == lane)
    else:
        return None
    result = await db.execute(stmt.options(selectinload(Cart.items)))
    return result.scalar_one_or_none()


async def upsert_cart_item(
    db: AsyncSession,
    cart: Cart,
    *,
    product_id: int,
    quantity: int,
) -> CartItem:
    existing = next((item for item in cart.items if item.product_id == product_id), None)
    if existing is not None:
        if quantity <= 0:
            await db.delete(existing)
            await db.flush()
            cart.items = [item for item in cart.items if item.id != existing.id]
            return existing
        existing.quantity = quantity
        await db.flush()
        return existing

    if quantity <= 0:
        raise ValueError("Quantity must be positive when adding a new cart item")

    item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity)
    db.add(item)
    await db.flush()
    cart.items.append(item)
    return item


async def remove_cart_item(db: AsyncSession, cart: Cart, product_id: int) -> bool:
    item = next((row for row in cart.items if row.product_id == product_id), None)
    if item is None:
        return False
    await db.delete(item)
    await db.flush()
    cart.items = [row for row in cart.items if row.product_id != product_id]
    return True


async def clear_cart_items(db: AsyncSession, cart: Cart) -> None:
    if not cart.items:
        return
    await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
    await db.flush()
    cart.items = []


async def merge_guest_cart_into_user(
    db: AsyncSession,
    *,
    guest_token: str,
    user_id: int,
    lane: CartLane,
) -> Cart:
    guest_cart = await get_cart_with_items(db, lane=lane, guest_token=guest_token)
    user_cart = await get_or_create_cart(db, lane=lane, user_id=user_id)

    if guest_cart is None or not guest_cart.items:
        return user_cart

    for guest_item in guest_cart.items:
        user_item = next(
            (item for item in user_cart.items if item.product_id == guest_item.product_id),
            None,
        )
        if user_item is not None:
            user_item.quantity += guest_item.quantity
        else:
            await upsert_cart_item(
                db,
                user_cart,
                product_id=guest_item.product_id,
                quantity=guest_item.quantity,
            )

    await clear_cart_items(db, guest_cart)
    await db.delete(guest_cart)
    await db.flush()
    await db.refresh(user_cart, attribute_names=["items"])
    return user_cart
