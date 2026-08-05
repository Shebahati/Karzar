"""INSIZE / TOSAG (www.tosag.ch) adapter — validation of governed CSV candidates."""

from __future__ import annotations

import html as html_lib
import re
from pathlib import Path
from typing import Any

from ..contracts import ImageCandidate, PageEvidence
from .base import SourceAdapter
from .candidate_loader import load_candidates_from_csv
from .html_subject import parse_page_subject, text_of

_ALLOWED = frozenset({"www.tosag.ch"})


def _text(fragment: str) -> str:
    return html_lib.unescape(text_of(fragment))


def _sku_token_present(text: str, sku: str) -> bool:
    pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(sku)}(?![A-Za-z0-9])", re.IGNORECASE)
    return bool(pattern.search(text))


def _extract_heading(subject_html: str, headings: list[str] | None = None) -> str:
    if headings:
        return headings[0]
    m = re.search(r"<h1\b[^>]*>(.*?)</h1>", subject_html, re.IGNORECASE | re.DOTALL)
    if m:
        return _text(m.group(1))
    return ""


def _json_ld_brand_name(prod: dict[str, Any]) -> str:
    brand = prod.get("brand")
    if isinstance(brand, dict):
        return str(brand.get("name") or "")
    return str(brand or "")


def _json_ld_sku_fields(prod: dict[str, Any]) -> list[str]:
    return [str(prod.get(f) or "") for f in ("sku", "mpn", "productID")]


def _product_fingerprint(prod: dict[str, Any]) -> str:
    brand = _json_ld_brand_name(prod).strip().casefold()
    skus = "|".join(sorted(s.strip().casefold() for s in _json_ld_sku_fields(prod) if s.strip()))
    return f"{brand}::{skus}"


def _select_atomic_json_ld_product(
    products: list[dict[str, Any]],
    sku: str,
) -> tuple[str, dict[str, Any] | None]:
    """Select one internally consistent Product for automatic structured acceptance.

    Never combine Brand from one object with SKU from another.
    Returns (status, product) where status is:
      ok | none | ambiguous | cross_object_mix
    """
    if not products:
        return "none", None

    consistent: list[dict[str, Any]] = []
    brand_only_insize: list[dict[str, Any]] = []
    sku_only_match: list[dict[str, Any]] = []
    other: list[dict[str, Any]] = []

    for prod in products:
        brand = _json_ld_brand_name(prod)
        has_insize = bool(brand and re.search(r"\binsize\b", brand, re.IGNORECASE))
        has_sku = any(_sku_token_present(sf, sku) for sf in _json_ld_sku_fields(prod))
        if has_insize and has_sku:
            consistent.append(prod)
        elif has_insize and not has_sku:
            brand_only_insize.append(prod)
        elif has_sku and not has_insize:
            sku_only_match.append(prod)
        else:
            other.append(prod)

    if brand_only_insize and sku_only_match and not consistent:
        return "cross_object_mix", None

    if consistent:
        fps = {_product_fingerprint(p) for p in consistent}
        if len(fps) > 1:
            return "ambiguous", None
        winner = consistent[0]
        winner_fp = _product_fingerprint(winner)
        # Distinct sibling Product nodes (e.g. other SKU) make structured evidence ambiguous
        for p in brand_only_insize + sku_only_match + other:
            if _product_fingerprint(p) != winner_fp:
                return "ambiguous", None
        return "ok", winner

    if len(products) > 1:
        return "ambiguous", None
    return "none", None


