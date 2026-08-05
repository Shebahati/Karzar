"""Dasqua official SourceAdapter — validates governed CSV candidates."""

from __future__ import annotations

import re
from pathlib import Path

from ..contracts import ImageCandidate, PageEvidence
from .base import SourceAdapter
from .candidate_loader import load_candidates_from_csv

# Page hosts only for detail navigation; observed CDN hosts for embedded assets.
_PAGE_HOSTS = frozenset({"www.dasquatools.com", "dasquatools.com"})
_OBSERVED_ASSET_HOSTS = frozenset({"cdn.globalso.com", "ecdn6.globalso.com"})
_ALLOWED = _PAGE_HOSTS | _OBSERVED_ASSET_HOSTS

_EXACT_CODE_RE = re.compile(r"\b(\d{3,5}-\d{3,5}(?:-[A-Za-z0-9]+|[A-Za-z])?)\b")
_TITLE_DASQUA_RE = re.compile(
    r"Dasqua\s+(\d{3,5}-\d{3,5}(?:-[A-Za-z0-9]+|[A-Za-z])?)\b",
    re.IGNORECASE,
)
_ITEM_NUMBER_RE = re.compile(
    r"(?:Item\s*Number|Item\s*No\.?|Order\s*No\.?|Art\.?\s*No\.?|Product\s*No\.?)\s*[:：]\s*"
    r"(\d{3,5}-\d{3,5}(?:-[A-Za-z0-9]+|[A-Za-z])?)\b",
    re.IGNORECASE,
)


def _norm_code(code: str) -> str:
    return (code or "").strip().casefold()


def _primary_exact_codes(page_html: str, detail_url: str = "") -> set[str]:
    """Title + labeled Item Number (+ single path code). Ignore related-product chrome.

    If no primary evidence exists, fall back to whole-page codes (fail closed).
    Codes are case-folded so path/title suffix case does not false-ambiguate.
    """
    html = page_html or ""
    primary: set[str] = set()
    title_m = re.search(r"<title>([^<]+)", html, re.IGNORECASE)
    title = title_m.group(1).strip() if title_m else ""
    m = _TITLE_DASQUA_RE.search(title)
    if m:
        primary.add(_norm_code(m.group(1)))
    primary.update(_norm_code(c) for c in _ITEM_NUMBER_RE.findall(html))
    path = detail_url or ""
    path_codes = list(dict.fromkeys(_EXACT_CODE_RE.findall(path)))
    if len(path_codes) == 1:
        primary.add(_norm_code(path_codes[0]))
    if primary:
        return primary
    return {_norm_code(c) for c in _EXACT_CODE_RE.findall(html)}


def _governed_sku(raw: str) -> str:
    return (raw or "").strip()


def _sku_token_present(text: str, sku: str) -> bool:
    """Require exact governed SKU token (suffix-sensitive)."""
    sku = _governed_sku(sku)
    if not sku:
        return False
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9]){re.escape(sku)}(?![A-Za-z0-9])",
            text or "",
            re.IGNORECASE,
        )
    )


class DasquaOfficialAdapter(SourceAdapter):
    """Validate governed CSV image candidates against Dasqua official pages."""

    name = "dasqua_official"
    brand = "Dasqua"

    def allowed_hosts(self) -> frozenset[str]:
        return _ALLOWED

    def normalize_sku(self, sku: str) -> str:
        """Preserve governed SKU including suffixes (no family collapse)."""
        return _governed_sku(sku)

    def load_candidates(
        self,
        *,
        products_csv: Path | None,
        candidates_csv: Path | None,
        sku_filters: list[str] | None,
        limit: int | None,
        offset: int,
        max_images_per_product: int,
    ) -> list[ImageCandidate]:
        if candidates_csv is None:
            raise SystemExit("dasqua_official requires --candidates-csv")
        return load_candidates_from_csv(
            adapter_name=self.name,
            brand=self.brand,
            candidates_csv=candidates_csv,
            products_csv=products_csv,
            sku_filters=sku_filters,
            limit=limit,
            offset=offset,
            max_images_per_product=max_images_per_product,
            normalize_sku=self.normalize_sku,
        )

    def validate_page(self, *, sku: str, page_html: str, detail_url: str) -> PageEvidence:
        html = page_html or ""
        governed = _governed_sku(sku)
        mfg_ok = bool(re.search(r"\bdasqua\b", html, re.IGNORECASE))
        if not mfg_ok:
            return PageEvidence(
                False,
                False,
                "dasqua_not_on_page",
                "",
                f"detail_url:{detail_url}",
                reason_code="manufacturer_not_confirmed",
                reason_detail="Dasqua manufacturer not confirmed on official page",
            )

        distinct_exact = _primary_exact_codes(html, detail_url or "")
        if len(distinct_exact) > 1:
            return PageEvidence(
                True,
                False,
                "page_body_dasqua",
                f"ambiguous_codes:{','.join(sorted(distinct_exact))}",
                f"detail_url:{detail_url}",
                reason_code="family_page_ambiguous",
                reason_detail="multiple distinct primary item codes on page",
            )

        sku_ok = _sku_token_present(html, governed) or _sku_token_present(
            detail_url or "", governed
        )
        if not sku_ok:
            return PageEvidence(
                True,
                False,
                "page_body_dasqua",
                f"exact_sku_missing:{governed}",
                f"detail_url:{detail_url}",
                reason_code="exact_sku_not_confirmed",
                reason_detail=(
                    f"governed_sku {governed} not confirmed as exact item code "
                    "(family base match alone is insufficient)"
                ),
            )
        return PageEvidence(
            True,
            True,
            "page_body_dasqua",
            f"exact_item_code:{governed}",
            f"detail_url:{detail_url}",
        )
