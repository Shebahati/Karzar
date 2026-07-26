"""Deterministic product SEO description helpers (P0/P1).

Rules (constitution / PIM):
- ``short_description`` is a separate field from long ``description``.
- Meta description priority: meta_description → short_description → description excerpt → fallback.
- Meta title priority: meta_title → name.
- Templates may only echo non-empty Source-of-Truth fields (no invented specs).
- AI long-form (P4) stays Draft/Pending until human QA — not applied here.
"""

from __future__ import annotations

import re
from typing import Any

# Stub classifier: very short or name-echo bodies are treated as empty for rewrite queues.
STUB_MAX_LENGTH = 40

_WHITESPACE_RE = re.compile(r"\s+")
_BILINGUAL_SPLIT_RE = re.compile(r"\s*\|\s*")
_ANVA_PREFIX_RE = re.compile(r"^انواع\s+")

# Measurement SoT keys only — catalog "جنس"/"استاندارد" are often country/SKU noise.
_SAFE_SPEC_KEYS: tuple[str, ...] = (
    "range",
    "resolution",
    "اندازه",
    "محدوده",
    "بازه اندازه‌گیری",
    "بازه اندازه گیری",
    "دقت",
    "رزولوشن",
)

# Prefer Persian display labels when echoing specs in storefront copy.
_SPEC_DISPLAY_LABELS: dict[str, str] = {
    "range": "بازه",
    "resolution": "رزولوشن",
    "اندازه": "اندازه",
    "محدوده": "محدوده",
    "بازه اندازه‌گیری": "بازه",
    "بازه اندازه گیری": "بازه",
    "دقت": "دقت",
    "رزولوشن": "رزولوشن",
}
_MAX_SPEC_VALUE_LEN = 48


def _norm(text: str | None) -> str:
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", text).strip()


def split_bilingual_label(label: str | None) -> tuple[str | None, str | None]:
    """Split ``EN | FA`` brand/category labels into (latin, persian) parts when present."""
    text = _norm(label)
    if not text:
        return None, None
    if "|" not in text:
        return text, None
    left, right = _BILINGUAL_SPLIT_RE.split(text, maxsplit=1)
    left, right = _norm(left), _norm(right)
    return (left or None), (right or None)


def display_brand_name(brand_name: str | None) -> str | None:
    """Prefer Persian brand half for RTL storefront copy; fall back to Latin/raw."""
    latin, persian = split_bilingual_label(brand_name)
    return persian or latin


def display_category_name(category_name: str | None) -> str | None:
    """Normalize category leaf labels (drop leading ``انواع `` noise)."""
    text = _norm(category_name)
    if not text:
        return None
    _, persian = split_bilingual_label(text)
    leaf = persian or text
    leaf = _ANVA_PREFIX_RE.sub("", leaf).strip()
    return leaf or None


_MODEL_TAIL_RE = re.compile(
    r"(?:\s*مدل\s+\S+|\s*کد\s+\S+|\s+\d[\w./-]{2,})\s*$",
    re.IGNORECASE,
)
_PAREN_RE = re.compile(r"\([^)]*\)")


def product_lead_from_name(
    name: str | None,
    *,
    brand_name: str | None = None,
) -> str | None:
    """Derive a short product-type lead from the product name (SoT).

    Strips brand tokens, parenthetical brand echoes, and trailing model/SKU tails.
    Prefer this over a taxonomy leaf when the name is more specific (sets, kits, parts).
    """
    text = _norm(name)
    if not text:
        return None
    brand = display_brand_name(brand_name)
    latin, _ = split_bilingual_label(brand_name)
    for token in (brand, latin, "Insize", "INSIZE", "Mitutoyo", "Dasqua", "ASIMETO", "آسیمتو"):
        if not token:
            continue
        text = re.sub(re.escape(token), " ", text, flags=re.IGNORECASE)
    text = _PAREN_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip(" -–—|,")
    # Peel model/SKU tails repeatedly.
    for _ in range(3):
        nxt = _MODEL_TAIL_RE.sub("", text).strip(" -–—|,")
        if nxt == text:
            break
        text = nxt
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if len(text) < 3:
        return None
    # Keep leads compact for PDP blurbs.
    if len(text) > 72:
        text = text[:71].rstrip() + "…"
    return text or None


