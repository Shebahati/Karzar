"""Dasqua official SourceAdapter — validates governed CSV candidates."""

from __future__ import annotations

import re
from pathlib import Path

from ..contracts import ImageCandidate, PageEvidence
from .base import SourceAdapter
from .candidate_loader import load_candidates_from_csv

_ALLOWED = frozenset(
    {
        "www.dasquatools.com",
        "dasquatools.com",
        "cdn.globalso.com",
        *[f"ecdn{i}.globalso.com" for i in range(1, 16)],
    }
)
_CODE_RE = re.compile(r"^(\d{3,5}-\d{3,5})")


def _normalize_code(raw: str) -> str:
    text = (raw or "").strip()
    m = _CODE_RE.match(text)
    return m.group(1) if m else text


def _sku_token_present(text: str, sku: str) -> bool:
    code = _normalize_code(sku)
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9]){re.escape(code)}(?![A-Za-z0-9])",
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
        return _normalize_code(sku)

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
        code = _normalize_code(sku)
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
        # Reject family / multi-code pages (ambiguous product subject).
        distinct_codes = {
            m.group(1)
            for m in re.finditer(r"\b(\d{3,5}-\d{3,5})\b", html)
        }
        if len(distinct_codes) > 1 and code in distinct_codes:
            return PageEvidence(
                True,
                False,
                "page_body_dasqua",
                f"ambiguous_codes:{','.join(sorted(distinct_codes))}",
                f"detail_url:{detail_url}",
                reason_code="family_page_ambiguous",
                reason_detail="multiple distinct item codes on page",
            )
        sku_ok = _sku_token_present(html, code)
        if not sku_ok:
            return PageEvidence(
                True,
                False,
                "page_body_dasqua",
                f"code_missing:{code}",
                f"detail_url:{detail_url}",
                reason_code="exact_sku_not_confirmed",
                reason_detail=f"item code {code} not confirmed on official page",
            )
        return PageEvidence(
            True,
            True,
            "page_body_dasqua",
            f"item_code:{code}",
            f"detail_url:{detail_url}",
        )
