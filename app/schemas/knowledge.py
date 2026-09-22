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


# --- PT-W2 Product Type Definitions + Attribute Memberships (admin) ---

DefinitionStatus = Literal["draft", "active", "retired"]
MembershipRequirednessLiteral = Literal[
    "required", "optional", "conditional", "forbidden"
]
EvidenceRequirementOverride = Literal["required", "recommended", "not_required"]


class ProductTypeAttributeMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_type_definition_id: int
    property_definition_id: str
    requiredness: MembershipRequirednessLiteral
    applicability_condition: dict[str, Any] = Field(default_factory=dict)
    validation_overrides: dict[str, Any] = Field(default_factory=dict)
    public_visibility_default: bool | None = None
    filterable: bool | None = None
    comparable: bool | None = None
    display_group: str | None = None
    display_order: int | None = None
    evidence_requirement_override: EvidenceRequirementOverride | None = None
    created_at: datetime
    updated_at: datetime


class ProductTypeDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_type_id: int
    version: int
    status: DefinitionStatus
    change_reason: str | None = None
    reviewed_by_user_id: int | None = None
    activated_at: datetime | None = None
    notes: str | None = None
    memberships: list[ProductTypeAttributeMembershipResponse] = Field(
        default_factory=list
    )
    created_at: datetime
    updated_at: datetime


class ProductTypeDefinitionListResponse(BaseModel):
    items: list[ProductTypeDefinitionResponse]
    total: int


class ProductTypeDefinitionCreateRequest(BaseModel):
    """Create a draft Definition. Version omitted => max(existing)+1 (or 1)."""

    notes: str | None = None
    version: int | None = Field(default=None, ge=1)


class ProductTypeAttributeMembershipCreateRequest(BaseModel):
    property_definition_id: str = Field(min_length=1, max_length=64)
    requiredness: MembershipRequirednessLiteral
    applicability_condition: dict[str, Any] = Field(default_factory=dict)
    validation_overrides: dict[str, Any] = Field(default_factory=dict)
    public_visibility_default: bool | None = None
    filterable: bool | None = None
    comparable: bool | None = None
    display_group: str | None = Field(default=None, max_length=64)
    display_order: int | None = None
    evidence_requirement_override: EvidenceRequirementOverride | None = None


class ProductTypeAttributeMembershipUpdateRequest(BaseModel):
    property_definition_id: str | None = Field(default=None, min_length=1, max_length=64)
    requiredness: MembershipRequirednessLiteral | None = None
    applicability_condition: dict[str, Any] | None = None
    validation_overrides: dict[str, Any] | None = None
    public_visibility_default: bool | None = None
    filterable: bool | None = None
    comparable: bool | None = None
    display_group: str | None = Field(default=None, max_length=64)
    display_order: int | None = None
    evidence_requirement_override: EvidenceRequirementOverride | None = None


class ProductTypeDefinitionActivateRequest(BaseModel):
    """Activation payload. Reviewer identity comes from auth, not this body."""

    change_reason: str = Field(min_length=1, max_length=4000)


# --- PT-W3A Product Type stewardship + manual assignment (admin) ---

ProductTypeLifecycleStatus = Literal["draft", "active", "retired"]


class ProductTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    slug: str
    name_fa: str
    name_en: str | None = None
    description: str | None = None
    status: ProductTypeLifecycleStatus


class ProductTypeListResponse(BaseModel):
    items: list[ProductTypeResponse]
    total: int


