"""SAN OU official SourceAdapter — validates governed CSV candidates."""

from __future__ import annotations

import re
from pathlib import Path

from ..contracts import ImageCandidate, PageEvidence
from .base import SourceAdapter
from .candidate_loader import load_candidates_from_csv

_ALLOWED = frozenset({"www.sanouchuck.com", "sanouchuck.com", "en.sanouchuck.com"})

# Keep in sync with image_candidate_discovery.providers.sanou_official.extract_model_tokens
_MODEL_TOKEN_RE = re.compile(
    r"(?:"
    r"\b(?P<kseries>K(?:1[12]|72|\d{2}))-?-?(?P<ksize>\d{2,4})(?:MM)?\b"
    r"|\b(?P<hkj>HKJ\d{3,5})\b"
    r"|\b(?P<jdrill>J\d{3,5}[A-Z]?)\b"
    r"|\b(?P<scroll>SCROLL)-?-?(?P<scrollsize>\d{2,4})\b"
    r"|\b(?P<pinion>PINION)-(?P<pinionsize>\d{2,4})\b"
    r"|\b(?P<morse>MS\d-(?:B\d{1,2}|JT\d))\b"
    r"|\b(?P<cyl>C\d{2}-\d{1,2})\b"
    r"|\b(?P<qchuck>Q\d{2,3})\b"
    r"|\b(?P<hyd>3HB?)-?-?(?P<hydsize>\d{2,3}[A-Z]?\d?)\b"
    r"|\b(?P<sb>SB-\d{2,4})\b"
    r"|(?<![A-Za-z0-9])(?P<mt>MT[1-6])(?![A-Za-z0-9])"
    r"|\b(?P<arbor>B(?:12|16|18|22))\b"
    r"|\b(?P<dead>D11[3-5])\b"
    r")",
    re.IGNORECASE,
)


def _extract_model_tokens(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for m in _MODEL_TOKEN_RE.finditer(text or ""):
        if m.group("kseries") and m.group("ksize"):
            tok = f"{m.group('kseries').upper()}-{m.group('ksize')}"
        elif m.group("hkj"):
            tok = m.group("hkj").upper()
        elif m.group("jdrill"):
            tok = m.group("jdrill").upper()
        elif m.group("scroll") and m.group("scrollsize"):
            tok = f"SCROLL-{m.group('scrollsize')}"
        elif m.group("pinion") and m.group("pinionsize"):
            tok = f"PINION-{m.group('pinionsize')}"
        elif m.group("morse"):
            tok = m.group("morse").upper()
        elif m.group("cyl"):
            tok = m.group("cyl").upper()
        elif m.group("qchuck"):
            tok = m.group("qchuck").upper()
        elif m.group("hyd") and m.group("hydsize"):
            tok = f"{m.group('hyd').upper()}-{m.group('hydsize').upper()}"
        elif m.group("sb"):
            tok = m.group("sb").upper()
        elif m.group("mt"):
            tok = m.group("mt").upper()
        elif m.group("dead"):
            tok = m.group("dead").upper()
        elif m.group("arbor"):
            tok = m.group("arbor").upper()
        else:
            continue
        if len(tok) < 3 or tok.startswith("SO-"):
            continue
        if tok not in seen:
            seen.add(tok)
            found.append(tok)
    return found


def _token_present(text: str, token: str) -> bool:
    return bool(
        re.search(
            rf"(?<![A-Za-z0-9]){re.escape(token)}(?:MM)?(?![A-Za-z0-9])",
            text or "",
            re.IGNORECASE,
        )
    )


class SanouOfficialAdapter(SourceAdapter):
    """Validate governed CSV image candidates against SAN OU official pages."""

    name = "sanou_official"
    brand = "SAN OU"

    def __init__(self) -> None:
        self._sku_models: dict[str, list[str]] = {}

    def allowed_hosts(self) -> frozenset[str]:
        return _ALLOWED

    def normalize_sku(self, sku: str) -> str:
        return sku.strip()

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
            raise SystemExit("sanou_official requires --candidates-csv")
        cands = load_candidates_from_csv(
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
        self._sku_models = {}
        for c in cands:
            models = _extract_model_tokens(f"{c.sku} {c.product_name}")
            # Prefer model encoded in sku_evidence-style notes if discovery left it in name only
            self._sku_models[c.sku] = models
        return cands

    def validate_page(self, *, sku: str, page_html: str, detail_url: str) -> PageEvidence:
        html = page_html or ""
        mfg_ok = bool(
            re.search(r"\bsan\s*ou\b|\bsanou\b|\bsano\b|sanouchuck", html, re.IGNORECASE)
        )
        if not mfg_ok:
            return PageEvidence(
                False,
                False,
                "sanou_not_on_page",
                "",
                f"detail_url:{detail_url}",
                reason_code="manufacturer_not_confirmed",
                reason_detail="SAN OU manufacturer not confirmed on official page",
            )

        models = self._sku_models.get(sku) or _extract_model_tokens(sku)
        matched = [m for m in models if _token_present(html, m)]
        if not matched:
            return PageEvidence(
                True,
                False,
                "page_body_sanou",
                f"model_missing:{','.join(models) or sku}",
                f"detail_url:{detail_url}",
                reason_code="exact_sku_not_confirmed",
                reason_detail="exact model token not confirmed on official page",
            )
        return PageEvidence(
            True,
            True,
            "page_body_sanou",
            f"model:{matched[0]}",
            f"detail_url:{detail_url}",
        )
