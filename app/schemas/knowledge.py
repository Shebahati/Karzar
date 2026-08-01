"""Pydantic schemas for Knowledge Graph wave-1 read/sync APIs (KB-001)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

KB001EdgeType = Literal[
    "PRODUCT_BELONGS_TO_CATEGORY",
    "PRODUCT_BRANDED_AS",
    "ARTICLE_EXPLAINS_PRODUCT",
]

EdgeStatus = Literal["asserted", "published", "rejected", "deprecated"]
NodeType = Literal["product", "category", "brand", "article"]


class KnowledgeEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edge_type: KB001EdgeType
    from_node_type: NodeType
    from_node_id: int
    to_node_type: NodeType
    to_node_id: int
    status: EdgeStatus
    source_kind: str
    source_ref: str | None = None
    recorded_at: datetime
    recorder: str
    confidence: Decimal | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class KnowledgeEdgeListResponse(BaseModel):
    items: list[KnowledgeEdgeResponse]
    total: int


class ProductNeighborhoodResponse(BaseModel):
    product_id: int
    belongs_to_category: KnowledgeEdgeResponse | None = None
    branded_as: KnowledgeEdgeResponse | None = None
    explained_by_articles: list[KnowledgeEdgeResponse] = Field(default_factory=list)


class ProjectionSyncRequest(BaseModel):
    """Optional scopes; empty = project all products + articles (local Category A)."""

    product_ids: list[int] | None = None
    article_ids: list[int] | None = None


class ProjectionSyncResponse(BaseModel):
    products_scanned: int
    articles_scanned: int
    edges_upserted: int
    edges_deprecated: int