class ProductTypeCreateRequest(BaseModel):
    """Create always starts as draft. status is not accepted."""

    code: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=200)
    name_fa: str = Field(min_length=1, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    description: str | None = None


class ProductTypeUpdateRequest(BaseModel):
    """Draft-only presentation metadata. code/status are not editable here."""

    slug: str | None = Field(default=None, min_length=1, max_length=200)
    name_fa: str | None = Field(default=None, min_length=1, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    description: str | None = None


class ProductTypeActivateRequest(BaseModel):
    """Activation payload. Actor identity comes from auth, not this body."""

    change_reason: str = Field(min_length=1, max_length=4000)


class ProductTypeAssignmentSummary(BaseModel):
    id: int
    code: str
    slug: str
    name_fa: str
    name_en: str | None = None
    status: ProductTypeLifecycleStatus


class ProductTypeAssignmentResponse(BaseModel):
    product_id: int
    current_product_type_id: int | None = None
    product_type: ProductTypeAssignmentSummary | None = None
    active_definition_id: int | None = None


class ProductTypeAssignmentRequest(BaseModel):
    """Manual reviewed assignment. null clears when allowed."""

    product_type_id: int | None = None
    change_reason: str = Field(min_length=1, max_length=4000)


# --- Prompt 12 Facts + Revisions (admin) ---

FactStatus = Literal["asserted", "published", "disputed", "deprecated"]


class KnowledgeFactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_id: int
    definition_id: str
    product_type_definition_id: int | None = None
    value: Any
    unit: str | None = None
    qualifier: str | None = None
    status: FactStatus
    source_id: str
    confidence: Decimal | None = None
    recorded_at: datetime
    recorder: str
    created_at: datetime
    updated_at: datetime


class KnowledgeFactListResponse(BaseModel):
    items: list[KnowledgeFactResponse]
    total: int


class KnowledgeFactCreateRequest(BaseModel):
    definition_id: str = Field(min_length=1, max_length=64)
    value: Any
    unit: str | None = Field(default=None, max_length=32)
    qualifier: str | None = Field(default=None, max_length=64)
    source_id: str = Field(min_length=1, max_length=255)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)


class KnowledgeFactUpdateRequest(BaseModel):
    value: Any | None = None
    unit: str | None = Field(default=None, max_length=32)
    qualifier: str | None = Field(default=None, max_length=64)
    source_id: str | None = Field(default=None, min_length=1, max_length=255)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    change_reason: str | None = Field(default=None, max_length=4000)


class KnowledgeFactLifecycleRequest(BaseModel):
    change_reason: str = Field(min_length=1, max_length=4000)


class KnowledgeFactRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fact_id: int
    revision_number: int
    value: Any
    unit: str | None = None
    qualifier: str | None = None
    status: FactStatus
    source_id: str
    confidence: Decimal | None = None
    product_type_definition_id: int | None = None
    recorded_at: datetime
    recorder: str
    change_reason: str | None = None
    created_at: datetime


class KnowledgeFactRevisionListResponse(BaseModel):
    items: list[KnowledgeFactRevisionResponse]
    total: int


# --- Prompt 13 Evidence + Taxonomy (admin) ---

EvidenceArtifactKind = Literal[
    "oem_catalogue",
    "datasheet",
    "standard",
    "certificate",
    "lab_report",
    "manual",
    "other",
]

TaxonomyDimension = Literal[
    "domain",
    "family",
    "application",
    "industry",
    "technical",
    "commerce_category",
]

TaxonomyStatus = Literal["draft", "active", "deprecated"]

ClassificationAssignmentRole = Literal[
    "application",
    "industry",
    "technical",
    "secondary_domain",
    "product_type_bridge",
]


class EvidenceArtifactCreateRequest(BaseModel):
    artifact_id: str = Field(min_length=1, max_length=64)
    kind: EvidenceArtifactKind
    title: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=1024)
    source_ref: str | None = Field(default=None, max_length=255)
    checksum_sha256: str | None = Field(default=None, max_length=64)
    publisher: str | None = Field(default=None, max_length=255)
    document_version: str | None = Field(default=None, max_length=64)
    notes: str | None = None


class EvidenceArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artifact_id: str
    kind: EvidenceArtifactKind
    title: str | None = None
    source_url: str | None = None
    source_ref: str | None = None
    checksum_sha256: str | None = None
    publisher: str | None = None
    document_version: str | None = None
    recorded_at: datetime
    recorder: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class EvidenceArtifactListResponse(BaseModel):
    items: list[EvidenceArtifactResponse]
    total: int


class EvidenceLinkCreateRequest(BaseModel):
    artifact_id: int
    locator: dict[str, Any] | None = None
    notes: str | None = None