def choose_product_lead(
    *,
    name: str | None,
    brand_name: str | None = None,
    category_name: str | None = None,
) -> str | None:
    """Prefer name-derived lead when it is clearly richer than the category leaf."""
    category = display_category_name(category_name)
    lead = product_lead_from_name(name, brand_name=brand_name)
    if lead and category:
        # Name lead wins when longer / not equal to the leaf (sets, kits, accessories).
        if lead.casefold() != category.casefold() and len(lead) >= max(len(category), 6):
            return lead
        return category
    return lead or category


def is_name_echo_description(text: str | None, *, product_name: str | None = None) -> bool:
    """True when body is empty or approximately the product name (ignores length)."""
    body = _norm(text)
    if not body:
        return True
    name = _norm(product_name)
    if not name:
        return False
    if body.casefold() == name.casefold():
        return True
    # Near name-echo: body is name plus trivial punctuation/SKU fragments only.
    if body.casefold().startswith(name.casefold()) and len(body) <= len(name) + 8:
        return True
    return False


def is_stub_description(text: str | None, *, product_name: str | None = None) -> bool:
    """Return True when copy is empty, too short, or approximately the product name."""
    body = _norm(text)
    if not body:
        return True
    if len(body) < STUB_MAX_LENGTH:
        return True
    return is_name_echo_description(body, product_name=product_name)


def excerpt_description(text: str | None, *, max_len: int = 160) -> str | None:
    body = _norm(text)
    if not body:
        return None
    if len(body) <= max_len:
        return body
    truncated = body[: max_len - 1].rstrip()
    # Prefer breaking on whitespace to avoid mid-word cuts.
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return f"{truncated}…"


def resolve_meta_title(*, meta_title: str | None, name: str) -> str:
    title = _norm(meta_title)
    return title or _norm(name) or "محصول"


def resolve_meta_description(
    *,
    meta_description: str | None,
    short_description: str | None,
    description: str | None,
    name: str,
) -> str:
    """Priority: explicit meta → short → long excerpt → minimal non-spammy fallback.

    Explicit ``meta_description`` always wins when non-empty (editor override).
    Stub filtering applies to inherited short/long copy so name-echo stubs do not
    pollute SERP snippets.
    """
    meta = _norm(meta_description)
    if meta:
        return meta[:500]

    short = _norm(short_description)
    if short and not is_stub_description(short, product_name=name):
        return short[:500]

    excerpt = excerpt_description(description) or ""
    if excerpt and not is_stub_description(excerpt, product_name=name):
        return excerpt[:500]

    if short:
        return short[:500]

    safe_name = _norm(name) or "این محصول"
    return f"{safe_name} | فروشگاه ابزار کارزار"


def resolve_jsonld_description(
    *,
    short_description: str | None,
    description: str | None,
    name: str,
    max_len: int = 500,
) -> str:
    """JSON-LD Product.description mirrors visible short copy (subset), no extra claims."""
    short = _norm(short_description)
    if short and not is_stub_description(short, product_name=name):
        return short[:max_len]
    if short:
        return short[:max_len]
    excerpt = excerpt_description(description, max_len=max_len)
    if excerpt:
        return excerpt
    return resolve_meta_description(
        meta_description=None,
        short_description=None,
        description=None,
        name=name,
    )[:max_len]


def _sot_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    text = _norm(str(value))
    return text or None


