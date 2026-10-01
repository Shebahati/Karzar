"""Phase 2B — multi-token identity-oriented catalog search helpers.

Semantics: AND( OR(approved fields match token_i) for each token ).

Surfaces: Product.name, Product.sku, Product.manufacturer_code, Brand.name,
ProductType.code/name_fa/name_en, and string synonyms on active taxonomy nodes
linked to the product's product_type_id.

Synonym contract (canonical PT nodes only):
  - status = active
  - node_type = product_type  (NOT assignment role product_type_bridge)
  - dimension = family  (taxonomy node_type → dimension map)
  - product_type_id = Product.product_type_id (non-null)
  - only top-level JSON array string elements are searchable
  - object/array/number/bool/null elements ignored; non-array → no match, no error

No description/specs/Facts search. No destructive OEM normalization.
"""

from __future__ import annotations

import itertools
import re
from typing import Any, cast

from sqlalchemy import and_, exists, literal, or_, select
from sqlalchemy.sql import ColumnElement

from app.db.models.knowledge import KnowledgeTaxonomyNode
from app.db.models.product import Brand, Product
from app.db.models.product_type import ProductType
from app.utils.storefront_catalog import escape_ilike_pattern

_ARABIC_YE = "ي"
_PERSIAN_YE = "ی"
_ARABIC_KE = "ك"
_PERSIAN_KE = "ک"
_WS_RE = re.compile(r"\s+")

# Canonical Product Type taxonomy nodes use dimension=family
# (see knowledge_taxonomy_service._NODE_TYPE_DIMENSION["product_type"]).
_PT_SYNONYM_NODE_TYPE = "product_type"
_PT_SYNONYM_DIMENSION = "family"
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


def _string_synonym_element_match(token: str, *, dialect_name: str) -> ColumnElement[bool]:
    """Match only top-level JSON-array string elements of ``synonyms``.

    Non-array / unsupported shapes contribute no match and must not error.
    Unique bind name per call so AND-of-ORs does not collide.
    """
    from sqlalchemy import text

    pattern = f"%{escape_ilike_pattern(token)}%"
    param_key = f"syn_pat_{next(_SYN_PARAM_SEQ)}"
    if dialect_name == "sqlite":
        # json_each + type='text' (SQLite JSON1); non-array coerced to [].
        sql = (
            "EXISTS ("
            "SELECT 1 FROM json_each("
            "CASE WHEN json_type(knowledge_taxonomy_nodes.synonyms) = 'array' "
            "THEN knowledge_taxonomy_nodes.synonyms ELSE '[]' END"
            ") AS je "
            f"WHERE je.type = 'text' AND je.value LIKE :{param_key} ESCAPE '\\'"
            ")"
        )
    else:
        # PostgreSQL: jsonb_array_elements + jsonb_typeof = 'string'.
        # #>> '{}' extracts the JSON string scalar without surrounding quotes.
        sql = (
            "EXISTS ("
            "SELECT 1 FROM jsonb_array_elements("
            "CASE WHEN jsonb_typeof(knowledge_taxonomy_nodes.synonyms) = 'array' "
            "THEN knowledge_taxonomy_nodes.synonyms ELSE '[]'::jsonb END"
            ") AS elem "
            f"WHERE jsonb_typeof(elem) = 'string' "
            f"AND (elem #>> '{{}}') ILIKE :{param_key} ESCAPE '\\'"
            ")"
        )
    # text() predicates are ColumnElement-compatible at runtime; mypy sees TextClause.
    return cast(
        ColumnElement[bool],
        text(sql).bindparams(**{param_key: pattern}),
    )


def _synonym_match(token: str, *, dialect_name: str) -> ColumnElement[bool]:
    """EXISTS active Product Type taxonomy synonym for the product's PT.

    Gates (all required):
      - Product.product_type_id IS NOT NULL
      - node.product_type_id == Product.product_type_id
      - node.status == active
      - node.node_type == product_type  (canonical; not assignment role)
      - node.dimension == family
      - string-only top-level synonym array elements
    """
    node = KnowledgeTaxonomyNode
    return exists(
        select(literal(1))
        .select_from(node)
        .where(
            and_(
                Product.product_type_id.is_not(None),
                node.product_type_id == Product.product_type_id,
                node.status == "active",
                node.node_type == _PT_SYNONYM_NODE_TYPE,
                node.dimension == _PT_SYNONYM_DIMENSION,
                _string_synonym_element_match(token, dialect_name=dialect_name),
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
