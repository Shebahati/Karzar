"""Deterministic SKU, brand, price, and match primitives.

SKU normalization is conservative: it must not collapse distinct manufacturer
codes (for example ``1114-150`` vs ``1114-150A``). Matching is brand-aware and
exact by default. Fuzzy matches never auto-apply.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

TOMAN_PER_RIAL_DIVISOR = Decimal("10")  # rial / 10 → toman; never inferred

STATES = ("KEEP", "UPDATE", "CREATE", "DEACTIVATE", "REVIEW", "NOOP_INACTIVE_NON_TARGET")

_HYPHEN_RE = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2212\uFE63\uFF0Dـ]")
_WS_RE = re.compile(r"\s+")
_MARKUP_RE = re.compile(
    r"(?<!\d)\+(\d+(?:\.\d+)?)\s*(?:%|٪|درصد)",
    re.IGNORECASE,
)
_ZWNJ_RE = re.compile(r"[\u200c\u200d\ufeff]")

# Historical INSIZE product-list unique-code band. Not a hardcoded universe size.
INSIZE_UNIQUE_SANITY_LOW = 800
INSIZE_UNIQUE_SANITY_HIGH = 950


def fold_token(value: str | None) -> str:
    """Folder/filename compare: drop ZWNJ/whitespace, unify Yeh/Kaf. Do not stem meaning."""
    if value is None:
        return ""
    s = str(value).replace("ي", "ی").replace("ك", "ک")
    s = _ZWNJ_RE.sub("", s)
    s = _WS_RE.sub("", s)
    return s.casefold()


# Canonical brand keys used for matching. Aliases never cross brands.
BRAND_ALIASES: dict[str, str] = {
    "INSIZE": "INSIZE",
    "اینسایز": "INSIZE",
    "TERMA": "TERMA",
    "ترما": "TERMA",
    "DASQUA": "DASQUA",
    "داسکوا": "DASQUA",
    "MITUTOYO": "MITUTOYO",
    "میتوتویو": "MITUTOYO",
    "GUANGLU": "GUANGLU",
    "GL": "GUANGLU",
    "GUANGLU / GL": "GUANGLU",
    "GUANGLU/GL": "GUANGLU",
    "گوانگلو": "GUANGLU",
    "DCOIL": "DCOIL",
    "دی کویل": "DCOIL",
    "SHAMS": "SHAMS",
    "شمس": "SHAMS",
    "ASTPOWER": "ASTPOWER",
    "AST POWER": "ASTPOWER",
    "AST-POWER": "ASTPOWER",
    "AST": "ASTPOWER",
    "AZARSANAT": "ASTPOWER",
    "آذرصنعت": "ASTPOWER",
    "ای اس تی پاور": "ASTPOWER",
}

CURRENCY_ALIASES: dict[str, str] = {
    "TOMAN": "toman",
    "TOMANS": "toman",
    "تومان": "toman",
    "IRT": "toman",
    "RIAL": "rial",
    "RIALS": "rial",
    "IRR": "rial",
    "ریال": "rial",
    "USD": "usd",
    "DOLLAR": "usd",
    "دلار": "usd",
}


def canonicalize_brand(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    key = _WS_RE.sub(" ", raw).upper()
    if key in BRAND_ALIASES:
        return BRAND_ALIASES[key]
    left = key.split("|", 1)[0].strip()
    if left in BRAND_ALIASES:
        return BRAND_ALIASES[left]
    return left or None


def normalize_sku(value: str | None) -> str:
    """Conservative exact-match key. Does not strip trailing letters or slashes."""
    if value is None:
        return ""
    s = str(value).strip().upper()
    s = _HYPHEN_RE.sub("-", s)
    s = s.replace("_", "-")
    s = _WS_RE.sub("", s)
    return s


def suffix_near_miss(left: str, right: str) -> bool:
    """True when codes differ only by a trailing letter suffix (never auto-match)."""
    a, b = normalize_sku(left), normalize_sku(right)
    if not a or not b or a == b:
        return False
    longer, shorter = (a, b) if len(a) > len(b) else (b, a)
    if not longer.startswith(shorter):
        return False
    rest = longer[len(shorter) :]
    return bool(re.fullmatch(r"[A-Z]+", rest))


def parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return Decimal(str(value))
    text = str(value).strip().replace(",", "").replace("٬", "").replace(" ", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def detect_markup_percent(*texts: str | None) -> Decimal | None:
    for text in texts:
        if not text:
            continue
        match = _MARKUP_RE.search(str(text))
        if match:
            return Decimal(match.group(1))
    return None


def canonicalize_currency(value: str | None) -> str | None:
    if value is None:
        return None
    key = _WS_RE.sub(" ", str(value).strip()).upper()
    if not key:
        return None
    return CURRENCY_ALIASES.get(key)


@dataclass(frozen=True)
class PriceConversion:
    raw_source_value: Decimal | None
    source_currency: str | None
    conversion: str
    markup_already_present: bool
    markup_percent: Decimal | None
    base_price_toman: Decimal | None
    review_reason: str | None


def convert_price(
    raw_value: Any,
    *,
    currency: str | None,
    markup_already_present: bool = False,
    apply_markup_percent: Decimal | None = None,
) -> PriceConversion:
    """Convert an explicit-currency source amount to Toman.

    Currency is never inferred. Rial → Toman is ``rial / 10``. Markup already
    present in the source is recorded and not applied again.
    """
    raw = parse_decimal(raw_value)
    canon = canonicalize_currency(currency)
    if raw is None:
        return PriceConversion(
            raw_source_value=None,
            source_currency=canon,
            conversion="none",
            markup_already_present=markup_already_present,
            markup_percent=apply_markup_percent,
            base_price_toman=None,
            review_reason="missing_price",
        )
    if canon is None:
        return PriceConversion(
            raw_source_value=raw,
            source_currency=currency,
            conversion="none",
            markup_already_present=markup_already_present,
            markup_percent=apply_markup_percent,
            base_price_toman=None,
            review_reason="uncertain_currency",
        )
    if canon == "toman":
        toman = raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        conversion = "toman_as_is"
    elif canon == "rial":
        toman = (raw / TOMAN_PER_RIAL_DIVISOR).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        conversion = "rial_div_10"
    else:
        return PriceConversion(
            raw_source_value=raw,
            source_currency=canon,
            conversion="none",
            markup_already_present=markup_already_present,
            markup_percent=apply_markup_percent,
            base_price_toman=None,
            review_reason="unsupported_currency_needs_rate",
        )

    if apply_markup_percent is not None and not markup_already_present:
        factor = Decimal("1") + (apply_markup_percent / Decimal("100"))
        toman = (toman * factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        conversion = f"{conversion}+markup_{apply_markup_percent}%"
    elif apply_markup_percent is not None and markup_already_present:
        conversion = f"{conversion};markup_already_present_{apply_markup_percent}%"

    if toman <= 0:
        return PriceConversion(
            raw_source_value=raw,
            source_currency=canon,
            conversion=conversion,
            markup_already_present=markup_already_present,
            markup_percent=apply_markup_percent,
            base_price_toman=toman,
            review_reason="non_positive_price",
        )
    return PriceConversion(
        raw_source_value=raw,
        source_currency=canon,
        conversion=conversion,
        markup_already_present=markup_already_present,
        markup_percent=apply_markup_percent,
        base_price_toman=toman,
        review_reason=None,
    )


@dataclass
class CurrentProduct:
    id: str | None
    sku: str
    normalized_sku: str
    slug: str | None
    name: str | None
    brand_id: str | None
    brand: str | None
    brand_key: str | None
    category_id: str | None
    base_price: Decimal | None
    is_active: bool | None
    is_available: bool | None
    deleted_at: str | None
    primary_image_url: str | None
    image_count: int | None
    source: str = "unknown"


@dataclass
class TargetSku:
    brand: str
    brand_key: str
    sku: str
    normalized_sku: str
    product_family: str
    source_scope: str
    source_product: str
    provenance: str = ""
    membership_mode: str = "authoritative"
    parse_status: str = "ok"
    duplicate_in_source: bool = False
    parser_confidence: str = "high"


@dataclass
class SourceFile:
    path: str
    brand_key: str | None
    role: str
    available: bool
    reason: str = ""
    sha256: str = ""
    row_count: int | None = None
    markup_percent: Decimal | None = None
    roles: list[str] = field(default_factory=list)
    parse_status: str = "ok"
    source_id: str = ""
    product_family: str = ""
    currency: str | None = None
    membership_mode: str = "authoritative"
    duplicate_copy: bool = False
    parser_confidence: str = "high"


@dataclass
class MatchDecision:
    method: str
    current: CurrentProduct | None = None
    confidence: str = "none"
    review_reason: str | None = None
    candidates: list[str] = field(default_factory=list)


def identity_key(brand_key: str | None, normalized_sku: str) -> tuple[str, str]:
    return (brand_key or "", normalized_sku)


def index_current_products(
    products: list[CurrentProduct],
) -> dict[tuple[str, str], list[CurrentProduct]]:
    index: dict[tuple[str, str], list[CurrentProduct]] = {}
    for product in products:
        key = identity_key(product.brand_key, product.normalized_sku)
        index.setdefault(key, []).append(product)
    return index


def cross_brand_sku_collisions(
    products: list[CurrentProduct] | list[TargetSku],
) -> dict[str, set[str]]:
    by_sku: dict[str, set[str]] = {}
    for item in products:
        sku = item.normalized_sku
        brand = getattr(item, "brand_key", None)
        if not sku or not brand:
            continue
        by_sku.setdefault(sku, set()).add(brand)
    return {sku: brands for sku, brands in by_sku.items() if len(brands) > 1}


def match_brand_sku(
    *,
    brand_key: str,
    normalized_sku: str,
    index: dict[tuple[str, str], list[CurrentProduct]],
    aliases: dict[tuple[str, str], str] | None = None,
    allow_cross_brand: bool = False,
) -> MatchDecision:
    """Exact brand + normalized SKU, then proven aliases. Never fuzzy, never silent cross-brand."""
    if not normalized_sku:
        return MatchDecision(method="unmatchable", review_reason="malformed_sku", confidence="none")

    exact_hits = list(index.get(identity_key(brand_key, normalized_sku), []))
    if len(exact_hits) == 1:
        return MatchDecision(
            method="exact_brand_sku",
            current=exact_hits[0],
            confidence="exact",
        )
    if len(exact_hits) > 1:
        return MatchDecision(
            method="duplicate_current_sku",
            confidence="none",
            review_reason="duplicate_current_sku",
            candidates=[p.sku for p in exact_hits],
        )

    alias_target = (aliases or {}).get((brand_key, normalized_sku))
    if alias_target:
        alias_hits = list(index.get(identity_key(brand_key, normalize_sku(alias_target)), []))
        if len(alias_hits) == 1:
            return MatchDecision(
                method="proven_alias",
                current=alias_hits[0],
                confidence="alias",
            )
        return MatchDecision(
            method="ambiguous_alias",
            confidence="none",
            review_reason="ambiguous_alias",
            candidates=[p.sku for p in alias_hits],
        )

    if allow_cross_brand:
        others = [
            product
            for (bkey, sku), rows in index.items()
            if sku == normalized_sku and bkey != brand_key
            for product in rows
        ]
        if len(others) == 1:
            return MatchDecision(
                method="cross_brand_unique_proof",
                current=others[0],
                confidence="review",
                review_reason="cross_brand_collision",
            )
        if others:
            return MatchDecision(
                method="cross_brand_ambiguous",
                confidence="none",
                review_reason="cross_brand_collision",
                candidates=[p.sku for p in others],
            )

    return MatchDecision(method="none", confidence="none")


def commerce_ready(
    *,
    target_member: bool,
    base_price_toman: Decimal | None,
    inventory_available: bool | None,
    review_reason: str | None,
) -> bool:
    if not target_member:
        return False
    if review_reason:
        return False
    if base_price_toman is None or base_price_toman <= 0:
        return False
    if inventory_available is not True:
        return False
    return True


def media_ready(*, image_count: int | None, primary_image_url: str | None) -> bool:
    url = (primary_image_url or "").strip()
    if not url:
        return False
    lowered = url.lower()
    if "placeholder" in lowered or lowered.endswith(".svg"):
        return False
    if image_count is not None and image_count <= 0:
        return False
    return True


def parse_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "t"}:
        return True
    if text in {"0", "false", "no", "n", "f"}:
        return False
    return None
