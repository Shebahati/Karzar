"""Conservative identity, brand, URL, and price normalization for zcc.ir.

Harmless formatting is folded. Distinct model suffixes are preserved.
Fuzzy name matching is never used as identity.
"""

from __future__ import annotations

import re
from decimal import Decimal
from urllib.parse import quote, unquote, urlparse, urlunparse

from catalog_target.core import convert_price, normalize_sku, parse_decimal

_HYPHEN_RE = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2212\uFE63\uFF0Dـ]")
_WS_RE = re.compile(r"\s+")
_ZWNJ_RE = re.compile(r"[\u200c\u200d\ufeff]")
_MODEL_RE = re.compile(
    r"(?:مدل|model)\s*[:：]?\s*"
    r"([A-Za-z0-9][A-Za-z0-9./\-]*(?:\s+[A-Za-z][A-Za-z0-9.\-]*)*)",
    re.IGNORECASE,
)
_INTERNAL_SKU_RE = re.compile(r"^\d{3,8}$")

# Local aliases only. Do not silently cross brands.
BRAND_ALIASES: dict[str, str] = {
    "ZCC": "ZCC.CT",
    "ZCC.CT": "ZCC.CT",
    "ZCCCT": "ZCC.CT",
    "ZCC-CT": "ZCC.CT",
    "ZCC_CT": "ZCC.CT",
    "زد سی سی": "ZCC.CT",
    "زد سی‌سی": "ZCC.CT",
    "زدسیسی": "ZCC.CT",
    "SANOU": "SAN OU",
    "SAN OU": "SAN OU",
    "SAN-OU": "SAN OU",
    "SAN_OU": "SAN OU",
    "سانو": "SAN OU",
    "STC": "STC",
}

KARZAR_BRAND_IDS: dict[str, str] = {
    "ZCC.CT": "8",
    "SAN OU": "20",
}

_BRAND_NAME_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"\bSAN\s*[-_]?OU\b|\bSANOU\b|سانو", re.I), "SAN OU", "name_token"),
    (re.compile(r"\bSTC\b", re.I), "STC", "name_token"),
    (re.compile(r"\bZCC(?:\.CT)?\b|زد\s*سی[‌\s]*سی", re.I), "ZCC.CT", "name_token"),
)