# --- Prompt 41 governed SKU-unit batch assert ---


class KnowledgeBatchAssertFactItem(BaseModel):
    definition_id: str = Field(min_length=1, max_length=64)
    value: Any
    unit: str | None = Field(default=None, max_length=32)
    qualifier: str | None = Field(default=None, max_length=64)
    source_id: str = Field(min_length=1, max_length=255)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)


class KnowledgeBatchAssertEvidenceItem(BaseModel):
    artifact_id: int
    locator: dict[str, Any]
    notes: str | None = None


class KnowledgeBatchAssertRequest(BaseModel):
    """Immutable Batch 1 SKU unit payload (manifest-pinned)."""

    manifest_sha256: str = Field(min_length=64, max_length=64)
    sku: str = Field(min_length=1, max_length=50)
    product_type_id: int
    definition_id: int
    facts: list[KnowledgeBatchAssertFactItem]
    evidence_links: list[KnowledgeBatchAssertEvidenceItem]
    change_reason: str = Field(min_length=1, max_length=4000)


class KnowledgeBatchAssertFactSummary(BaseModel):
    id: int
    definition_id: str
    status: FactStatus
    source_id: str


class KnowledgeBatchAssertLinkSummary(BaseModel):
    id: int
    fact_id: int | None = None
    artifact_id: int
    relation_type: Literal["FACT_SUPPORTED_BY", "EDGE_SUPPORTED_BY"]


class KnowledgeBatchAssertResponse(BaseModel):
    product_id: int
    sku: str
    product_type_id: int | None = None
    definition_id: int
    manifest_sha256: str
    facts: list[KnowledgeBatchAssertFactSummary]
    evidence_links: list[KnowledgeBatchAssertLinkSummary]
    published_count: int
    specifications_fingerprint: str


class EvidenceLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artifact_id: int
    target_type: Literal["fact", "edge"]
    fact_id: int | None = None
    edge_id: int | None = None
    relation_type: Literal["FACT_SUPPORTED_BY", "EDGE_SUPPORTED_BY"]
    locator: dict[str, Any]
    locator_fingerprint: str
    recorded_at: datetime
    recorder: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class EvidenceLinkListResponse(BaseModel):
    items: list[EvidenceLinkResponse]
    total: int


class TaxonomyNodeCreateRequest(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)
    dimension: TaxonomyDimension
    node_type: str = Field(min_length=1, max_length=64)
    slug: str = Field(min_length=1, max_length=128)
    name_fa: str = Field(min_length=1, max_length=255)
    name_en: str | None = Field(default=None, max_length=255)
    parent_id: int | None = None
    synonyms: list[Any] | None = None
    seo_meta_title: str | None = Field(default=None, max_length=255)
    seo_meta_description: str | None = None
    commerce_category_id: int | None = None
    product_type_id: int | None = None
    sort_order: int | None = None
    steward: str | None = Field(default=None, max_length=128)


class TaxonomyNodeStatusRequest(BaseModel):
    status: TaxonomyStatus


class TaxonomyNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    node_id: str
    dimension: TaxonomyDimension
    node_type: str
    slug: str
    name_fa: str
    name_en: str | None = None
    parent_id: int | None = None
    status: TaxonomyStatus
    synonyms: list[Any]
    seo_meta_title: str | None = None
    seo_meta_description: str | None = None
    commerce_category_id: int | None = None
    product_type_id: int | None = None
    sort_order: int | None = None
    steward: str | None = None
    created_at: datetime
    updated_at: datetime


class ClassificationAssignmentCreateRequest(BaseModel):
    taxonomy_node_id: int
    assignment_role: ClassificationAssignmentRole
    is_primary: bool = False
    source_ref: str | None = Field(default=None, max_length=255)
    notes: str | None = None


class ClassificationAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    taxonomy_node_id: int
    assignment_role: ClassificationAssignmentRole
    is_primary: bool
    source_ref: str | None = None
    recorded_at: datetime
    recorder: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ClassificationAssignmentListResponse(BaseModel):
    items: list[ClassificationAssignmentResponse]
    total: int
