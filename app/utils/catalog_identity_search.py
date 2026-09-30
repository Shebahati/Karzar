"""Phase 2B — multi-token identity-oriented catalog search helpers.

Semantics: AND( OR(approved fields match token_i) for each token ).

Surfaces: Product.name, Product.sku, Product.manufacturer_code, Brand.name,
ProductType.code/name_fa/name_en, and string synonyms on active taxonomy nodes
linked to the product's product_type_id.

No description/specs/Facts search. No destructive OEM normalization.
"""

from __future__ import annotations

import itertools
import re
from typing import Any

from sqlalchemy import and_, cast, exists, literal, or_, select
from sqlalchemy.sql import ColumnElement
from sqlalchemy.types import String

from app.db.models.knowledge import KnowledgeTaxonomyNode
from app.db.models.product import Brand, Product
from app.db.models.product_type import ProductType
from app.utils.storefront_catalog import escape_ilike_pattern

_ARABIC_YE = "ي"
_PERSIAN_YE = "ی"
_ARABIC_KE = "ك"
_PERSIAN_KE = "ک"
_WS_RE = re.compile(r"\s+")

# Synonym nodes must be active Product Type bridges (not commerce/industry noise).
_SYNONYM_DIMENSIONS = frozenset({"domain", "family", "technical"})
_SYN_PARAM_SEQ = itertools.count(1)


def normalize_search_display_token(token: str) -> str:
    """Normalize Persian/Arabic display equivalents for search tokens only."""
    out = token.replace(_ARABIC_YE, _PERSIAN_YE).replace(_ARABIC_KE, _PERSIAN_KE)
    # Arabic-Indic digits → Western (search convenience; does not rewrite stored OEM).
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    out = out.translate(trans)
    return _WS_RE.sub(" ", out).strip()


def tokenize_search_query(search: str) -> list[str]:
    """Split query into significant tokens (whitespace). Empty → []."""
    raw = (search or "").strip()
    if not raw:
        return []
    tokens: list[str] = []
    seen: set[str] = set()
    for part in raw.split():
        tok = normalize_search_display_token(part)
        if not tok or tok in seen:
            continue
        seen.add(tok)
        tokens.append(tok)
    return tokens


def _ilike(column: Any, token: str) -> ColumnElement[bool]:
    pattern = f"%{escape_ilike_pattern(token)}%"
    return column.ilike(pattern, escape="\\")


def _product_type_match(token: str) -> ColumnElement[bool]:
    """EXISTS ProductType rows matching token via product.product_type_id."""
    pt = ProductType
    return exists(
        select(literal(1)).where(
            and_(
                Product.product_type_id.is_not(None),
                Product.product_type_id == pt.id,
                or_(
                    _ilike(pt.code, token),
                    _ilike(pt.name_fa, token),
                    _ilike(pt.name_en, token),
                    _ilike(pt.slug, token),
                ),
            )
        )
    )


def _synonym_match(token: str, *, dialect_name: str) -> ColumnElement[bool]:
    """EXISTS active PT-linked taxonomy synonym for the product's Product Type.

    Contract: only ``status=active`` nodes with ``product_type_id`` matching the
    product and ``dimension`` in {domain, family, technical}. Synonyms JSON is
    matched via cast-to-text so string-array rows are practically usable;
    non-string legacy structures are ignored for matching purposes (documented
    in PHASE-2B-SEARCH-PREVIEW.md).
    """
    node = KnowledgeTaxonomyNode
    pattern = f"%{escape_ilike_pattern(token)}%"
    syn_match = cast(node.synonyms, String).ilike(pattern, escape="\\")
    if dialect_name == "sqlite":
        # json_each expands array elements (SQLite JSON1).
        # Unique bind name per token — AND-of-ORs reuses this clause once per
        # token; a shared :syn_pat name would collide and break multi-token.
        from sqlalchemy import text

        param_key = f"syn_pat_{next(_SYN_PARAM_SEQ)}"
        syn_match = text(
            "EXISTS (SELECT 1 FROM json_each(knowledge_taxonomy_nodes.synonyms) "
            f"AS je WHERE je.value LIKE :{param_key} ESCAPE '\\')"
        ).bindparams(**{param_key: pattern})
    return exists(
        select(literal(1))
        .select_from(node)
        .where(
            and_(
                Product.product_type_id.is_not(None),
                node.product_type_id == Product.product_type_id,
                node.status == "active",
                node.dimension.in_(tuple(_SYNONYM_DIMENSIONS)),
                syn_match,
            )
        )
    )


def token_matches_identity_surfaces(
    token: str,
    *,
    dialect_name: str = "postgresql",
) -> ColumnElement[bool]:
    """OR across approved identity search surfaces for one token."""
    return or_(
        _ilike(Product.name, token),
        _ilike(Product.sku, token),
        and_(
            Product.manufacturer_code.is_not(None),
            _ilike(Product.manufacturer_code, token),
        ),
        Product.brand.has(_ilike(Brand.name, token)),
        _product_type_match(token),
        _synonym_match(token, dialect_name=dialect_name),
    )


def build_identity_search_filter(
    search: str | None,
    *,
    dialect_name: str = "postgresql",
) -> ColumnElement[bool] | None:
    """AND-of-ORs filter, or None when search empty."""
    tokens = tokenize_search_query(search or "")
    if not tokens:
        return None
    return and_(
        *(
            token_matches_identity_surfaces(tok, dialect_name=dialect_name)
            for tok in tokens
        )
    )
