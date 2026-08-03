"""INSIZE / TOSAG (www.tosag.ch) adapter — validation of governed CSV candidates."""

from __future__ import annotations

import csv
import html as html_lib
import re
from pathlib import Path
from typing import Any

from ..contracts import ImageCandidate, PageEvidence, derive_source_candidate_key
from .base import SourceAdapter
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


def _json_ld_consistent_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Only Product nodes whose brand/SKU fields are internally non-contradictory placeholders.

    Consistency rule: if both brand and a SKU-like field are present, both must be non-empty
    strings (Product subject). Conflicting multi-brand bags are excluded by caller checks.
    """
    out: list[dict[str, Any]] = []
    for prod in products:
        brand = _json_ld_brand_name(prod).strip()
        skus = [str(prod.get(f) or "").strip() for f in ("sku", "mpn", "productID")]
        skus = [s for s in skus if s]
        # Require Product-typed node already filtered; drop empty shells
        if not brand and not skus:
            continue
        out.append(prod)
    return out


def _manufacturer_in_subject(
    subject_html: str,
    subject_text: str,
    *,
    headings: list[str],
    meta: dict[str, str],
    products: list[dict[str, Any]],
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

    for prod in _json_ld_consistent_products(products):
        brand_name = _json_ld_brand_name(prod)
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
    products: list[dict[str, Any]],
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

    for key, val in meta.items():
        if _sku_token_present(val, sku) and any(
            x in key for x in ("sku", "mpn", "product:retailer_item_id", "product_id")
        ):
            return True, f"meta:{key}:{sku}"

    for prod in _json_ld_consistent_products(products):
        brand_name = _json_ld_brand_name(prod)
        # Brand/SKU evidence must be internally consistent for the Product subject
        sku_fields = [str(prod.get(f) or "") for f in ("sku", "mpn", "productID")]
        if any(_sku_token_present(sf, sku) for sf in sku_fields):
            if brand_name and not re.search(r"\binsize\b", brand_name, re.IGNORECASE):
                continue  # inconsistent Product subject for INSIZE adapter
            return True, f"jsonld_sku:{sku}"

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
        if max_images_per_product <= 0:
            raise SystemExit("ERROR: --max-images-per-product must be > 0")
        if candidates_csv is None:
            raise SystemExit("insize_tosag requires --candidates-csv")
        product_skus: set[str] | None = None
        if products_csv is not None:
            product_skus = set()
            with products_csv.open(newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    s = (row.get("sku") or "").strip()
                    if s:
                        product_skus.add(s)

        filters = set(sku_filters or [])
        by_sku: dict[str, list[ImageCandidate]] = {}
        seen_source: dict[str, set[tuple[str, str]]] = {}
        with candidates_csv.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                sku = self.normalize_sku(row.get("sku") or "")
                if not sku:
                    continue
                if filters and sku not in filters:
                    continue
                if product_skus is not None and sku not in product_skus:
                    continue
                detail = (row.get("detail_url") or "").strip()
                image = (row.get("image_url") or "").strip()
                if not detail or not image:
                    continue
                # Deduplicate exact detail/image pairs before role assignment
                key = (detail, image)
                if key in seen_source.setdefault(sku, set()):
                    continue
                seen_source[sku].add(key)
                product_id = (row.get("product_id") or "").strip()
                cand = ImageCandidate(
                    sku=sku,
                    product_name=(row.get("product_name") or "").strip(),
                    brand=(row.get("brand") or self.brand).strip() or self.brand,
                    detail_url=detail,
                    image_url=image,
                    source_adapter=self.name,
                    confidence=(row.get("confidence") or "very_high").strip() or "very_high",
                    image_role="primary",
                    source_rank=1,
                    display_order_candidate=1,
                    # Index assigned after dedupe; identity key uses detail|image only (index=0)
                    source_image_index=0,
                    product_id=product_id,
                )
                # Stable source identity independent of duplicate-row presence
                cand.source_candidate_key = derive_source_candidate_key(
                    detail_url=detail,
                    image_url=image,
                    source_image_index=0,
                )
                by_sku.setdefault(sku, []).append(cand)

        ordered_skus: list[str] = []
        seen: set[str] = set()
        with candidates_csv.open(newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                sku = self.normalize_sku(row.get("sku") or "")
                if sku in by_sku and sku not in seen:
                    ordered_skus.append(sku)
                    seen.add(sku)

        if offset:
            ordered_skus = ordered_skus[offset:]
        if limit is not None:
            ordered_skus = ordered_skus[:limit]

        out: list[ImageCandidate] = []
        for sku in ordered_skus:
            # max-images applies after dedupe
            cands = by_sku[sku][:max_images_per_product]
            for i, c in enumerate(cands):
                c.source_image_index = i
                c.display_order_candidate = i + 1
                c.source_rank = i + 1
                c.image_role = "primary" if i == 0 else "alternate"
                # Keep source_candidate_key from detail|image (stable); role changes candidate_id
                c.source_candidate_key = derive_source_candidate_key(
                    detail_url=c.detail_url,
                    image_url=c.image_url,
                    source_image_index=0,
                )
                c.ensure_identity()
                out.append(c)
        return out

    def validate_page(self, *, sku: str, page_html: str, detail_url: str) -> PageEvidence:
        parsed = parse_page_subject(page_html)
        subject_html = parsed.subject_html()
        unrelated_html = parsed.unrelated_html()
        scripts_html = parsed.scripts_html()
        subject_text = _text(subject_html)
        unrelated_text = _text(unrelated_html)
        scripts_text = _text(scripts_html)
        headings = list(parsed.headings)
        meta = dict(parsed.meta_fields)
        products = list(parsed.json_ld_products)

        mfg_ok, mfg_ev = _manufacturer_in_subject(
            subject_html,
            subject_text,
            headings=headings,
            meta=meta,
            products=products,
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
            products=products,
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
