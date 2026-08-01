"""Knowledge Graph wave-1 read + projection sync (KB-001 / ADR-013 / ADR-014)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_super_admin
from app.core.errors import api_error
from app.crud import knowledge as knowledge_crud
from app.db.database import get_db
from app.db.models.knowledge import KB001_EDGE_TYPES
from app.db.models.user import User
from app.schemas.knowledge import (
    KnowledgeEdgeListResponse,
    KnowledgeEdgeResponse,
    ProductNeighborhoodResponse,
    ProjectionSyncRequest,
    ProjectionSyncResponse,
)
from app.services.knowledge_edge_projector import sync_projections

router = APIRouter()


@router.get(
    "/edges",
    response_model=KnowledgeEdgeListResponse,
    summary="List knowledge edges (KB-001 freeze types)",
)
async def list_knowledge_edges(
    edge_type: str | None = Query(
        default=None,
        description="One of PRODUCT_BELONGS_TO_CATEGORY | PRODUCT_BRANDED_AS | ARTICLE_EXPLAINS_PRODUCT",
    ),
    from_type: str | None = Query(default=None, alias="from_type"),
    from_id: int | None = Query(default=None, alias="from_id"),
    to_type: str | None = Query(default=None, alias="to_type"),
    to_id: int | None = Query(default=None, alias="to_id"),
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeEdgeListResponse:
    if edge_type is not None and edge_type not in KB001_EDGE_TYPES:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="INVALID_EDGE_TYPE",
            message="edge_type must be a KB-001 freeze type",
            details=[{"field": "edge_type", "message": f"allowed={list(KB001_EDGE_TYPES)}"}],
        )
    items, total = await knowledge_crud.list_edges(
        db,
        edge_type=edge_type,
        from_node_type=from_type,
        from_node_id=from_id,
        to_node_type=to_type,
        to_node_id=to_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return KnowledgeEdgeListResponse(
        items=[KnowledgeEdgeResponse.model_validate(e) for e in items],
        total=total,
    )


@router.get(
    "/products/{product_id}/neighborhood",
    response_model=ProductNeighborhoodResponse,
    summary="Depth-1 knowledge neighborhood for a product",
)
async def product_neighborhood(
    product_id: int,
    db: AsyncSession = Depends(get_db),
) -> ProductNeighborhoodResponse:
    data = await knowledge_crud.get_product_neighborhood(db, product_id)
    return ProductNeighborhoodResponse(
        product_id=product_id,
        belongs_to_category=(
            KnowledgeEdgeResponse.model_validate(data["belongs_to_category"])
            if data["belongs_to_category"] is not None
            else None
        ),
        branded_as=(
            KnowledgeEdgeResponse.model_validate(data["branded_as"])
            if data["branded_as"] is not None
            else None
        ),
        explained_by_articles=[
            KnowledgeEdgeResponse.model_validate(e)
            for e in data["explained_by_articles"]
        ],
    )


@router.post(
    "/projections/sync",
    response_model=ProjectionSyncResponse,
    summary="Project SoR soft-links into knowledge_edges (admin, Category A local)",
)
async def sync_knowledge_projections(
    body: ProjectionSyncRequest | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_super_admin),
) -> ProjectionSyncResponse:
    payload = body or ProjectionSyncRequest()
    stats = await sync_projections(
        db,
        product_ids=payload.product_ids,
        article_ids=payload.article_ids,
    )
    await db.commit()
    return ProjectionSyncResponse(**stats)