def fold_text(value: str | None) -> str:
    if value is None:
        return ""
    s = str(value).replace("ي", "ی").replace("ك", "ک")
    s = _ZWNJ_RE.sub("", s)
    s = _HYPHEN_RE.sub("-", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def canonicalize_brand(value: str | None) -> str | None:
    raw = fold_text(value)
    if not raw:
        return None
    left = raw.split("|", 1)[0].strip()
    key = _WS_RE.sub(" ", left).upper()
    key = key.replace("‌", "")
    compact = key.replace(" ", "")
    if key in BRAND_ALIASES:
        return BRAND_ALIASES[key]
    if compact in BRAND_ALIASES:
        return BRAND_ALIASES[compact]
    return key or None


def detect_brand_from_text(*texts: str | None) -> tuple[str | None, str | None]:
    """Return (normalized_brand, evidence). First distinct hit wins; conflicts → (None, conflict)."""
    hits: list[tuple[str, str]] = []
    seen: set[str] = set()
    for text in texts:
        blob = fold_text(text)
        if not blob:
            continue
        for pattern, brand, evidence in _BRAND_NAME_PATTERNS:
            if pattern.search(blob) and brand not in seen:
                hits.append((brand, evidence))
                seen.add(brand)
    if not hits:
        return None, None
    brands = {h[0] for h in hits}
    if len(brands) > 1:
        return None, "brand_token_conflict:" + ",".join(sorted(brands))
    return hits[0]


def extract_model_from_name(name: str | None) -> str | None:
    if not name:
        return None
    match = _MODEL_RE.search(fold_text(name))
    if not match:
        return None
    model = fold_text(match.group(1))
    model = model.strip(" -_/.,;:")
    return model or None


def manufacturer_identity_key(model: str | None) -> str:
    """Exact-match key for manufacturer model/grade. Preserves trailing letters."""
    if not model:
        return ""
    # Keep spaces between geometry and grade as hyphens so DCMT11T312-XM YBC203
    # matches Karzar ZCC-DCMT11T312-XM-YBC203 after prefix strip.
    folded = fold_text(model)
    folded = folded.replace(" ", "-")
    return normalize_sku(folded)


def is_internal_numeric_sku(value: str | None) -> bool:
    if value is None:
        return False
    return bool(_INTERNAL_SKU_RE.fullmatch(str(value).strip()))


def strip_known_sku_prefix(normalized_sku: str, brand_key: str | None) -> str:
    """Proven Karzar encoding prefixes only. Never strip meaningful model suffixes."""
    sku = normalized_sku or ""
    if brand_key == "ZCC.CT" and sku.startswith("ZCC-"):
        return sku[4:]
    if brand_key == "SAN OU" and sku.startswith("SO-"):
        return sku[3:]
    return sku


def karzar_alias_candidates(
    *,
    brand_key: str | None,
    manufacturer_key: str,
    internal_sku: str | None,
) -> list[str]:
    """Exact alias keys that may exist in Karzar, never fuzzy variants."""
    out: list[str] = []
    if brand_key == "ZCC.CT" and manufacturer_key:
        out.append(normalize_sku("ZCC-" + manufacturer_key))
    if brand_key == "SAN OU" and internal_sku and is_internal_numeric_sku(internal_sku):
        out.append(normalize_sku("SO-" + internal_sku.strip()))
    return out


def encode_http_url(url: str) -> str:
    """Percent-encode path so urllib can send the request line as ASCII."""
    if not url:
        return ""
    parsed = urlparse(url)
    path = quote(unquote(parsed.path or "/"), safe="/")
    query = quote(unquote(parsed.query), safe="=&%")
    return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, query, ""))


def normalize_source_url(url: str | None) -> str:
    if not url:
        return ""
    raw = str(url).strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "https").lower()
    if scheme not in {"http", "https"}:
        return raw
    host = (parsed.hostname or "").lower().rstrip(".")
    if host == "www.zcc.ir":
        host = "zcc.ir"
    path = quote(unquote(parsed.path or "/"), safe="/")
    # Rebuild without query/fragment — robots.txt disallows /*?*
    return urlunparse((scheme, host, path, "", "", ""))


def canonical_product_url(url: str | None) -> str:
    normalized = normalize_source_url(url)
    if not normalized:
        return ""
    parsed = urlparse(normalized)
    path = parsed.path or "/"
    if "/product/" in path and not path.endswith("/"):
        path += "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def slug_from_product_url(url: str | None) -> str | None:
    parsed = urlparse(normalize_source_url(url))
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "product":
        return unquote(parts[1])
    return None


def category_path_from_url(url: str | None) -> list[str]:
    parsed = urlparse(normalize_source_url(url))
    parts = [unquote(p) for p in parsed.path.split("/") if p]
    if parts[:1] == ["product-category"]:
        return parts[1:]
    return []


def price_to_toman(raw: str | None, currency: str | None) -> tuple[Decimal | None, str, str | None]:
    """Return (toman, status, reason). Currency is never inferred."""
    if raw is None or str(raw).strip() == "":
        return None, "missing", "missing_price"
    converted = convert_price(raw, currency=currency)
    if converted.review_reason:
        status = "invalid" if converted.review_reason in {"non_positive_price"} else "unusable"
        return converted.base_price_toman, status, converted.review_reason
    if converted.base_price_toman is None:
        return None, "unusable", converted.review_reason
    return converted.base_price_toman, "ok", None


def parse_price_amount(value: Any) -> Decimal | None:
    return parse_decimal(value)
