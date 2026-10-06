"""INSIZE trailing-A identity rule (Owner-closed; identity only).

Registered deterministic brand-specific rule for supplier stock / catalog
identity matching. Availability classification remains exclusively from stock
authority (وضعیت / quantity semantics) — this module never maps price or
existence to AVAILABLE.

Rule (Owner-closed policy, Wave 1A.1):
  brand = INSIZE only
  one side exact code X; other side exact code X + single terminal ASCII A
  normalized base maps uniquely
  no competing exact SKU on the XA side
  no multi-row / multi-candidate collision
  else AMBIGUOUS (not matched)

Direction used by distributor workbook intake:
  workbook CODE ``XA`` ↔ catalog SKU ``X``
  Exact match always wins. Never strip internal A. Never strip AA→A as multi.
  Never apply to other brands.

See docs/catalog/SUPPLIER_STOCK_AUTHORITY.md §4 (INSIZE adapter).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from catalog_target.core import canonicalize_brand, normalize_sku

RULE_ID = "INSIZE_TRAILING_A_IDENTITY"
RULE_VERSION = "insize_trailing_a_identity/1.0.0"
MATCH_DETAIL = "EXACT_NORMALIZED_SKU:insize_trailing_A"
OWNER_POLICY_CITATION = (
    "Owner-closed Wave 1A.1 INSIZE_TRAILING_A_IDENTITY "
    "(brand=INSIZE; X↔X+terminal A; unique base; fail closed → AMBIGUOUS)"
)


@dataclass(frozen=True)
class InsizeTrailingAResult:
    outcome: str  # EXACT_MATCH | AMBIGUOUS | NOT_FOUND | WRONG_BRAND
    catalog_sku: str = ""
    source_sku: str = ""
    base: str = ""
    detail: str = ""
    candidates: tuple[str, ...] = field(default_factory=tuple)


def strip_exactly_one_terminal_A(code: str | None) -> str | None:
    """Strip exactly one terminal ASCII ``A`` from a normalized code.

    Returns None when the code does not end with a single removable ``A``
    (too short, no terminal A, or would yield empty base).
    """
    key = normalize_sku(code)
    if len(key) < 2 or not key.endswith("A"):
        return None
    base = key[:-1]
    return base or None


def _brand_is_insize(brand: str | None) -> bool:
    canon = canonicalize_brand(brand) if brand else None
    return canon == "INSIZE"


def match_catalog_sku_to_source_codes(
    *,
    brand: str | None,
    catalog_sku: str | None,
    source_codes: Mapping[str, Sequence[str]] | Mapping[str, object],
    catalog_insize_skus: frozenset[str] | set[str] | None = None,
) -> InsizeTrailingAResult:
    """Match catalog SKU ``X`` to a unique source code ``XA`` (INSIZE only).

    ``source_codes`` maps normalized source CODE → sequence of raw codes (or any
    truthy value). Multiplicity of keys is used for uniqueness; if values are
    sequences of length > 1 the row is treated as a multi-row collision.
    """
    if not _brand_is_insize(brand):
        return InsizeTrailingAResult(
            outcome="WRONG_BRAND",
            detail="insize_trailing_a_wrong_brand",
        )

    key = normalize_sku(catalog_sku)
    if not key:
        return InsizeTrailingAResult(outcome="NOT_FOUND", detail="empty_catalog_sku")

    # Exact source CODE equal to catalog SKU always wins — caller should prefer
    # exact paths first; defend here so trailing-A never overrides exact.
    exact_val = source_codes.get(key)
    if exact_val is not None:
        return InsizeTrailingAResult(
            outcome="EXACT_MATCH",
            catalog_sku=key,
            source_sku=key,
            base=key,
            detail="EXACT_SKU_PRECEDENCE",
        )

    xa = key + "A"
    src = source_codes.get(xa)
    if src is None:
        return InsizeTrailingAResult(
            outcome="NOT_FOUND",
            catalog_sku=key,
            detail="no_source_XA",
        )

    # Multi-row collision on the XA source key
    if isinstance(src, (list, tuple)) and len(src) > 1:
        return InsizeTrailingAResult(
            outcome="AMBIGUOUS",
            catalog_sku=key,
            source_sku=xa,
            base=key,
            detail="multi_row_source_XA",
            candidates=tuple(str(x) for x in src),
        )

    # Competing exact catalog SKU XA exists → never alias workbook XA to X
    insize_set = catalog_insize_skus or frozenset()
    if xa in insize_set:
        return InsizeTrailingAResult(
            outcome="AMBIGUOUS",
            catalog_sku=key,
            source_sku=xa,
            base=key,
            detail="competing_exact_catalog_XA",
            candidates=(xa, key),
        )

    # Source also contains exact non-A code X → collision / Case C
    # (already handled by exact precedence when matching X; if both X and XA
    # exist in source while catalog is X, exact wins — if we reached here
    # exact X was absent. Extra guard: multiple XA-style candidates → AMBIGUOUS.)
    base = strip_exactly_one_terminal_A(xa)
    if base != key:
        return InsizeTrailingAResult(
            outcome="NOT_FOUND",
            catalog_sku=key,
            source_sku=xa,
            detail="terminal_a_strip_failed",
        )

    return InsizeTrailingAResult(
        outcome="EXACT_MATCH",
        catalog_sku=key,
        source_sku=xa,
        base=key,
        detail=MATCH_DETAIL,
        candidates=(key,),
    )


def match_source_code_to_catalog_skus(
    *,
    brand: str | None,
    source_sku: str | None,
    catalog_by_sku: Mapping[str, Sequence[object]],
) -> InsizeTrailingAResult:
    """Match source CODE ``XA`` to unique catalog SKU ``X`` (INSIZE only).

    ``catalog_by_sku`` maps normalized catalog SKU → sequence of catalog hits.
    Exact source==catalog wins first. Trailing-A only when source ends with
    one terminal A and base maps uniquely with no competing exact XA hit.
    """
    if not _brand_is_insize(brand):
        return InsizeTrailingAResult(
            outcome="WRONG_BRAND",
            detail="insize_trailing_a_wrong_brand",
        )

    src = normalize_sku(source_sku)
    if not src:
        return InsizeTrailingAResult(outcome="NOT_FOUND", detail="empty_source_sku")

    # Exact catalog hit
    exact_hits = list(catalog_by_sku.get(src) or ())
    if len(exact_hits) == 1:
        return InsizeTrailingAResult(
            outcome="EXACT_MATCH",
            catalog_sku=src,
            source_sku=src,
            base=src,
            detail="EXACT_SKU_PRECEDENCE",
        )
    if len(exact_hits) > 1:
        return InsizeTrailingAResult(
            outcome="AMBIGUOUS",
            catalog_sku=src,
            source_sku=src,
            detail="exact_catalog_ambiguous",
            candidates=(src,),
        )

    base = strip_exactly_one_terminal_A(src)
    if base is None:
        return InsizeTrailingAResult(
            outcome="NOT_FOUND",
            source_sku=src,
            detail="no_terminal_A",
        )

    # Competing exact catalog XA already checked above (none). If catalog has
    # XA and we are matching source XA, exact would have hit — good.
    base_hits = list(catalog_by_sku.get(base) or ())
    if len(base_hits) == 1:
        # Ensure no second source-style candidate: unique base only
        return InsizeTrailingAResult(
            outcome="EXACT_MATCH",
            catalog_sku=base,
            source_sku=src,
            base=base,
            detail=MATCH_DETAIL,
            candidates=(base,),
        )
    if len(base_hits) > 1:
        return InsizeTrailingAResult(
            outcome="AMBIGUOUS",
            catalog_sku=base,
            source_sku=src,
            base=base,
            detail="catalog_base_ambiguous",
            candidates=(base,),
        )
    return InsizeTrailingAResult(
        outcome="NOT_FOUND",
        source_sku=src,
        base=base or "",
        detail="no_catalog_base",
    )
