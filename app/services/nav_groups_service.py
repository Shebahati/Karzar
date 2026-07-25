"""Megamenu nav-group validation and persistence."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

from app.core.errors import ErrorCode, api_error
from app.db.models.content import MegamenuNavGroup
from app.db.models.product import Category
from app.schemas.cms import NavGroupReplaceItem, NavGroupReplaceRequest


def _slug_ok(slug: str) -> bool:
    if not slug or len(slug) > 64:
        return False
    return all(ch.isalnum() or ch in "-_" for ch in slug)


async def list_nav_groups(
    db: AsyncSession,
    *,
    enabled_only: bool = False,
) -> list[MegamenuNavGroup]:
    stmt = select(MegamenuNavGroup).order_by(
        MegamenuNavGroup.sort_order.asc(),
        MegamenuNavGroup.id.asc(),
    )
    if enabled_only:
        stmt = stmt.where(MegamenuNavGroup.is_enabled.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _load_l1_ids(db: AsyncSession) -> set[int]:
    result = await db.execute(select(Category.id).where(Category.parent_id.is_(None)))
    return set(result.scalars().all())


async def validate_nav_group_payload(
    db: AsyncSession,
    groups: list[NavGroupReplaceItem],
) -> None:
    """Raise 422 when slugs collide, roots are not L1, or a root appears twice."""
    if not groups:
        raise api_error(
            HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="حداقل یک گروه ناوبری لازم است",
            details=[{"field": "groups", "message": "At least one nav group is required"}],
        )

    details: list[dict[str, str | None]] = []
    slugs = [g.slug.strip() for g in groups]
    slug_counts = Counter(slugs)
    for slug, count in slug_counts.items():
        if count > 1:
            details.append(
                {
                    "field": "slug",
                    "message": f"شناسه گروه تکراری است: {slug}",
                }
            )
        if not _slug_ok(slug):
            details.append(
                {
                    "field": "slug",
                    "message": f"شناسه گروه نامعتبر است: {slug}",
                }
            )

    for idx, group in enumerate(groups):
        if not group.label.strip():
            details.append(
                {
                    "field": f"groups[{idx}].label",
                    "message": "برچسب گروه الزامی است",
                }
            )
        # Duplicates inside a single group
        id_counts = Counter(group.root_category_ids)
        for root_id, count in id_counts.items():
            if count > 1:
                details.append(
                    {
                        "field": f"groups[{idx}].root_category_ids",
                        "message": f"ریشه {root_id} در همین گروه تکراری است",
                    }
                )

    all_roots: list[int] = []
    for group in groups:
        all_roots.extend(group.root_category_ids)
    root_counts = Counter(all_roots)
    for root_id, count in root_counts.items():
        if count > 1:
            details.append(
                {
                    "field": "root_category_ids",
                    "message": f"ریشه لایه ۱ با شناسه {root_id} در بیش از یک گروه قرار گرفته است",
                }
            )

    l1_ids = await _load_l1_ids(db)
    for root_id in set(all_roots):
        if root_id not in l1_ids:
            details.append(
                {
                    "field": "root_category_ids",
                    "message": f"شناسه {root_id} یک دسته ریشه (لایه ۱) معتبر نیست",
                }
            )

    if details:
        raise api_error(
            HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="پیکربندی گروه‌های مگامنو نامعتبر است",
            details=details,
        )


async def replace_nav_groups(
    db: AsyncSession,
    payload: NavGroupReplaceRequest,
) -> list[MegamenuNavGroup]:
    """Atomically replace all megamenu nav groups."""
    await validate_nav_group_payload(db, payload.groups)

    existing = await list_nav_groups(db, enabled_only=False)
    for row in existing:
        await db.delete(row)
    await db.flush()

    created: list[MegamenuNavGroup] = []
    for item in sorted(payload.groups, key=lambda g: (g.sort_order, g.slug)):
        row = MegamenuNavGroup(
            slug=item.slug.strip(),
            label=item.label.strip(),
            sort_order=item.sort_order,
            is_enabled=item.is_enabled,
            highlight=item.highlight,
            root_category_ids=list(dict.fromkeys(item.root_category_ids)),
        )
        db.add(row)
        created.append(row)
    await db.flush()
    for row in created:
        await db.refresh(row)
    return sorted(created, key=lambda g: (g.sort_order, g.id))


async def get_nav_group(db: AsyncSession, group_id: int) -> MegamenuNavGroup | None:
    result = await db.execute(select(MegamenuNavGroup).where(MegamenuNavGroup.id == group_id))
    return result.scalar_one_or_none()
