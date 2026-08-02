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


# --- Prompt 11A Property Dictionary (admin read) ---

DictionaryStatus = Literal["draft", "active", "deprecated"]
PropertyDataType = Literal[
    "boolean",
    "integer",
    "number",
    "quantity",
    "range",
    "enum",
    "string",
    "string_array",
    "ref_standard",
    "ref_document",
]
UnitDimension = Literal["length", "angle", "mass", "dimensionless", "hardness"]


class KnowledgeUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dimension: UnitDimension
    canonical_code: str
    aliases: list[Any] = Field(default_factory=list)
    conversion_table_version: str | None = None
    label_en: str | None = None
    label_fa: str | None = None
    status: DictionaryStatus
    seed_version: str | None = None
    seed_checksum: str | None = None


class KnowledgeUnitListResponse(BaseModel):
    items: list[KnowledgeUnitResponse]
    total: int


class KnowledgePropertyAliasResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    definition_id: str
    alias: str
    alias_normalized: str
    source_kind: str
    language: str | None = None
    status: DictionaryStatus


class KnowledgePropertyDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    definition_id: str
    key: str
    data_type: PropertyDataType
    unit_dimension: str | None = None
    default_unit: str | None = None
    label_en: str
    label_fa: str
    description_en: str | None = None
    description_fa: str | None = None
    validation: dict[str, Any] = Field(default_factory=dict)
    enum_values: list[Any] | None = None
    comparable: bool
    filterable: bool
    customer_facing: bool
    version: str
    status: DictionaryStatus
    steward: str | None = None
    supersedes_definition_id: str | None = None
    seed_version: str | None = None
    seed_checksum: str | None = None
    aliases: list[KnowledgePropertyAliasResponse] = Field(default_factory=list)


class KnowledgePropertyDefinitionListResponse(BaseModel):
    items: list[KnowledgePropertyDefinitionResponse]
    total: int


class KnowledgePropertyAliasListResponse(BaseModel):
    items: list[KnowledgePropertyAliasResponse]
    total: int
