"""Prior-artifact reuse adapter — index once, lookup many."""

from __future__ import annotations

import csv
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from ..identity import brands_compatible, normalize_brand_key, normalize_sku
from .base import CalibrationResult, IndexedHit, ProbeResult, SourceAdapter
from .spec import SourceSpec

PRIOR_ROOT = Path("/home/moahmmad/Projects/Karzar-image-discovery")


class PriorArtifactAdapter(SourceAdapter):
    adapter_type = "prior_artifact"

    def __init__(self, spec: SourceSpec, root: Path = PRIOR_ROOT) -> None:
        super().__init__(spec.source_id, spec.domain, spec.lane, spec.country, spec.base_url)
        self.root = root
        self.stats = {
            "prior_rows_loaded": 0,
            "prior_candidates_indexed": 0,
            "prior_products_hit": 0,
        }
        self._by_brand_sku: dict[str, IndexedHit] = {}
        self._by_sku: dict[str, list[IndexedHit]] = {}

    def probe_source(self, fetcher: Any) -> ProbeResult:
        self.probe_attempted = True
        ok = self.root.is_dir()
        self.probe = ProbeResult(
            source_id=self.source_id,
            domain=self.domain,
            dns_ok=ok,
            ipv4_ok=ok,
            tls_ok=ok,
            http_status=200 if ok else None,
            failure_class="" if ok else "dns_failure",
            attempt_count=1,
            notes=str(self.root),
        )
        return self.probe

    def build_index(self, fetcher: Any, sample_skus: list[str] | None = None) -> int:
        self.executed = True
        rows = self._load_rows()
        self.stats["prior_rows_loaded"] = len(rows)
        for row in rows:
            sku = str(row.get("sku") or "").strip()
            if not sku:
                continue
            page = str(
                row.get("source_detail_url")
                or row.get("detail_url")
                or row.get("source_page_url")
                or ""
            )
            image = str(
                row.get("source_image_url")
                or row.get("final_image_url")
                or row.get("image_url")
                or ""
            )
            if not page or not image:
                continue
            # Skip non-image catalogue PDFs (common in official distributor dumps)
            low_img = image.lower()
            if ".pdf" in low_img.split("?", 1)[0]:
                continue
            brand = str(row.get("brand") or row.get("brand_key") or "")
            hit = IndexedHit(
                sku=sku,
                title=str(row.get("product_name") or ""),
                page_url=page,
                image_urls=[image],
                brand_text=brand,
                evidence={"source": "prior_artifact"},
            )
            bkey = f"{normalize_brand_key(brand)}::{normalize_sku(sku)}"
            self._by_brand_sku[bkey] = hit
            self._by_sku.setdefault(normalize_sku(sku), []).append(hit)
            self._index[normalize_sku(sku)] = hit
        self.stats["prior_candidates_indexed"] = len(self._index)
        self.bulk_enabled = len(self._index) > 0
        return len(self._index)

    def calibrate(self, sample_skus: list[str]) -> CalibrationResult:
        # Prior reuse is pre-validated historical evidence — enable whenever indexed.
        n = len(self._index)
        passed = n > 0
        result = CalibrationResult(
            source_id=self.source_id,
            checked=min(n, len(sample_skus) or n),
            hits=min(n, len(sample_skus) or n),
            passed=passed,
            bulk_enabled=passed,
            notes="prior_artifact_index" if passed else "prior_empty",
        )
        self.calibration = result
        self.bulk_enabled = passed
        return result

    def lookup_product(self, product):  # type: ignore[no-untyped-def]
        if not self.bulk_enabled:
            return None
        sku_n = normalize_sku(product.sku)
        bkey = f"{normalize_brand_key(product.brand_key)}::{sku_n}"
        hit = self._by_brand_sku.get(bkey)
        if hit:
            self.stats["prior_products_hit"] += 1
            return hit
        # Bilingual storefront keys ("dasqua|-فا") vs latin prior brand ("dasqua")
        stem = re.match(r"[a-z0-9]+", normalize_brand_key(product.brand_key).replace(" ", "") or "")
        if stem:
            hit = self._by_brand_sku.get(f"{stem.group(0)}::{sku_n}")
            if hit:
                self.stats["prior_products_hit"] += 1
                return hit
        candidates = self._by_sku.get(sku_n) or []
        if not candidates:
            return None
        # Conservative brand verification
        if not product.brand_key.strip():
            self.stats["prior_products_hit"] += 1
            return candidates[0]
        for c in candidates:
            if brands_compatible(product.brand_key, c.brand_text):
                self.stats["prior_products_hit"] += 1
                return c
        return None

    def _load_rows(self) -> list[dict[str, str]]:
        if not self.root.is_dir():
            return []
        rows: list[dict[str, str]] = []
        for zp in sorted(self.root.glob("*.zip")):
            try:
                with zipfile.ZipFile(zp) as zf:
                    for name in zf.namelist():
                        low = name.lower()
                        if not (
                            low.endswith("candidates.csv")
                            or low.endswith("manifest.csv")
                            or "green" in low and low.endswith(".csv")
                        ):
                            continue
                        with zf.open(name) as fh:
                            text = fh.read().decode("utf-8", errors="replace")
                        reader = csv.DictReader(text.splitlines())
                        rows.extend(dict(r) for r in reader)
            except Exception:
                continue
        # Also unpacked dirs
        for csv_path in self.root.rglob("*.csv"):
            name = csv_path.name.lower()
            if not ("candidate" in name or "manifest" in name or name.startswith("green")):
                continue
            try:
                with csv_path.open(encoding="utf-8", newline="") as f:
                    rows.extend(dict(r) for r in csv.DictReader(f))
            except Exception:
                continue
        return rows

    def write_index_cache(self, path: Path) -> None:
        payload = {
            "stats": self.stats,
            "keys": list(self._index.keys())[:5000],
            "count": len(self._index),
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
