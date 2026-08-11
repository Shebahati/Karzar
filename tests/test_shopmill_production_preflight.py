"""Tests for read-only ShopMill production preflight path safety."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.shopmill_watermark.production_preflight import (
    normalize_relative_path,
    resolve_under_root,
    run_preflight,
)


def test_normalize_rejects_traversal_and_absolute(tmp_path: Path):
    assert normalize_relative_path("1381/foo.webp") == "1381/foo.webp"
    assert normalize_relative_path("../etc/passwd") is None
    assert normalize_relative_path("/abs/path") is None
    assert normalize_relative_path("a/../../b") is None
    assert normalize_relative_path("") is None


def test_resolve_under_root(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    rel = "1/a.webp"
    (root / "1").mkdir()
    (root / "1" / "a.webp").write_bytes(b"abc")
    resolved = resolve_under_root(root, rel)
    assert resolved is not None
    assert resolved.is_file()
    assert resolve_under_root(root, "../outside") is None


def test_preflight_classifies_exact_and_missing(tmp_path: Path):
    products = tmp_path / "products"
    products.mkdir()
    (products / "10").mkdir()
    target = products / "10" / "x.webp"
    target.write_bytes(b"hello-bytes")
    import csv
    import hashlib

    expected = hashlib.sha256(b"hello-bytes").hexdigest()

    manifest = tmp_path / "manifest.csv"
    fields = [
        "product_id",
        "sku",
        "product_slug",
        "product_name",
        "brand_name",
        "image_id",
        "sha256_original",
        "image_url_original",
        "mapped_local_relative_path",
        "preview_path",
        "remediation_method",
        "replacement_source",
        "output_path",
        "sha256_final",
        "width",
        "height",
        "remaining_logo_yellow",
        "remediation_ok",
        "reason",
        "verification_status",
    ]
    with manifest.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "product_id": "10",
                "sku": "SKU",
                "product_slug": "slug",
                "product_name": "name",
                "brand_name": "brand",
                "image_id": "1",
                "sha256_original": expected,
                "image_url_original": "url",
                "mapped_local_relative_path": "10/x.webp",
                "preview_path": "",
                "remediation_method": "method_c",
                "replacement_source": "",
                "output_path": "",
                "sha256_final": "deadbeef",
                "width": "1",
                "height": "1",
                "remaining_logo_yellow": "0",
                "remediation_ok": "True",
                "reason": "",
                "verification_status": "clean",
            }
        )
        writer.writerow(
            {
                "product_id": "11",
                "sku": "SKU2",
                "product_slug": "slug2",
                "product_name": "name2",
                "brand_name": "brand",
                "image_id": "2",
                "sha256_original": "abcd",
                "image_url_original": "url",
                "mapped_local_relative_path": "11/missing.webp",
                "preview_path": "",
                "remediation_method": "method_c",
                "replacement_source": "",
                "output_path": "",
                "sha256_final": "deadbeef",
                "width": "1",
                "height": "1",
                "remaining_logo_yellow": "0",
                "remediation_ok": "True",
                "reason": "",
                "verification_status": "clean",
            }
        )
    report = tmp_path / "report"
    code = run_preflight(
        manifest=manifest,
        storage_root=products,
        report_dir=report,
        expected_target_paths=2,
        expected_unique_assets=2,
    )
    assert code == 0
    data = json.loads((report / "preflight-report.json").read_text(encoding="utf-8"))
    assert data["EXACT_MATCH"] == 1
    assert data["MISSING_SOURCE"] == 1
    assert data["TARGET_PATHS_ACCOUNTED_FOR"] == 2
    assert data["reconciliation_ok"] is True
