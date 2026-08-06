"""SKU / catalog-code / URL identity helpers for multisource adapters."""

from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

# Catalog / model codes (deterministic; rejects short numeric ranges like 0-150).
_CATALOG_CODE = re.compile(
    r"(?ix)"
    r"(?<![0-9A-Z])"
    r"("
    # Alpha-leading multi-segment: ISQ-RM30, ISO-1200FN, DSW-A010, ISQ-DRM31
    r"[A-Z]{2,}[A-Z0-9]*-(?:[A-Z]{0,4}\d+[A-Z0-9]*|\d+[A-Z][A-Z0-9]*)"
    r"|"
    # Numeric family with alpha mid/suffix: 5801-A55, 2308-10A
    r"\d{3,5}-(?:[A-Z]\d+[A-Z0-9]*|\d{1,5}[A-Z][A-Z0-9]*)"
    r"|"
    # Numeric-numeric with ≥1 digit after separator: 2199-1, 7600-6, 1108-150
    r"\d{3,5}-\d{1,5}"
    r"|"
    # SAN OU style
    r"SO-\d+"
    r")"
    r"(?![0-9A-Z])"
)

# Words / dimension-like tokens that must never count as SKUs.
_REJECT_EXACT = frozenset(
    {
        "ip54",
        "ip65",
        "ip67",
        "din878",
        "mm",
        "inch",
    }
)


def normalize_sku(sku: str) -> str:
    return (sku or "").strip().casefold()


def strip_trailing_variant(sku: str) -> str:
    """Strip trailing letter-only suffix after a numeric SKU (e.g. 2308-10a → 2308-10)."""
    text = (sku or "").strip()
    m = re.match(r"(?i)^(\d{3,5}-\d{1,5})[a-z]+$", text)
    if m:
        return m.group(1)
    return text


def is_plausible_catalog_code(token: str) -> bool:
    t = (token or "").strip()
    if not t or normalize_sku(t) in _REJECT_EXACT:
        return False
    if not _CATALOG_CODE.fullmatch(t):
        return False
    # Reject tiny numeric ranges (0-10, 6-80): first segment must be ≥3 digits unless alpha-led.
    if t[0].isdigit():
        left = t.split("-", 1)[0]
        if len(left) < 3:
            return False
    return True


def skus_in_text(text: str) -> set[str]:
    found: set[str] = set()
    for m in _CATALOG_CODE.finditer(text or ""):
        token = m.group(1)
        if is_plausible_catalog_code(token):
            found.add(normalize_sku(token))
    return found


def extract_catalog_codes(text: str) -> list[str]:
    """Ordered unique catalog codes as they appear (original casing preserved loosely)."""
    out: list[str] = []
    seen: set[str] = set()
    for m in _CATALOG_CODE.finditer(text or ""):
        token = m.group(1)
        if not is_plausible_catalog_code(token):
            continue
        key = normalize_sku(token)
        if key in seen:
            continue
        seen.add(key)
        out.append(token)
    return out


def sku_token_in_path(url: str, sku: str) -> str:
    """Classify URL-path identity: exact | family | conflict | absent."""
    target = normalize_sku(sku)
    if not target:
        return "absent"
    path = unquote(urlparse(url).path or "").casefold()
    tokens = skus_in_text(path)
    if not tokens:
        if re.search(rf"(?i)(?<![0-9a-z]){re.escape(target)}(?![0-9a-z])", path):
            return "exact"
        return "absent"
    if target in tokens:
        foreign = {
            t
            for t in tokens
            if t != target
            and normalize_sku(strip_trailing_variant(t))
            != normalize_sku(strip_trailing_variant(sku))
        }
        return "conflict" if foreign else "exact"
    base = normalize_sku(strip_trailing_variant(sku))
    family_hits = {
        t
        for t in tokens
        if normalize_sku(strip_trailing_variant(t)) == base and t != target
    }
    if family_hits and all(
        normalize_sku(strip_trailing_variant(t)) == base for t in tokens
    ):
        return "family"
    return "conflict"


def exact_or_family_slug_match(catalog_sku: str, governed_sku: str) -> str:
    """Return exact | family | ''."""
    c = normalize_sku(catalog_sku)
    g = normalize_sku(governed_sku)
    if not c or not g:
        return ""
    if c == g:
        return "exact"
    if normalize_sku(strip_trailing_variant(c)) == g or c == normalize_sku(
        strip_trailing_variant(g)
    ):
        return "family"
    return ""


def brand_aliases(brand_key: str) -> tuple[str, ...]:
    key = (brand_key or "").strip().casefold()
    table = {
        "insize": ("insize", "اینسایز"),
        "dasqua": ("dasqua", "داسکا", "داسکوا"),
        "san_ou": ("san ou", "sanou", "san-ou", "سان او"),
    }
    return table.get(key, (key,) if key else ())


def conflicting_brand_in_text(text: str, expected_brand: str) -> str | None:
    """Return conflicting brand token if text encodes a different known brand."""
    hay = (text or "").casefold()
    expected = (expected_brand or "").strip().casefold()
    known = {
        "insize": brand_aliases("insize"),
        "dasqua": brand_aliases("dasqua"),
        "san_ou": brand_aliases("san_ou"),
    }
    expected_aliases = set(brand_aliases(expected))
    for brand, aliases in known.items():
        if brand == expected or brand.replace("_", "") == expected.replace("_", ""):
            continue
        for alias in aliases:
            if alias and alias in hay and alias not in expected_aliases:
                return brand
    return None
