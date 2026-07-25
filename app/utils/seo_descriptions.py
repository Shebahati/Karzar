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


def _norm(text: str | None) -> str:
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", text).strip()


def is_stub_description(text: str | None, *, product_name: str | None = None) -> bool:
    """Return True when copy is empty, too short, or approximately the product name."""
    body = _norm(text)
    if not body:
        return True
    if len(body) < STUB_MAX_LENGTH:
        return True
    name = _norm(product_name)
    if name and body.casefold() == name.casefold():
        return True
    # Near name-echo: body is name plus trivial punctuation/SKU fragments only.
    if name and body.casefold().startswith(name.casefold()) and len(body) <= len(name) + 8:
        return True
    return False


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
    brand = _sot_value(brand_name)
    category = _sot_value(category_name)
    if brand and category:
        parts.append(f"{category} برند {brand}")
    elif category:
        parts.append(category)
    elif brand:
        parts.append(f"محصول برند {brand}")

    # Pull a few safe display keys if already present — never fabricate.
    safe_keys = ("range", "resolution", "material", "standard", "اندازه", "محدوده")
    found: list[str] = []
    if isinstance(technical_specs, list):
        keyed = {
            _norm(str(row.get("key", ""))).casefold(): _sot_value(row.get("value"))
            for row in technical_specs
            if isinstance(row, dict)
        }
        for key in safe_keys:
            val = keyed.get(key.casefold())
            if val:
                found.append(f"{key}: {val}")
    elif isinstance(technical_specs, dict):
        for key in safe_keys:
            val = _sot_value(technical_specs.get(key))
            if val:
                found.append(f"{key}: {val}")
    if found:
        parts.append("؛ ".join(found[:3]))

    sku_val = _sot_value(sku)
    if sku_val:
        parts.append(f"کد {sku_val}")

    if not parts:
        # Name alone is a stub — refuse to emit name-echo.
        return None

    # Optional family hint for future per-template wording (kept additive, not required).
    _ = spec_template_key

    body = " — ".join(parts)
    # Avoid emitting a near-name stub.
    if is_stub_description(body, product_name=name):
        return None
    return body[:500]