def _manufacturer_in_subject(
    subject_html: str,
    subject_text: str,
    *,
    headings: list[str],
    meta: dict[str, str],
    atomic_product: dict[str, Any] | None,
) -> tuple[bool, str]:
    labeled = re.search(
        r"(?:manufacturer|brand|hersteller|marke)\s*[:：]\s*</?(?:[^>]+>)?\s*([^<\n]{0,80})",
        subject_html,
        re.IGNORECASE,
    )
    if labeled:
        val = _text(labeled.group(1))
        if re.search(r"\binsize\b", val, re.IGNORECASE):
            return True, f"labeled_brand_field:{val[:80]}"

    # TOSAG: <strong>Manufacturers:</strong> … <span itemprop="name">Insize</span>
    mfr_block = re.search(
        r"(?:manufacturers?|brand|hersteller|marke)\s*[:：]\s*</strong>\s*"
        r"(?:<[^>]+>\s*)*?<span[^>]*itemprop=[\"']name[\"'][^>]*>\s*([^<]+)",
        subject_html,
        re.IGNORECASE | re.DOTALL,
    )
    if mfr_block and re.search(r"\binsize\b", mfr_block.group(1), re.IGNORECASE):
        return True, f"labeled_itemprop_name:{_text(mfr_block.group(1))[:80]}"

    brand_span = re.search(
        r'itemprop=["\']brand["\'][^>]*>.*?itemprop=["\']name["\'][^>]*>\s*([^<]+)',
        subject_html,
        re.IGNORECASE | re.DOTALL,
    )
    if brand_span and re.search(r"\binsize\b", brand_span.group(1), re.IGNORECASE):
        return True, f"schema_brand_name:{_text(brand_span.group(1))[:80]}"

    dt = re.search(
        r"<dt[^>]*>\s*(?:manufacturer|brand|hersteller|marke)\s*</dt>\s*<dd[^>]*>\s*([^<]+)",
        subject_html,
        re.IGNORECASE,
    )
    if dt and re.search(r"\binsize\b", dt.group(1), re.IGNORECASE):
        return True, f"labeled_dt_dd:{_text(dt.group(1))[:80]}"

    heading = _extract_heading(subject_html, headings)
    if re.search(r"\binsize\b", heading, re.IGNORECASE):
        return True, f"heading:{heading[:120]}"

    for key in ("product:brand", "og:brand", "brand"):
        if key in meta and re.search(r"\binsize\b", meta[key], re.IGNORECASE):
            return True, f"meta:{key}:{meta[key][:80]}"

    # JSON-LD brand only from the selected atomic Product (never cross-object)
    if atomic_product is not None:
        brand_name = _json_ld_brand_name(atomic_product)
        if re.search(r"\binsize\b", brand_name, re.IGNORECASE):
            return True, f"jsonld_brand:{brand_name[:80]}"

    if re.search(r"\binsize\b", subject_text, re.IGNORECASE):
        return False, "weak_body_insize_only"
    return False, "insize_not_in_page_subject"


def _sku_in_subject(
    subject_html: str,
    subject_text: str,
    sku: str,
    *,
    headings: list[str],
    meta: dict[str, str],
    atomic_product: dict[str, Any] | None,
    json_ld_status: str,
    scripts_text: str,
) -> tuple[bool, str]:
    heading = _extract_heading(subject_html, headings)
    if _sku_token_present(heading, sku):
        return True, f"heading_sku:{sku}"
    for h in headings:
        if _sku_token_present(h, sku):
            return True, f"heading_sku:{sku}"

    art = re.search(
        rf"(?:art(?:ikel)?(?:[\.\s-]*n[ro]\.?)?|item\s*(?:no\.?|number)|bestell(?:nummer)?|"
        rf"sku|model|variation)\s*[:#]?\s*.{{0,40}}?(?<![A-Za-z0-9]){re.escape(sku)}(?![A-Za-z0-9])",
        subject_text,
        re.IGNORECASE,
    )
    if art:
        return True, f"labeled_article:{sku}"

    if re.search(
        rf"<t[dh]\b[^>]*>\s*{re.escape(sku)}\s*</t[dh]>",
        subject_html,
        re.IGNORECASE,
    ):
        return True, f"table_cell:{sku}"

    # TOSAG variation anchors in subject only: "1120-500 - Digital Inside Groove…"
    # Do not use a bare body occurrence (related/nav text is filtered by subject split).
    if re.search(
        rf"<a\b[^>]*>\s*{re.escape(sku)}\s*[-–:]",
        subject_html,
        re.IGNORECASE,
    ):
        return True, f"variation_anchor_label:{sku}"

    for key, val in meta.items():
        if _sku_token_present(val, sku) and any(
            x in key for x in ("sku", "mpn", "product:retailer_item_id", "product_id")
        ):
            return True, f"meta:{key}:{sku}"

    if atomic_product is not None and json_ld_status == "ok":
        return True, f"jsonld_atomic:{sku}"

    if json_ld_status == "cross_object_mix":
        return False, "jsonld_cross_object_mix"
    if json_ld_status == "ambiguous":
        return False, "jsonld_ambiguous_products"

    if _sku_token_present(subject_text, sku):
        return False, f"weak_body_sku_only:{sku}"
    if _sku_token_present(scripts_text, sku):
        return False, f"weak_script_sku_only:{sku}"
    return False, f"sku_not_in_page_subject:{sku}"


