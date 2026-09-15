"""Image manifest for planned creates/updates (no upload)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

from zcc_ir_catalog.models import SourceProduct

from zcc_ir_phase2.reconcile import Phase2ReconcileRow


@dataclass
class ImageManifestRow:
    source_product_identity: str
    source_url: str
    main_image_url: str | None
    gallery_urls: list[str]
    image_count: int
    placeholder_flags: list[str]
    broken_url_flags: list[str]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["gallery_urls"] = list(self.gallery_urls)
        data["placeholder_flags"] = list(self.placeholder_flags)
        data["broken_url_flags"] = list(self.broken_url_flags)
        return data


def _url_ok(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def build_image_manifest(
    products: list[SourceProduct],
    reconcile: list[Phase2ReconcileRow],
) -> list[ImageManifestRow]:
    need = {
        r.source_url
        for r in reconcile
        if r.primary_state in {"CREATE_CANDIDATE", "UPDATE_CONTENT_CANDIDATE"}
    }
    rows: list[ImageManifestRow] = []
    for product in products:
        if product.source_url not in need:
            continue
        identity = product.part_number or product.source_internal_sku or product.source_url
        placeholders: list[str] = []
        broken: list[str] = []
        if "missing_image" in product.parse_flags:
            placeholders.append("missing_image_flag")
        if product.main_image_url and not _url_ok(product.main_image_url):
            broken.append("main_image_malformed")
        gallery = [u for u in product.gallery_image_urls if u]
        rows.append(
            ImageManifestRow(
                source_product_identity=str(identity),
                source_url=product.source_url,
                main_image_url=product.main_image_url,
                gallery_urls=gallery,
                image_count=product.gallery_count or len(gallery) + (1 if product.main_image_url else 0),
                placeholder_flags=placeholders,
                broken_url_flags=broken,
            )
        )
    rows.sort(key=lambda r: r.source_url)
    return rows
