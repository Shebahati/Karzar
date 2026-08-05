"""SKU / URL identity helpers for multisource adapters."""

from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

_SKU_TOKEN = re.compile(r"(?i)(?<![0-9a-z])([0-9]{3,5}-[0-9]{2,5}[a-z0-9]*|SO-\d+)(?![0-9a-z])")


def normalize_sku(sku: str) -> str:
    return (sku or "").strip().casefold()


def strip_trailing_variant(sku: str) -> str:
    """Strip trailing letter suffix after a numeric SKU (e.g. 2308-10a → 2308-10)."""
    text = (sku or "").strip()
    return re.sub(r"(?i)^([0-9]{3,5}-[0-9]{2,5})[a-z]+$", r"\1", text)


def skus_in_text(text: str) -> set[str]:
    return {m.group(1).casefold() for m in _SKU_TOKEN.finditer(text or "")}


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
    # Path bears a different SKU token than the governed product → conflict.
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
