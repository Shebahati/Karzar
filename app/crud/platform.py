"""CRUD for platform tables: carts, refresh tokens, audit, idempotency."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.platform import (
    AdminAuditLog,
    Cart,
    CartItem,
    CartLane,
    IdempotencyKey,
    ProductChangeLog,
    RefreshToken,
    StepUpTokenUse,
)


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


async def store_refresh_token(
    db: AsyncSession,
    *,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    row = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(row)
    await db.flush()
    return row


async def get_valid_refresh_token(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    now = datetime.now(UTC)
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked_at.is_(None),
        RefreshToken.expires_at > now,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def revoke_refresh_token(db: AsyncSession, row: RefreshToken) -> None:
    row.revoked_at = datetime.now(UTC)
    await db.flush()


async def revoke_all_refresh_tokens_for_user(db: AsyncSession, user_id: int) -> None:
    now = datetime.now(UTC)
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    )
    rows = (await db.execute(stmt)).scalars().all()
    for row in rows:
        row.revoked_at = now
    await db.flush()


async def record_audit_log(
    db: AsyncSession,
    *,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> AdminAuditLog:
    row = AdminAuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    db.add(row)
    await db.flush()
    return row


async def list_audit_logs(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> tuple[list[AdminAuditLog], int]:
    filters = []
    if entity_type:
        filters.append(AdminAuditLog.entity_type == entity_type)
    if entity_id:
        filters.append(AdminAuditLog.entity_id == entity_id)

    count_stmt = select(func.count()).select_from(AdminAuditLog)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(AdminAuditLog)
        .order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
        .offset(skip)
        .limit(limit)
    )
    if filters:
        stmt = stmt.where(*filters)
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), total


async def record_product_change(
    db: AsyncSession,
    *,
    product_id: int,
    field_name: str,
    old_value: str | None,
    new_value: str | None,
    reason: str | None = None,
    actor_user_id: int | None = None,
) -> ProductChangeLog:
    row = ProductChangeLog(
        product_id=product_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
        actor_user_id=actor_user_id,
    )
    db.add(row)
    await db.flush()
    return row


async def list_product_change_logs(
    db: AsyncSession,
    product_id: int,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[ProductChangeLog], int]:
    count_stmt = (
        select(func.count())
        .select_from(ProductChangeLog)
        .where(ProductChangeLog.product_id == product_id)
    )
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = (
        select(ProductChangeLog)
        .where(ProductChangeLog.product_id == product_id)
        .order_by(ProductChangeLog.created_at.desc(), ProductChangeLog.id.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), total


async def get_idempotency_record(
    db: AsyncSession,
    *,
    scope: str,
    key: str,
) -> IdempotencyKey | None:
    now = datetime.now(UTC)
    stmt = select(IdempotencyKey).where(
        IdempotencyKey.scope == scope,
        IdempotencyKey.key == key,
        IdempotencyKey.expires_at > now,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def store_idempotency_record(
    db: AsyncSession,
    *,
    scope: str,
    key: str,
    status_code: int,
    response_body: dict[str, Any],
    expires_at: datetime,
) -> IdempotencyKey:
    row = IdempotencyKey(
        scope=scope,
        key=key,
        status_code=status_code,
        response_body=response_body,
        expires_at=expires_at,
    )
    db.add(row)
    await db.flush()
    return row


async def consume_step_up_jti(
    db: AsyncSession,
    *,
    jti: str,
    expires_at: datetime,
) -> bool:
    try:
        async with db.begin_nested():
            row = StepUpTokenUse(jti=jti, expires_at=expires_at)
            db.add(row)
            await db.flush()
            return True
    except IntegrityError:
        return False
