"""Data-quality checks. Conflicts are flagged, never silently merged."""

from __future__ import annotations

from collections import Counter, defaultdict

from zcc_ir_catalog.models import QualityIssue, SourceProduct
from zcc_ir_catalog.normalize import manufacturer_identity_key


def _examples(values: list[str], limit: int = 5) -> list[str]:
    return values[:limit]


def quality_report(products: list[SourceProduct]) -> list[QualityIssue]:
    issues: list[QualityIssue] = []

    def add(kind: str, groups: dict[str, list[str]], message: str) -> None:
        for key, urls in groups.items():
            if len(urls) < 2 and kind.endswith("collision"):
                continue
            if kind.startswith("duplicate_") and len(urls) < 2:
                continue
            issues.append(
                QualityIssue(
                    kind=kind,
                    key=key,
                    count=len(urls),
                    examples=_examples(urls),
                    message=message,
                )
            )

    by_id: dict[str, list[str]] = defaultdict(list)
    by_url: dict[str, list[str]] = defaultdict(list)
    by_internal: dict[str, list[str]] = defaultdict(list)
    by_identity: dict[str, list[str]] = defaultdict(list)
    missing_brand: list[str] = []
    missing_identity: list[str] = []
    missing_category: list[str] = []
    impossible_price: list[str] = []
    malformed_url: list[str] = []
    conflicting_identity: list[str] = []

    for product in products:
        url = product.canonical_url or product.source_url
        if product.source_product_id:
            by_id[product.source_product_id].append(url)
        if url:
            by_url[url].append(url)
        if product.source_internal_sku:
            by_internal[product.source_internal_sku].append(url)
        ident = ""
        if product.brand_normalized and product.part_number:
            ident = f"{product.brand_normalized}|{product.part_number}"
            by_identity[ident].append(url)
        if not product.brand_normalized:
            missing_brand.append(url)
        if not product.manufacturer_code and not product.source_product_id:
            missing_identity.append(url)
        if not product.category_path:
            missing_category.append(url)
        if product.price_status == "invalid":
            impossible_price.append(url)
        if not (product.source_url or "").startswith("https://zcc.ir/"):
            malformed_url.append(url or product.source_url or "")
        if product.manufacturer_code:
            key = manufacturer_identity_key(product.manufacturer_code)
            if key != (product.part_number or ""):
                conflicting_identity.append(url)
        if "brand_token_conflict" in " ".join(product.parse_flags):
            conflicting_identity.append(url)

    add("duplicate_source_id", dict(by_id), "duplicate source product id")
    add("duplicate_canonical_url", dict(by_url), "duplicate canonical URL")
    add("duplicate_internal_sku", dict(by_internal), "duplicate internal numeric SKU")
    add("sku_normalization_collision", dict(by_identity), "same brand+manufacturer identity on multiple URLs")

    def singleton(kind: str, urls: list[str], message: str) -> None:
        if urls:
            issues.append(
                QualityIssue(kind=kind, key="*", count=len(urls), examples=_examples(urls), message=message)
            )

    singleton("missing_brand", missing_brand, "products without a trusted brand")
    singleton("missing_usable_identity", missing_identity, "products without manufacturer code or source id")
    singleton("missing_category", missing_category, "products without category path")
    singleton("impossible_price", impossible_price, "non-positive or unusable price")
    singleton("malformed_url", malformed_url, "source URL is not https://zcc.ir/...")
    singleton("conflicting_identity", conflicting_identity, "identity fields conflict")

    # Collision is one source name mapping to multiple normalized brands.
    source_to_norm: dict[str, set[str]] = defaultdict(set)
    for product in products:
        if product.brand and product.brand_normalized:
            source_to_norm[product.brand].add(product.brand_normalized)
    brand_name_collisions = {k: sorted(v) for k, v in source_to_norm.items() if len(v) > 1}
    for key, norms in brand_name_collisions.items():
        issues.append(
            QualityIssue(
                kind="brand_normalization_collision",
                key=key,
                count=len(norms),
                examples=norms,
                message="one source brand string mapped to multiple normalized brands",
            )
        )

    return issues


def duplicate_counts(issues: list[QualityIssue]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for issue in issues:
        if issue.kind.startswith("duplicate_") or issue.kind.endswith("collision"):
            counts[issue.kind] += 1
    return dict(counts)
