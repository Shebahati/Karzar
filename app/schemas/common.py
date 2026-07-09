"""Shared pagination wrapper used by list endpoints."""

from typing import Generic, List, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    total_count: int = Field(..., ge=0)
    skip: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard list response envelope: {data: T[], meta: PaginationMeta}."""

    data: List[T]
    meta: PaginationMeta


def build_pagination_meta(*, total_count: int, skip: int, limit: int) -> PaginationMeta:
    return PaginationMeta(
        total_count=total_count,
        skip=skip,
        limit=limit,
        has_next=(skip + limit) < total_count,
        has_prev=skip > 0,
    )


def resolve_pagination(
    *,
    page: int | None,
    page_size: int | None,
    skip: int,
    limit: int,
) -> tuple[int, int]:
    """Prefer page/page_size when provided; otherwise fall back to skip/limit."""
    if page is not None or page_size is not None:
        resolved_page = page if page is not None else 1
        resolved_page_size = page_size if page_size is not None else limit
        if resolved_page < 1:
            resolved_page = 1
        if resolved_page_size < 1:
            resolved_page_size = 1
        return (resolved_page - 1) * resolved_page_size, resolved_page_size
    return skip, limit