class InsizeTosagAdapter(SourceAdapter):
    """Validate governed CSV image candidates against TOSAG product pages."""

    name = "insize_tosag"
    brand = "INSIZE"

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
            raise SystemExit("insize_tosag requires --candidates-csv")
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
        parsed = parse_page_subject(page_html)
        subject_html = parsed.subject_html()
        unrelated_html = parsed.unrelated_html()
        scripts_html = parsed.scripts_html()
        subject_text = _text(subject_html)
        unrelated_text = _text(unrelated_html)
        scripts_text = _text(scripts_html)
        headings = list(parsed.headings)
        # Subject-region meta/JSON-LD only — unrelated structured evidence never auto-accepts
        meta = dict(parsed.subject_meta)
        subject_products = list(parsed.subject_json_ld_products)
        json_ld_status, atomic_product = _select_atomic_json_ld_product(subject_products, sku)

        mfg_ok, mfg_ev = _manufacturer_in_subject(
            subject_html,
            subject_text,
            headings=headings,
            meta=meta,
            atomic_product=atomic_product if json_ld_status == "ok" else None,
        )
        heading = _extract_heading(subject_html, headings)
        if not mfg_ok:
            if mfg_ev == "weak_body_insize_only":
                return PageEvidence(
                    False,
                    False,
                    mfg_ev,
                    "",
                    heading,
                    reason_code="manufacturer_not_confirmed",
                    reason_detail="INSIZE only in weak body text — not governed subject evidence",
                    weak_review_only=True,
                )
            if re.search(r"\binsize\b", unrelated_text, re.IGNORECASE) and not re.search(
                r"\binsize\b", subject_text, re.IGNORECASE
            ):
                return PageEvidence(
                    False,
                    False,
                    "footer_or_nav_only",
                    "",
                    heading,
                    reason_code="manufacturer_not_confirmed",
                    reason_detail="INSIZE only in unrelated navigation/footer/related",
                )
            return PageEvidence(
                False,
                False,
                mfg_ev,
                "",
                heading,
                reason_code="manufacturer_not_confirmed",
                reason_detail=mfg_ev,
            )

        sku_ok, sku_ev = _sku_in_subject(
            subject_html,
            subject_text,
            sku,
            headings=headings,
            meta=meta,
            atomic_product=atomic_product,
            json_ld_status=json_ld_status,
            scripts_text=scripts_text,
        )
        if not sku_ok:
            if sku_ev.startswith("weak_"):
                return PageEvidence(
                    True,
                    False,
                    mfg_ev,
                    sku_ev,
                    heading,
                    reason_code="exact_sku_not_confirmed",
                    reason_detail="SKU only as weak body/script evidence — not accepted as exact",
                    weak_review_only=True,
                )
            if sku_ev in {"jsonld_cross_object_mix", "jsonld_ambiguous_products"}:
                return PageEvidence(
                    True,
                    False,
                    mfg_ev,
                    sku_ev,
                    heading,
                    reason_code="exact_sku_not_confirmed",
                    reason_detail=sku_ev,
                )
            if _sku_token_present(unrelated_text, sku) and not _sku_token_present(subject_text, sku):
                return PageEvidence(
                    True,
                    False,
                    mfg_ev,
                    "related_or_nav_only",
                    heading,
                    reason_code="exact_sku_not_confirmed",
                    reason_detail="SKU only in related/nav/footer/breadcrumb sections",
                )
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(sku)}[A-Za-z0-9]", subject_text):
                return PageEvidence(
                    True,
                    False,
                    mfg_ev,
                    "prefix_of_longer_sku",
                    heading,
                    reason_code="exact_sku_not_confirmed",
                    reason_detail="SKU only as prefix of another token",
                )
            return PageEvidence(
                True,
                False,
                mfg_ev,
                sku_ev,
                heading,
                reason_code="exact_sku_not_confirmed",
                reason_detail=sku_ev,
            )

        return PageEvidence(
            True,
            True,
            mfg_ev,
            sku_ev,
            heading or f"detail_url:{detail_url}",
        )
