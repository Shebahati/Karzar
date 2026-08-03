"""Focused tests for IMG-02A-02 existing image human-review batches."""

from __future__ import annotations

import hashlib
import io
import json
import socket
import zipfile
from pathlib import Path

import pytest
from PIL import Image
from scripts.image_audit.output import write_checksums
from scripts.image_review.contracts import ReviewError
from scripts.image_review.pipeline import build_pilot_package, semantic_compare_summaries
from scripts.image_review.prescreen import compute_prescreen
from scripts.image_review.selection import group_assets, select_pilot_assets
from scripts.image_review.source_inventory import verify_checksum_manifest

REPO = Path(__file__).resolve().parents[1]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _png_bytes(size: tuple[int, int] = (80, 60), *, color=(20, 40, 60), alpha: int | None = None) -> bytes:
    if alpha is None:
        im = Image.new("RGB", size, color)
    else:
        im = Image.new("RGBA", size, color + (alpha,))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _write_source_snapshot(
    source_dir: Path,
    *,
    rows: list[dict],
    summary: dict,
) -> str:
    source_dir.mkdir(parents=True, exist_ok=True)
    # minimal required companions
    (source_dir / "inventory.json").write_text("[]\n", encoding="utf-8")
    (source_dir / "run-metadata.json").write_text("{}\n", encoding="utf-8")
    (source_dir / "duplicate-exact-sha.csv").write_text("sha256\n", encoding="utf-8")
    (source_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fields = [
        "image_id",
        "product_id",
        "sku",
        "product_slug",
        "product_name",
        "brand_id",
        "brand_name",
        "category_id",
        "category_name",
        "image_url",
        "is_primary",
        "display_order",
        "mapped_local_relative_path",
        "local_exists",
        "local_entry_status",
        "byte_size",
        "sha256",
        "detected_format",
        "mime_type",
        "width",
        "height",
        "decode_status",
        "audit_status",
    ]
    lines = [",".join(fields)]
    for r in rows:
        lines.append(",".join(str(r.get(f, "")) for f in fields))
    (source_dir / "inventory.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_checksums(
        source_dir,
        [
            "inventory.csv",
            "inventory.json",
            "summary.json",
            "run-metadata.json",
            "duplicate-exact-sha.csv",
        ],
    )
    return _sha((source_dir / "checksums.sha256").read_bytes())


def _row(**kwargs):
    base = {
        "sku": "SKU",
        "product_slug": "slug",
        "product_name": "نام",
        "brand_id": 1,
        "brand_name": "BrandA",
        "category_id": 1,
        "category_name": "Cat",
        "image_url": "/static/uploads/products/x.png",
        "is_primary": "true",
        "display_order": 0,
        "local_exists": "true",
        "local_entry_status": "regular_image",
        "detected_format": "png",
        "mime_type": "image/png",
        "width": 80,
        "height": 60,
        "decode_status": "ok",
        "audit_status": "ok",
    }
    base.update(kwargs)
    return base


def _make_mini_world(tmp: Path, *, shared: int = 2, singleton: int = 2):
    storage = tmp / "storage"
    storage.mkdir()
    source = tmp / "source"
    rows = []
    image_id = 1
    product_id = 1
    # shared assets: each used by 2 products
    for i in range(shared):
        data = _png_bytes(color=(i * 10, 20, 30))
        digest = _sha(data)
        rel = f"shared/{digest[:8]}.png"
        path = storage / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        for _ in range(2):
            rows.append(
                _row(
                    image_id=image_id,
                    product_id=product_id,
                    brand_name=f"BrandShared{i}",
                    brand_id=100 + i,
                    mapped_local_relative_path=rel,
                    sha256=digest,
                    byte_size=len(data),
                    sku=f"S{product_id}",
                )
            )
            image_id += 1
            product_id += 1
    # singleton assets with round-robin brands
    brands = ["Alpha", "Beta", "Alpha", "Gamma"]
    for i in range(singleton):
        data = _png_bytes(color=(5, i * 12, 40))
        digest = _sha(data)
        rel = f"single/{digest[:8]}.png"
        path = storage / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        bname = brands[i % len(brands)]
        rows.append(
            _row(
                image_id=image_id,
                product_id=product_id,
                brand_name=bname,
                brand_id=200 + i,
                mapped_local_relative_path=rel,
                sha256=digest,
                byte_size=len(data),
                sku=f"U{product_id}",
            )
        )
        image_id += 1
        product_id += 1
    # one remote deferred
    rows.append(
        _row(
            image_id=9999,
            product_id=9999,
            audit_status="remote_unverified",
            local_exists="false",
            local_entry_status="",
            decode_status="",
            sha256="",
            mapped_local_relative_path="",
            image_url="https://example.com/x.jpg",
        )
    )
    summary = {
        "total_products": shared * 2 + singleton + 1,
        "total_product_images": len(rows),
        "valid_local_image_rows": shared * 2 + singleton,
        "external_remote_rows": 1,
        "missing_local_file_rows": 0,
        "decode_failed_rows": 0,
        "unique_local_asset_sha256s": shared + singleton,
        "exact_duplicate_sha_groups": shared,
        "cross_product_duplicate_sha_groups": shared,
        "cross_brand_duplicate_sha_groups": 0,
    }
    digest = _write_source_snapshot(source, rows=rows, summary=summary)
    return source, storage, digest, summary, shared, singleton


def test_verified_source_checksum_manifest_accepted(tmp_path: Path):
    source, storage, digest, summary, shared, singleton = _make_mini_world(tmp_path)
    mapping = verify_checksum_manifest(source, expected_checksums_digest=digest)
    assert "inventory.csv" in mapping


def test_checksum_mismatch_rejected(tmp_path: Path):
    source, *_ = _make_mini_world(tmp_path)
    with pytest.raises(ReviewError, match="digest mismatch"):
        verify_checksum_manifest(source, expected_checksums_digest="0" * 64)


def test_wrong_source_summary_rejected(tmp_path: Path):
    source, storage, digest, summary, shared, singleton = _make_mini_world(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    bad = dict(summary)
    bad["total_products"] = 1
    (source / "summary.json").write_text(json.dumps(bad), encoding="utf-8")
    # rewrite checksums after tamper
    write_checksums(
        source,
        [
            "inventory.csv",
            "inventory.json",
            "summary.json",
            "run-metadata.json",
            "duplicate-exact-sha.csv",
        ],
    )
    digest2 = _sha((source / "checksums.sha256").read_bytes())
    with pytest.raises(ReviewError, match="summary.total_products"):
        build_pilot_package(
            source_dir=source,
            storage_root=storage,
            output_dir=out,
            repository_root=REPO,
            expected_checksums_digest=digest2,
            expected_summary=summary,
            shared_count=shared,
            singleton_count=singleton,
        )


def test_grouping_remote_and_identity(tmp_path: Path):
    source, storage, digest, summary, shared, singleton = _make_mini_world(tmp_path)
    from scripts.image_review.source_inventory import load_verified_source

    _, _, rows = load_verified_source(
        source, expected_checksums_digest=digest, expected_summary=summary
    )
    assets, remote = group_assets(rows)
    assert len(remote) == 1
    assert remote[0]["reason"] == "remote_unverified_out_of_scope"
    assert all(a["asset_id"] == a["sha256"] for a in assets)
    shared_asset = next(a for a in assets if a["product_count"] > 1)
    assert len(shared_asset["assignments"]) == shared_asset["reference_count"]


def test_selection_deterministic_and_exact_counts(tmp_path: Path):
    source, storage, digest, summary, shared, singleton = _make_mini_world(
        tmp_path, shared=3, singleton=4
    )
    from scripts.image_review.source_inventory import load_verified_source

    _, _, rows = load_verified_source(
        source, expected_checksums_digest=digest, expected_summary=summary
    )
    assets, _ = group_assets(rows)
    a1, m1 = select_pilot_assets(assets, shared_count=2, singleton_count=2, total=4)
    a2, m2 = select_pilot_assets(assets, shared_count=2, singleton_count=2, total=4)
    assert m1["selected_asset_ids"] == m2["selected_asset_ids"]
    assert len({x["sha256"] for x in a1}) == 4
    assert len(a1) == 4


def test_pilot_package_happy_path_and_html_boundaries(tmp_path: Path):
    source, storage, digest, summary, shared, singleton = _make_mini_world(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    zip_path = tmp_path / "pilot.zip"

    def guard():
        # fail if anything tries to open a network socket
        real = socket.socket

        def blocked(*a, **k):
            raise AssertionError("network socket opened")

        socket.socket = blocked  # type: ignore[assignment]
        return real

    real_sock = guard()
    try:
        result = build_pilot_package(
            source_dir=source,
            storage_root=storage,
            output_dir=out,
            repository_root=REPO,
            expected_checksums_digest=digest,
            expected_summary=summary,
            shared_count=shared,
            singleton_count=singleton,
            zip_path=zip_path,
        )
    finally:
        socket.socket = real_sock  # type: ignore[assignment]

    assert result["selected_unique_assets"] == shared + singleton
    assert result["database_accessed"] is False
    assert result["network_requests_performed"] == 0
    assert (out / "review.html").exists()
    html = (out / "review.html").read_text(encoding="utf-8")
    assert "http://" not in html
    assert "https://" not in html
    assert "image_url" not in html
    assert "source_relative_path" not in html
    assert "<script src=" not in html.lower()
    assert "googleapis" not in html.lower()
    assert "cdn.jsdelivr" not in html.lower()
    assert "review_schema_version" in html
    for asset_id in result["selected_asset_ids"]:
        assert asset_id in html
    assign_ids = [
        line.split(",")[0]
        for line in (out / "assignment-manifest.csv").read_text(encoding="utf-8").splitlines()[1:]
        if line.strip()
    ]
    # assignment_id is first column
    for aid in assign_ids:
        assert aid in html
    assert "assignment_id" in html
    # templates default rights
    asset_csv = (out / "asset-review-template.csv").read_text(encoding="utf-8")
    assert "review_required" in asset_csv
    assert "cleared_by_owner" not in asset_csv.splitlines()[1]
    schema = json.loads((out / "review-schema.json").read_text(encoding="utf-8"))
    assert schema["review_schema_version"] == 1
    # zip has no source originals tree
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert any(n.endswith("review.html") for n in names)
    assert not any("/data/uploads/" in n for n in names)
    assert result["pilot_zip_sha256"]


def test_symlink_storage_rejected(tmp_path: Path):
    source, storage, digest, summary, shared, singleton = _make_mini_world(tmp_path)
    linked = tmp_path / "linked-storage"
    linked.symlink_to(storage)
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(ReviewError):
        build_pilot_package(
            source_dir=source,
            storage_root=linked,
            output_dir=out,
            repository_root=REPO,
            expected_checksums_digest=digest,
            expected_summary=summary,
            shared_count=shared,
            singleton_count=singleton,
        )


def test_output_inside_repo_rejected(tmp_path: Path):
    source, storage, digest, summary, shared, singleton = _make_mini_world(tmp_path)
    out = REPO / "tmp-should-not-exist-img02a02"
    out.mkdir(exist_ok=True)
    try:
        with pytest.raises(ReviewError):
            build_pilot_package(
                source_dir=source,
                storage_root=storage,
                output_dir=out,
                repository_root=REPO,
                expected_checksums_digest=digest,
                expected_summary=summary,
                shared_count=shared,
                singleton_count=singleton,
            )
    finally:
        if out.exists():
            for child in out.iterdir():
                child.unlink()
            out.rmdir()


def test_source_sha_mismatch_rejected(tmp_path: Path):
    source, storage, digest, summary, shared, singleton = _make_mini_world(tmp_path)
    # corrupt one storage file bytes without updating inventory
    target = next(storage.rglob("*.png"))
    target.write_bytes(_png_bytes(color=(1, 2, 3)))
    out = tmp_path / "out"
    out.mkdir()
    with pytest.raises(ReviewError, match="SHA-256 mismatch"):
        build_pilot_package(
            source_dir=source,
            storage_root=storage,
            output_dir=out,
            repository_root=REPO,
            expected_checksums_digest=digest,
            expected_summary=summary,
            shared_count=shared,
            singleton_count=singleton,
        )
    assert list(out.iterdir()) == []


def test_preview_aspect_and_no_crop(tmp_path: Path):
    from scripts.image_review.previews import generate_derivatives

    storage = tmp_path / "st"
    storage.mkdir()
    data = _png_bytes((200, 100))
    digest = _sha(data)
    rel = "a.png"
    (storage / rel).write_bytes(data)
    prev = tmp_path / "p"
    th = tmp_path / "t"
    prev.mkdir()
    th.mkdir()
    info = generate_derivatives(
        storage,
        relative_path=rel,
        expected_sha256=digest,
        preview_dir=prev,
        thumb_dir=th,
    )
    assert info["preview_width"] / info["preview_height"] == pytest.approx(2.0)
    assert info["generation_parameters"]["crop"] is False


def test_prescreen_deterministic_and_watermark_not_run():
    im = Image.new("RGB", (100, 50), (10, 10, 10))
    a = compute_prescreen(im)
    b = compute_prescreen(im)
    assert a == b
    assert a["watermark_prescreen"] == "not_run"
    assert a["watermark_review_required"] is True
    assert a["low_resolution_candidate"] is True
    assert a["extreme_aspect_candidate"] is False


def test_transparent_preview_deterministic(tmp_path: Path):
    from scripts.image_review.previews import generate_derivatives

    storage = tmp_path / "st"
    storage.mkdir()
    data = _png_bytes((64, 64), alpha=120)
    digest = _sha(data)
    (storage / "t.png").write_bytes(data)
    p1 = tmp_path / "p1"
    t1 = tmp_path / "t1"
    p2 = tmp_path / "p2"
    t2 = tmp_path / "t2"
    for d in (p1, t1, p2, t2):
        d.mkdir()
    a = generate_derivatives(storage, relative_path="t.png", expected_sha256=digest, preview_dir=p1, thumb_dir=t1)
    b = generate_derivatives(storage, relative_path="t.png", expected_sha256=digest, preview_dir=p2, thumb_dir=t2)
    assert a["preview_sha256"] == b["preview_sha256"]
    assert a["thumb_sha256"] == b["thumb_sha256"]
    assert a["prescreen"]["transparent_background_candidate"] is True


def test_second_run_semantic_stability(tmp_path: Path):
    source, storage, digest, summary, shared, singleton = _make_mini_world(tmp_path)
    out1 = tmp_path / "o1"
    out2 = tmp_path / "o2"
    out1.mkdir()
    out2.mkdir()
    r1 = build_pilot_package(
        source_dir=source,
        storage_root=storage,
        output_dir=out1,
        repository_root=REPO,
        expected_checksums_digest=digest,
        expected_summary=summary,
        shared_count=shared,
        singleton_count=singleton,
    )
    r2 = build_pilot_package(
        source_dir=source,
        storage_root=storage,
        output_dir=out2,
        repository_root=REPO,
        expected_checksums_digest=digest,
        expected_summary=summary,
        shared_count=shared,
        singleton_count=singleton,
    )
    semantic_compare_summaries(r1, r2)


def test_hash_seed_selection_stable(tmp_path: Path):
    source, storage, digest, summary, shared, singleton = _make_mini_world(tmp_path)
    from scripts.image_review.source_inventory import load_verified_source

    _, _, rows = load_verified_source(
        source, expected_checksums_digest=digest, expected_summary=summary
    )
    assets, _ = group_assets(rows)
    ids = []
    for _ in range(3):
        selected, meta = select_pilot_assets(
            assets, shared_count=shared, singleton_count=singleton, total=shared + singleton
        )
        ids.append(meta["selected_asset_ids"])
    assert ids[0] == ids[1] == ids[2]


def test_output_inside_storage_rejected(tmp_path: Path):
    source, storage, digest, summary, shared, singleton = _make_mini_world(tmp_path)
    out = storage / "nested-out"
    out.mkdir()
    with pytest.raises(ReviewError):
        build_pilot_package(
            source_dir=source,
            storage_root=storage,
            output_dir=out,
            repository_root=REPO,
            expected_checksums_digest=digest,
            expected_summary=summary,
            shared_count=shared,
            singleton_count=singleton,
        )


def test_html_payload_strips_urls_and_paths():
    from scripts.image_review.html_review import (
        assert_html_offline_contract,
        build_review_html,
        html_safe_assets,
        html_safe_assignments,
    )
    from scripts.image_review.review_schema import review_schema_document

    assets = [
        {
            "asset_id": "abc",
            "sha256": "abc",
            "source_relative_path": "brand/x.jpg",
            "preview_filename": "abc.jpg",
            "thumb_filename": "abc.jpg",
            "product_count": 1,
            "brands": ["Brand"],
            "width": 10,
            "height": 10,
            "byte_size": 1,
            "reference_count": 1,
            "low_resolution_candidate": False,
            "extreme_aspect_candidate": False,
            "transparent_background_candidate": False,
            "busy_or_nonuniform_border_candidate": False,
            "selection_segment": "singleton",
            "megapixels": 0.1,
            "aspect_ratio": 1.0,
        }
    ]
    assignments = [
        {
            "assignment_id": "abc:1:1",
            "asset_id": "abc",
            "image_id": 1,
            "product_id": 1,
            "sku": "S",
            "product_name": "P",
            "brand_name": "Brand",
            "category_name": "C",
            "image_url": "https://api.karzartools.com/static/uploads/products/x.jpg",
            "is_primary": True,
            "display_order": 0,
        }
    ]
    safe_a = html_safe_assets(assets)
    safe_b = html_safe_assignments(assignments)
    assert "source_relative_path" not in safe_a[0]
    assert "image_url" not in safe_b[0]
    html = build_review_html(
        batch_id="IMG-02A-02-PILOT-001",
        assets=assets,
        assignments=assignments,
        schema=review_schema_document(),
    )
    assert_html_offline_contract(html)
    assert "http://" not in html and "https://" not in html
    assert "image_url" not in html
    assert "source_relative_path" not in html
    assert "abc" in html and "abc:1:1" in html


def test_human_review_identity_against_external_pilot_if_present():
    from scripts.image_review.review_evidence import validate_human_review_bundle

    review = Path("/var/tmp/karzar-image-review/img02a02-pilot-001-human-review")
    pilot = Path(
        "/home/moahmmad/Projects/Karzar-image-review/IMG-02A-02-pilot-001/img02a02-pilot-001"
    )
    if not review.is_dir() or not pilot.is_dir():
        pytest.skip("external pilot/human-review artifacts not present")
    agg = validate_human_review_bundle(review, pilot_dir=pilot)
    assert agg["assets_reviewed"] == 100
    assert agg["assignments_reviewed"] == 465
    assert agg["watermark"]["distributor_or_retailer"] == 52
    assert agg["assignment_decisions"]["REPLACE_REQUIRED"] == 41
