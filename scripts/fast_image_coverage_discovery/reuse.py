"""Revalidate prior external discovery artifacts as candidate input."""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path

from .contracts import DiscoveryCandidate, RunProduct
from .identity import classify_identity, owner_policy_for_country, temporary_primary_eligible
from .sources.registry import is_iranian_domain

PRIOR_ROOT = Path("/home/moahmmad/Projects/Karzar-image-discovery")
CANDIDATE_GLOBS = ("**/candidates.csv", "**/manifest.csv", "**/green*.csv")


def _iter_prior_rows(root: Path) -> list[dict[str, str]]:
    if not root.is_dir():
        return []
    rows: list[dict[str, str]] = []
    for zp in sorted(root.glob("*.zip")):
        try:
            with zipfile.ZipFile(zp) as zf:
                for name in zf.namelist():
                    low = name.lower()
                    if not (low.endswith("candidates.csv") or low.endswith("manifest.csv")):
                        continue
                    with zf.open(name) as fh:
                        text = fh.read().decode("utf-8", errors="replace")
                    reader = csv.DictReader(text.splitlines())
                    rows.extend(dict(r) for r in reader)
        except Exception:
            continue
    return rows


def revalidate_prior_candidate(
    row: dict[str, str],
    product: RunProduct,
) -> DiscoveryCandidate | None:
    sku = product.sku
    row_sku = str(row.get("sku") or "").strip()
    if row_sku and row_sku.strip().upper() != sku.strip().upper():
        return None
    page_url = str(row.get("source_detail_url") or row.get("detail_url") or row.get("source_page_url") or "")
    image_url = str(row.get("source_image_url") or row.get("final_image_url") or row.get("image_url") or "")
    if not page_url or not image_url:
        return None
    domain = page_url.split("/")[2] if "://" in page_url else ""
    country = "IR" if is_iranian_domain(domain) else "XX"
    policy = owner_policy_for_country(country)
    status, match_type, brand_ev, sku_ev, reason = classify_identity(
        sku=sku,
        brand_key=product.brand_key,
        product_name=product.product_name,
        page_title=str(row.get("product_name") or product.product_name),
        page_text=str(row.get("sku_evidence") or row.get("page_subject_evidence") or product.product_name),
        has_pdp_structure=True,
        image_is_product_gallery=True,
        source_country=country,
    )
    if status == "red_rejected":
        return None
    return DiscoveryCandidate(
        product_id=product.product_id,
        sku=sku,
        brand_key=product.brand_key,
        product_name=product.product_name,
        category=product.category_slug,
        source_id="prior_artifact",
        source_domain=domain,
        source_country=country,
        source_class="prior_artifact_revalidated",
        lane="REUSE",
        source_page_url=page_url,
        source_image_url=image_url,
        match_type=match_type,
        brand_evidence=brand_ev,
        sku_model_evidence=sku_ev,
        page_identity_evidence="prior_artifact",
        gallery_identity_evidence="prior_manifest",
        owner_usage_policy=policy,  # type: ignore[arg-type]
        discovery_status=status,  # type: ignore[arg-type]
        temporary_primary_eligible=temporary_primary_eligible(policy),
        reason_code=reason,
        stop_search=status == "green_exact",
    )


def load_reuse_candidates(product: RunProduct, root: Path = PRIOR_ROOT) -> list[DiscoveryCandidate]:
    out: list[DiscoveryCandidate] = []
    for row in _iter_prior_rows(root):
        cand = revalidate_prior_candidate(row, product)
        if cand:
            out.append(cand)
    return out
