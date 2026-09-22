"""Prompt 13 Industrial Taxonomy runtime + classification assignments.

Primary Product Type identity remains products.product_type_id (ADR-015 Hybrid).
PRODUCT_CLASSIFIED_AS KnowledgeEdge projection is deferred — assignment table is
the runtime source for secondary multi-dimensional classification.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, api_error
from app.crud.audit import record_audit_log
from app.db.models.knowledge import (
    CLASSIFICATION_ASSIGNMENT_ROLES,
    TAXONOMY_DIMENSIONS,
    TAXONOMY_NODE_TYPES,
    TAXONOMY_STATUSES,
    KnowledgeClassificationAssignment,
    KnowledgeTaxonomyNode,
)
from app.db.models.product import Category, Product
from app.db.models.product_type import ProductType
from app.db.models.user import User

# node_type → expected dimension
_NODE_TYPE_DIMENSION: dict[str, str] = {
    "industrial_domain": "domain",
    "tool_family": "family",
    "knowledge_category": "family",
    "product_subcategory": "family",
    "product_type": "family",
    "application": "application",
    "industry": "industry",
    "technical_class": "technical",
    "commerce_category": "commerce_category",
}


def _actor_label(actor: User) -> str:
    return actor.phone_number or f"user:{actor.id}"


def _validate_node_type_dimension(node_type: str, dimension: str) -> None:
    expected = _NODE_TYPE_DIMENSION.get(node_type)
    if expected is None:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="unsupported taxonomy node_type",
            details=[{"field": "node_type", "message": "unsupported"}],
        )
    if expected != dimension:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="node_type does not match dimension",
            details=[
                {
                    "field": "node_type",
                    "message": f"expected dimension {expected}",
                }
            ],
        )


async def create_taxonomy_node(
    db: AsyncSession,
    *,
    node_id: str,
    dimension: str,
    node_type: str,
    slug: str,
    name_fa: str,
    name_en: str | None,
    parent_id: int | None,
    synonyms: list[Any] | None,
    seo_meta_title: str | None,
    seo_meta_description: str | None,
    commerce_category_id: int | None,
    product_type_id: int | None,
    sort_order: int | None,
    steward: str | None,
    actor: User,
) -> KnowledgeTaxonomyNode:
    if dimension not in TAXONOMY_DIMENSIONS:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="invalid taxonomy dimension",
            details=[{"field": "dimension", "message": "unsupported"}],
        )
    if node_type not in TAXONOMY_NODE_TYPES:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="invalid taxonomy node_type",
            details=[{"field": "node_type", "message": "unsupported"}],
        )
    _validate_node_type_dimension(node_type, dimension)

    nid = (node_id or "").strip()
    slug_v = (slug or "").strip()
    if not nid or not slug_v or not (name_fa or "").strip():
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="node_id, slug, and name_fa are required",
        )

    parent: KnowledgeTaxonomyNode | None = None
    if parent_id is not None:
        parent = await db.get(KnowledgeTaxonomyNode, parent_id)
        if parent is None:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="parent taxonomy node not found",
                details=[{"field": "parent_id", "message": "not found"}],
            )
        if parent.dimension != dimension:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="parent must be in the same taxonomy dimension",
                details=[{"field": "parent_id", "message": "cross-dimension parent"}],
            )

    if commerce_category_id is not None:
        cat = await db.get(Category, commerce_category_id)
        if cat is None:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="commerce_category_id not found",
                details=[{"field": "commerce_category_id", "message": "not found"}],
            )

    if product_type_id is not None:
        pt = await db.get(ProductType, product_type_id)
        if pt is None:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="product_type_id not found",
                details=[{"field": "product_type_id", "message": "not found"}],
            )
        if node_type != "product_type":
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="product_type_id is only valid for product_type nodes",
                details=[{"field": "product_type_id", "message": "invalid"}],
            )

    row = KnowledgeTaxonomyNode(
        node_id=nid,
        dimension=dimension,
        node_type=node_type,
        slug=slug_v,
        name_fa=name_fa.strip(),
        name_en=name_en,
        parent_id=parent_id,
        status="draft",
        synonyms=synonyms or [],
        seo_meta_title=seo_meta_title,
        seo_meta_description=seo_meta_description,
        commerce_category_id=commerce_category_id,
        product_type_id=product_type_id,
        sort_order=sort_order,
        steward=steward,
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="taxonomy node_id or dimension/slug already exists",
            details=[{"field": "node", "message": "duplicate"}],
        ) from exc

    await record_audit_log(
        db,
        actor_user_id=actor.id,
        action="knowledge_taxonomy_node.create",
        entity_type="knowledge_taxonomy_node",
        entity_id=str(row.id),
        details={"node_id": nid, "dimension": dimension, "slug": slug_v},
    )
    return row


async def get_taxonomy_node(db: AsyncSession, node_pk: int) -> KnowledgeTaxonomyNode:
    row = await db.get(KnowledgeTaxonomyNode, node_pk)
    if row is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Taxonomy node not found",
        )
    return row


async def update_taxonomy_node_status(
    db: AsyncSession,
    *,
    node_pk: int,
    status_value: str,
    actor: User,
) -> KnowledgeTaxonomyNode:
    if status_value not in TAXONOMY_STATUSES:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="invalid taxonomy status",
            details=[{"field": "status", "message": "unsupported"}],
        )
    node = await get_taxonomy_node(db, node_pk)
    if node.parent_id is not None and node.parent_id == node.id:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="taxonomy parent_id cannot equal self",
            details=[{"field": "parent_id", "message": "self-reference"}],
        )
    prev = node.status
    node.status = status_value
    await db.flush()
    await record_audit_log(
        db,
        actor_user_id=actor.id,
        action="knowledge_taxonomy_node.status",
        entity_type="knowledge_taxonomy_node",
        entity_id=str(node.id),
        details={"from": prev, "to": status_value},
    )
    return node


async def create_classification_assignment(
    db: AsyncSession,
    *,
    product_id: int,
    taxonomy_node_id: int,
    assignment_role: str,
    is_primary: bool,
    source_ref: str | None,
    notes: str | None,
    actor: User,
) -> KnowledgeClassificationAssignment:
    if assignment_role not in CLASSIFICATION_ASSIGNMENT_ROLES:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="invalid assignment_role",
            details=[{"field": "assignment_role", "message": "unsupported"}],
        )

    product = await db.get(Product, product_id)
    if product is None:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            error_code=ErrorCode.NOT_FOUND,
            message="Product not found",
        )
    node = await get_taxonomy_node(db, taxonomy_node_id)
    if node.status == "deprecated":
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="cannot assign a deprecated taxonomy node",
            details=[{"field": "taxonomy_node_id", "message": "deprecated"}],
        )
    if node.status != "active":
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="taxonomy node must be active for new assignments",
            details=[{"field": "taxonomy_node_id", "message": "not active"}],
        )

    # Role ↔ dimension coherence (minimal).
    role_dim = {
        "application": "application",
        "industry": "industry",
        "technical": "technical",
        "secondary_domain": "domain",
        "product_type_bridge": "family",
    }
    if node.dimension != role_dim[assignment_role]:
        raise api_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code=ErrorCode.VALIDATION_FAILED,
            message="assignment_role does not match taxonomy node dimension",
            details=[{"field": "assignment_role", "message": "dimension mismatch"}],
        )

    if assignment_role == "product_type_bridge":
        if node.node_type != "product_type" or node.product_type_id is None:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="product_type_bridge requires a product_type node with product_type_id",
                details=[{"field": "taxonomy_node_id", "message": "missing Product Type bridge"}],
            )
        if product.product_type_id is None:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message="Product has no primary product_type_id for bridge agreement",
                details=[{"field": "product_type_id", "message": "missing"}],
            )
        if product.product_type_id != node.product_type_id:
            raise api_error(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                error_code=ErrorCode.VALIDATION_FAILED,
                message=(
                    "primary Product Type conflict: taxonomy bridge must resolve "
                    "to products.product_type_id"
                ),
                details=[
                    {
                        "field": "product_type_id",
                        "message": "bridge disagrees with primary FK",
                    }
                ],
            )

    row = KnowledgeClassificationAssignment(
        product_id=product.id,
        taxonomy_node_id=node.id,
        assignment_role=assignment_role,
        is_primary=bool(is_primary),
        source_ref=source_ref,
        recorded_at=datetime.now(UTC),
        recorder=_actor_label(actor),
        notes=notes,
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            error_code=ErrorCode.CONFLICT,
            message="duplicate classification assignment",
            details=[{"field": "assignment", "message": "duplicate"}],
        ) from exc

    await record_audit_log(
        db,
        actor_user_id=actor.id,
        action="knowledge_classification_assignment.create",
        entity_type="knowledge_classification_assignment",
        entity_id=str(row.id),
        details={
            "product_id": product.id,
            "taxonomy_node_id": node.id,
            "assignment_role": assignment_role,
        },
    )
    return row


async def list_assignments_for_product(
    db: AsyncSession, product_id: int
) -> list[KnowledgeClassificationAssignment]:
    stmt = (
        select(KnowledgeClassificationAssignment)
        .where(KnowledgeClassificationAssignment.product_id == product_id)
        .order_by(KnowledgeClassificationAssignment.id.asc())
    )
    return list((await db.execute(stmt)).scalars().all())
