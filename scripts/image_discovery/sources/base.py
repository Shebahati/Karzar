"""Source adapter protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..contracts import ImageCandidate, PageEvidence


class SourceAdapter(ABC):
    """Brand/source-specific discovery and page validation."""

    name: str
    brand: str

    @abstractmethod
    def allowed_hosts(self) -> frozenset[str]:
        raise NotImplementedError

    @abstractmethod
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
        """Return ordered candidates.

        Current INSIZE path validates governed CSV candidates (not open-web crawl).
        """
        raise NotImplementedError

    @abstractmethod
    def validate_page(self, *, sku: str, page_html: str, detail_url: str) -> PageEvidence:
        raise NotImplementedError

    def normalize_sku(self, sku: str) -> str:
        return sku.strip()
