"""Exact SKU/model identity matching for Fast Coverage discovery."""

from __future__ import annotations

import re
import unicodedata

from scripts.image_discovery.contracts import normalize_identity_token

# Word-boundary exact token — suffix/variant protection (5801-A55 ≠ 5801).
_EXACT_BOUNDARY = r"(?<![A-Za-z0-9\-_/])"
_EXACT_BOUNDARY_END = r"(?![A-Za-z0-9\-_/])"

_PUNCT_COLLAPSE = re.compile(r"[\s_\-/]+")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def normalize_sku(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = _PUNCT_COLLAPSE.sub("", text.strip().casefold())
    return text


def normalize_brand_key(value: str) -> str:
    return normalize_identity_token(value.replace("|", " ").replace("-", " "))


def sku_tokens(value: str) -> list[str]:
    raw = (value or "").strip()
    if not raw:
        return []
    primary = normalize_sku(raw)
    tokens = [primary] if primary else []
    # Preserve hyphenated forms for boundary checks
    compact = re.sub(r"\s+", "", raw.casefold())
    if compact and compact not in tokens:
        tokens.append(compact)
    return list(dict.fromkeys(tokens))


def exact_sku_in_text(expected_sku: str, text: str) -> bool:
    if not expected_sku or not text:
        return False
    hay = unicodedata.normalize("NFKC", text)
    for tok in sku_tokens(expected_sku):
        if not tok:
            continue
        pattern = _EXACT_BOUNDARY + re.escape(tok) + _EXACT_BOUNDARY_END
        if re.search(pattern, hay, flags=re.IGNORECASE):
            return True
        # Also check spaced/hyphen variants when token has no separators
        if "-" not in tok and len(tok) >= 4:
            spaced = "-".join(re.findall(r".{1,4}", tok)) if len(tok) > 4 else tok
            pattern2 = _EXACT_BOUNDARY + re.escape(spaced) + _EXACT_BOUNDARY_END
            if re.search(pattern2, hay, flags=re.IGNORECASE):
                return True
    return False


def is_family_only_match(expected_sku: str, matched_token: str) -> bool:
    """Reject when matched token is a strict prefix/family of expected."""
    exp = normalize_sku(expected_sku)
    got = normalize_sku(matched_token)
    if not exp or not got or exp == got:
        return False
    if exp.startswith(got) and len(exp) > len(got):
        return True
    if got.startswith(exp) and len(got) > len(exp):
        return True
    return False


def brand_matches(expected_brand: str, text: str, *, extra_tokens: tuple[str, ...] = ()) -> bool:
    if not expected_brand.strip():
        return not _has_contradictory_brand(text)
    key = normalize_brand_key(expected_brand)
    hay = normalize_identity_token(text)
    parts = [p.strip() for p in re.split(r"[|\-]", expected_brand) if p.strip()]
    candidates = {key, *(_NON_ALNUM.sub("", normalize_identity_token(p)) for p in parts)}
    candidates.update(_NON_ALNUM.sub("", normalize_identity_token(t)) for t in extra_tokens)
    candidates = {c for c in candidates if c}
    return any(c and c in _NON_ALNUM.sub("", hay) for c in candidates)


def _has_contradictory_brand(text: str) -> bool:
    # Conservative: known major brands in title when product is unbranded
    known = (
        "mitutoyo",
        "insize",
        "dasqua",
        "san ou",
        "sanou",
        "tiger",
        "yowax",
        "chumpower",
        "asimeto",
        "ast power",
        "astpower",
    )
    hay = normalize_identity_token(text)
    hits = sum(1 for k in known if k.replace(" ", "") in hay.replace(" ", ""))
    return hits >= 2


def classify_identity(
    *,
    sku: str,
    brand_key: str,
    product_name: str,
    page_title: str,
    page_text: str,
    has_pdp_structure: bool,
    image_is_product_gallery: bool,
    source_country: str,
) -> tuple[str, str, str, str, str]:
    """Return (status, match_type, brand_evidence, sku_evidence, reason_code)."""
    subject = f"{page_title}\n{product_name}\n{page_text[:8000]}"
    sku_hit = exact_sku_in_text(sku, subject)
    branded = bool(brand_key.strip())
    brand_hit = brand_matches(brand_key, subject) if branded else True
    contradictory = (not branded) and _has_contradictory_brand(subject)

    if not has_pdp_structure:
        return "red_rejected", "", "", "", "category_or_list_page"

    if branded and not brand_hit:
        if sku_hit:
            return "red_rejected", "", "missing", "exact_sku_present", "wrong_brand"
        return "red_rejected", "", "missing", "missing", "wrong_brand"

    if not sku_hit:
        if exact_sku_in_text(sku, product_name):
            sku_hit = True
        else:
            return "red_rejected", "", "present" if brand_hit else "", "missing", "wrong_sku"

    if contradictory:
        return "yellow_review", "no_brand_exact_sku", "", "exact_sku", "contradictory_brand_context"

    if not image_is_product_gallery:
        return "yellow_review", "exact_sku_weak_image", "present", "exact_sku", "ambiguous_image_relation"

    if branded and brand_hit and sku_hit:
        return "green_exact", "exact_brand_sku", "exact_brand", "exact_sku", ""

    if not branded and sku_hit:
        return "green_exact", "exact_sku_no_brand", "none", "exact_sku", ""

    return "yellow_review", "exact_sku_incomplete_brand", "partial", "exact_sku", "brand_evidence_incomplete"


def owner_policy_for_country(country: str) -> str:
    return "iranian_source_allowed" if country.upper() in {"IR", "IRAN"} else "non_iranian_not_precleared"


def temporary_primary_eligible(policy: str) -> bool:
    return policy == "iranian_source_allowed"