def _coerce_technical_specs(
    technical_specs: dict[str, Any] | list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | dict[str, Any] | None:
    """Accept raw technical_specs or nested ``specifications`` payloads from the API."""
    if technical_specs is None:
        return None
    if isinstance(technical_specs, list):
        return technical_specs
    if not isinstance(technical_specs, dict):
        return None
    nested = technical_specs.get("technical_specs")
    if isinstance(nested, list):
        return nested
    # Flat dict of key→value SoT fields.
    return technical_specs


def _extract_safe_specs(
    technical_specs: dict[str, Any] | list[dict[str, Any]] | None,
    *,
    sku: str | None = None,
) -> list[str]:
    coerced = _coerce_technical_specs(technical_specs)
    sku_norm = _norm(sku).casefold()
    found: list[str] = []
    if isinstance(coerced, list):
        keyed = {
            _norm(str(row.get("key", ""))).casefold(): _sot_value(row.get("value"))
            for row in coerced
            if isinstance(row, dict)
        }
        for key in _SAFE_SPEC_KEYS:
            val = keyed.get(key.casefold())
            if not val:
                continue
            if sku_norm and val.casefold() == sku_norm:
                continue
            if len(val) > _MAX_SPEC_VALUE_LEN:
                val = val[: _MAX_SPEC_VALUE_LEN - 1].rstrip() + "…"
            label = _SPEC_DISPLAY_LABELS.get(key, key)
            found.append(f"{label} {val}")
    elif isinstance(coerced, dict):
        for key in _SAFE_SPEC_KEYS:
            val = _sot_value(coerced.get(key))
            if not val:
                continue
            if sku_norm and val.casefold() == sku_norm:
                continue
            if len(val) > _MAX_SPEC_VALUE_LEN:
                val = val[: _MAX_SPEC_VALUE_LEN - 1].rstrip() + "…"
            label = _SPEC_DISPLAY_LABELS.get(key, key)
            found.append(f"{label} {val}")
    return found[:3]


def render_short_description_template(
    *,
    name: str,
    brand_name: str | None = None,
    category_name: str | None = None,
    sku: str | None = None,
    spec_template_key: str | None = None,
    technical_specs: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> str | None:
    """Deterministic short blurb from non-empty SoT fields only.

    Returns None when there is insufficient SoT signal (caller should leave field empty).
    Does not invent accuracy/range/warranty claims.
    """
    parts: list[str] = []
    brand = display_brand_name(brand_name)
    lead = choose_product_lead(name=name, brand_name=brand_name, category_name=category_name)
    if brand and lead:
        parts.append(f"{lead} برند {brand}")
    elif lead:
        parts.append(lead)
    elif brand:
        parts.append(f"محصول برند {brand}")

    sku_val = _sot_value(sku)
    found = _extract_safe_specs(technical_specs, sku=sku_val)
    if found:
        parts.append("؛ ".join(found))

    if sku_val:
        parts.append(f"کد {sku_val}")

    if not parts:
        # Name alone is a stub — refuse to emit name-echo.
        return None

    # Optional family hint for future per-template wording (kept additive, not required).
    _ = spec_template_key

    body = " — ".join(parts)
    # Reject name-echo only. Short SoT blurbs (brand+lead+SKU) are valid
    # even when under STUB_MAX_LENGTH.
    if is_name_echo_description(body, product_name=name):
        return None
    return body[:500]


def template_apply_ready(
    *,
    name: str,
    brand_name: str | None = None,
    category_name: str | None = None,
    sku: str | None = None,
    technical_specs: dict[str, Any] | list[dict[str, Any]] | None = None,
) -> bool:
    """True when a template has at least one safe measurement SoT field.

    Category/name+SKU-only blurbs are useful for dry-run review but are not
    excellent enough for bulk apply (taxonomy leaves are often wrong for kits).
    """
    preview = render_short_description_template(
        name=name,
        brand_name=brand_name,
        category_name=category_name,
        sku=sku,
        technical_specs=technical_specs,
    )
    if not preview:
        return False
    return bool(_extract_safe_specs(technical_specs, sku=_sot_value(sku)))
