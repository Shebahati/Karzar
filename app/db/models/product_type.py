"""Product Type engineering-classification aggregate (ADR-015 Hybrid).

PT-W1: core identity + lifecycle.
PT-W2: Product Type Definitions + Attribute Memberships (no readout, Facts, seeds).
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base

if TYPE_CHECKING:
    from app.db.models.product import Product


class ProductTypeStatus(str, enum.Enum):
    """Lifecycle for Product Type rows (SPEC-canonical-product-type-model §6.4)."""

    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class ProductTypeDefinitionStatus(str, enum.Enum):
    """Definition lifecycle (PT-W2): only draft is mutable."""

    DRAFT = "draft"
    ACTIVE = "active"
    RETIRED = "retired"


class MembershipRequiredness(str, enum.Enum):
    """Attribute membership requiredness vocabulary (PT-W2 closed set)."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    CONDITIONAL = "conditional"
    FORBIDDEN = "forbidden"


DEFINITION_STATUSES = frozenset(s.value for s in ProductTypeDefinitionStatus)
MEMBERSHIP_REQUIREDNESS = frozenset(s.value for s in MembershipRequiredness)
EVIDENCE_REQUIREMENT_OVERRIDES = frozenset({"required", "recommended", "not_required"})

# validation_overrides may narrow constraints only — never redefine identity.
FORBIDDEN_VALIDATION_OVERRIDE_KEYS = frozenset(
    {
        "data_type",
        "unit_dimension",
        "key",
        "definition_id",
        "label_en",
        "label_fa",
        "canonical_key",
        "meaning",
    }
)
ALLOWED_VALIDATION_OVERRIDE_KEYS = frozenset(
    {
        "min",
        "max",
        "min_inclusive",
        "max_inclusive",
        "enum_subset",
        "pattern",
        "max_length",
        "min_length",
        "precision",
        "scale",
    }
)


class ProductType(Base):
    """First-class engineering Product Type (not commerce Category)."""

    __tablename__ = "product_types"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','retired')",
            name="ck_product_types_status",
        ),
        Index("ix_product_types_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    name_fa: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Stored as String + CHECK (KnowledgeEdge / OrderStatus pattern) — not a PG ENUM.
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProductTypeStatus.DRAFT.value,
        server_default=ProductTypeStatus.DRAFT.value,
    )

    products: Mapped[list[Product]] = relationship(
        "Product",
        back_populates="product_type",
        # "all": never null loaded Product FKs on ProductType delete; DB RESTRICT/NO ACTION must fire.
        passive_deletes="all",
    )
    definitions: Mapped[list[ProductTypeDefinition]] = relationship(
        "ProductTypeDefinition",
        back_populates="product_type",
        passive_deletes="all",
    )

    def __str__(self) -> str:
        return self.code


class ProductTypeDefinition(Base):
    """Versioned engineering Definition for one Product Type (PT-W2).

    Ownership: whether/how Property Dictionary properties apply to a Product Type.
    Only status=draft rows are mutable. active/retired are historical and immutable.
    """

    __tablename__ = "product_type_definitions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','retired')",
            name="ck_product_type_definitions_status",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_product_type_definitions_version_positive",
        ),
        UniqueConstraint(
            "product_type_id",
            "version",
            name="uq_product_type_definitions_type_version",
        ),
        Index("ix_product_type_definitions_product_type_id", "product_type_id"),
        Index("ix_product_type_definitions_status", "status"),
        # At most one active Definition per Product Type (Postgres partial unique).
        Index(
            "uq_product_type_definitions_one_active",
            "product_type_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("product_types.id"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProductTypeDefinitionStatus.DRAFT.value,
        server_default=ProductTypeDefinitionStatus.DRAFT.value,
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    product_type: Mapped[ProductType] = relationship(
        "ProductType",
        back_populates="definitions",
    )
    memberships: Mapped[list[ProductTypeAttributeMembership]] = relationship(
        "ProductTypeAttributeMembership",
        back_populates="definition",
        passive_deletes="all",
        order_by="ProductTypeAttributeMembership.id",
    )


class ProductTypeAttributeMembership(Base):
    """Product-Type-specific applicability of one Property Dictionary definition.

    Does NOT duplicate canonical property identity (key, labels, datatype, units).
    FK target: knowledge_property_definitions.definition_id (11A stable id).
    """

    __tablename__ = "product_type_attribute_memberships"
    __table_args__ = (
        CheckConstraint(
            "requiredness IN ('required','optional','conditional','forbidden')",
            name="ck_pt_attr_memberships_requiredness",
        ),
        CheckConstraint(
            "evidence_requirement_override IS NULL OR "
            "evidence_requirement_override IN "
            "('required','recommended','not_required')",
            name="ck_pt_attr_memberships_evidence_override",
        ),
        UniqueConstraint(
            "product_type_definition_id",
            "property_definition_id",
            name="uq_pt_attr_memberships_definition_property",
        ),
        Index(
            "ix_pt_attr_memberships_definition_id",
            "product_type_definition_id",
        ),
        Index(
            "ix_pt_attr_memberships_property_definition_id",
            "property_definition_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_type_definition_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("product_type_definitions.id"),
        nullable=False,
    )
    # Stable 11A identifier — not the integer PK, matching alias FK convention.
    property_definition_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("knowledge_property_definitions.definition_id"),
        nullable=False,
    )
    requiredness: Mapped[str] = mapped_column(String(32), nullable=False)
    applicability_condition: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    validation_overrides: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    public_visibility_default: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    filterable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    comparable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    display_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_requirement_override: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    definition: Mapped[ProductTypeDefinition] = relationship(
        "ProductTypeDefinition",
        back_populates="memberships",
    )
