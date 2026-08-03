"""Tests for IMG-02A-01 read-only existing image inventory."""

from __future__ import annotations

import asyncio
import os
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from PIL import Image
from scripts.image_audit.contracts import AuditError, ImageRow, ProductRow, StorageEntry
from scripts.image_audit.database import ReadOnlyDbContext, assert_readonly_sql
from scripts.image_audit.inventory import run_inventory
from scripts.image_audit.output import (
    atomic_write_text,
    publish_inventory_outputs,
    write_checksums,
    write_json,
)
from scripts.image_audit.storage import (
    assert_disjoint_output_storage,
    assert_real_directory_no_symlink,
    classify_image_url,
    file_meta_for_mapped_path,
    inspect_regular_file,
    prepare_output_dir,
    scan_storage_tree,
)


def _jpeg_bytes(color: tuple[int, int, int] = (10, 20, 30), size: tuple[int, int] = (32, 32)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _png_bytes(color: tuple[int, int, int] = (1, 2, 3), size: tuple[int, int] = (24, 24)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_readonly_sql_guard_rejects_insert():
    with pytest.raises(AuditError) as ei:
        assert_readonly_sql("INSERT INTO product_images (id) VALUES (1)")
    assert ei.value.code == "sql_guard"


def test_readonly_sql_guard_rejects_update():
    with pytest.raises(AuditError):
        assert_readonly_sql("UPDATE products SET name='x' WHERE id=1")


def test_readonly_sql_guard_rejects_delete():
    with pytest.raises(AuditError):
        assert_readonly_sql("DELETE FROM product_images WHERE id=1")


def test_readonly_sql_guard_allows_select_and_txn_setup():
    assert_readonly_sql("SELECT id FROM product_images")
    assert_readonly_sql("SET TRANSACTION READ ONLY")
    assert_readonly_sql("SHOW transaction_read_only")


def test_readonly_sql_guard_rejects_read_write():
    with pytest.raises(AuditError):
        assert_readonly_sql("SET TRANSACTION READ WRITE")


def test_readonly_sql_guard_rejects_other_show():
    with pytest.raises(AuditError):
        assert_readonly_sql("SHOW search_path")


def test_readonly_sql_guard_rejects_pragma_assignment():
    with pytest.raises(AuditError):
        assert_readonly_sql("PRAGMA journal_mode=WAL")


def test_internal_absolute_static_url_maps(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url("/static/uploads/products/9/a.jpg", storage_root=root)
    assert cls.url_kind == "internal_static_absolute"
    assert cls.mapped_relative_path == "9/a.jpg"
    assert cls.query_present is False


def test_https_with_marker_maps_internal_absolute(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url(
        "https://cdn.example.com/static/uploads/products/9/a.jpg",
        storage_root=root,
    )
    assert cls.url_kind == "internal_static_absolute"
    assert cls.mapped_relative_path == "9/a.jpg"
    assert cls.url_host == "cdn.example.com"


def test_http_with_marker_maps_internal_absolute(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url(
        "http://evil.example/static/uploads/products/1/x.png",
        storage_root=root,
    )
    assert cls.url_kind == "internal_static_absolute"
    assert cls.mapped_relative_path == "1/x.png"


def test_lookalike_products_evil_rejects(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url("/static/uploads/products-evil/1/a.jpg", storage_root=root)
    assert cls.mapped_relative_path is None
    assert "missing_public_path_marker" in cls.reason_codes


def test_lookalike_products_backup_rejects(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url("/static/uploads/products_backup/1/a.jpg", storage_root=root)
    assert cls.mapped_relative_path is None
    assert "missing_public_path_marker" in cls.reason_codes


def test_internal_relative_static_url_maps(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url("static/uploads/products/9/b.png", storage_root=root)
    assert cls.url_kind == "internal_static_relative"
    assert cls.mapped_relative_path == "9/b.png"


def test_query_and_fragment_removed_not_persisted(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url(
        "https://cdn.example.com/static/uploads/products/1/x.jpg?token=SECRET&sig=1#frag",
        storage_root=root,
    )
    assert cls.query_present is True
    assert cls.url_host == "cdn.example.com"
    assert "SECRET" not in cls.sanitized_url
    assert "token=" not in cls.sanitized_url
    assert "#frag" not in cls.sanitized_url
    assert "@cdn" not in cls.sanitized_url
    assert cls.mapped_relative_path == "1/x.jpg"


def test_userinfo_stripped_url_host_preserved(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url(
        "https://user:pass@cdn.example.com/static/uploads/products/2/y.jpg",
        storage_root=root,
    )
    assert cls.url_host == "cdn.example.com"
    assert "user:" not in cls.sanitized_url
    assert "pass@" not in cls.sanitized_url


def test_encoded_traversal_rejects(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url(
        "/static/uploads/products/1/%2e%2e/%2e%2e/etc/passwd",
        storage_root=root,
    )
    assert cls.mapped_relative_path is None
    assert "path_traversal_rejected" in cls.reason_codes


def test_plain_traversal_rejects(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url("/static/uploads/products/../secret.jpg", storage_root=root)
    assert cls.mapped_relative_path is None
    assert "path_traversal_rejected" in cls.reason_codes


def test_windows_drive_path_rejects(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url("C:\\static\\uploads\\products\\1\\a.jpg", storage_root=root)
    assert cls.url_kind == "unsupported_scheme"
    assert cls.mapped_relative_path is None


def test_symlinked_storage_root_rejects(tmp_path: Path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(AuditError):
        assert_real_directory_no_symlink(link, label="storage-root")


def test_symlinked_nested_directory_rejects_without_reading_target(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    target = tmp_path / "outside"
    target.mkdir()
    (target / "secret.bin").write_bytes(b"secret-bytes")
    nested = root / "1"
    nested.mkdir()
    link = nested / "linked"
    link.symlink_to(target)
    entries = scan_storage_tree(root)
    statuses = {e.relative_path: e for e in entries}
    assert "1/linked" in statuses
    assert statuses["1/linked"].status == "symlink_rejected"
    assert statuses["1/linked"].sha256 is None
    assert not any(e.sha256 and "secret" in (e.relative_path or "") for e in entries)


def test_symlinked_file_rejects_without_hashing_target(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    target = tmp_path / "target.jpg"
    target.write_bytes(_jpeg_bytes())
    link = root / "x.jpg"
    link.symlink_to(target)
    entries = scan_storage_tree(root)
    assert len(entries) == 1
    assert entries[0].status == "symlink_rejected"
    assert entries[0].sha256 is None


def test_fifo_non_regular_rejects(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    fifo = root / "pipe.fifo"
    os.mkfifo(fifo)
    entries = scan_storage_tree(root)
    assert entries[0].status == "non_regular_rejected"
    assert entries[0].sha256 is None


def test_missing_local_file_reports(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url("/static/uploads/products/99/missing.jpg", storage_root=root)
    assert cls.mapped_relative_path == "99/missing.jpg"
    meta = file_meta_for_mapped_path(root, cls.mapped_relative_path)
    assert meta.local_exists is False


def test_file_meta_storage_index_no_filesystem_fallback(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    path = root / "hidden.jpg"
    path.write_bytes(_jpeg_bytes())
    index: dict[str, StorageEntry] = {}
    meta = file_meta_for_mapped_path(root, "hidden.jpg", storage_index=index)
    assert meta.local_exists is False
    assert meta.local_entry_status is None


def test_file_meta_propagates_rejected_ancestor(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    index = {
        "1/linked": StorageEntry(
            relative_path="1/linked",
            status="symlink_rejected",
            reason_codes=["symlink_rejected"],
        )
    }
    meta = file_meta_for_mapped_path(root, "1/linked/child.jpg", storage_index=index)
    assert meta.local_exists is False
    assert meta.local_entry_status == "symlink_rejected"


def test_valid_jpeg_metadata_and_sha(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    path = root / "a.jpg"
    data = _jpeg_bytes()
    path.write_bytes(data)
    entry = inspect_regular_file(path, relative_path="a.jpg")
    assert entry.status == "regular_image"
    assert entry.mime_type == "image/jpeg"
    assert entry.sha256 is not None
    assert len(entry.sha256) == 64
    assert entry.width == 32 and entry.height == 32
    assert entry.decode_status == "ok"


def test_valid_png_metadata_and_sha(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    path = root / "a.png"
    path.write_bytes(_png_bytes())
    entry = inspect_regular_file(path, relative_path="a.png")
    assert entry.status == "regular_image"
    assert entry.mime_type == "image/png"
    assert entry.decode_status == "ok"


def test_extension_content_mismatch_uses_signature(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    path = root / "lie.png"
    path.write_bytes(_jpeg_bytes())
    entry = inspect_regular_file(path, relative_path="lie.png")
    assert entry.mime_type == "image/jpeg"
    assert entry.detected_format == "jpg"


def test_decode_failure_isolated(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    path = root / "bad.jpg"
    path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 20)
    entry = inspect_regular_file(path, relative_path="bad.jpg")
    assert entry.status == "decode_failed"
    assert entry.decode_status == "decode_failed"
    assert entry.sha256 is not None


def test_decompression_bomb_isolated_decode_failed(tmp_path: Path, monkeypatch):
    root = tmp_path / "products"
    root.mkdir()
    path = root / "bomb.jpg"
    path.write_bytes(_jpeg_bytes())

    from PIL import Image as PILImage

    def boom_open(_path):
        raise PILImage.DecompressionBombError("too large")

    monkeypatch.setattr("PIL.Image.open", boom_open)
    entry = inspect_regular_file(path, relative_path="bomb.jpg")
    assert entry.status == "decode_failed"
    assert entry.decode_status == "decode_failed"


def test_external_http_remote_unverified_zero_requests(tmp_path: Path):
    root = tmp_path / "products"
    root.mkdir()
    cls = classify_image_url("http://cdn.example.com/a.jpg", storage_root=root)
    assert cls.url_kind == "external_http"
    assert "remote_unverified" in cls.reason_codes
    assert cls.mapped_relative_path is None


def test_output_dir_equals_storage_root_rejects(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    storage = tmp_path / "storage"
    storage.mkdir()
    out = storage
    with pytest.raises(AuditError):
        assert_disjoint_output_storage(out, storage)


def test_output_dir_nested_in_storage_rejects(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    storage = tmp_path / "storage"
    storage.mkdir()
    out = storage / "reports"
    out.mkdir()
    with pytest.raises(AuditError):
        assert_disjoint_output_storage(out, storage)


def test_inventory_duplicates_unreferenced_deterministic(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    storage = tmp_path / "storage"
    storage.mkdir()
    payload = _jpeg_bytes((40, 50, 60))
    p1 = storage / "1"
    p2 = storage / "2"
    p1.mkdir()
    p2.mkdir()
    (p1 / "a.jpg").write_bytes(payload)
    (p2 / "b.jpg").write_bytes(payload)
    (storage / "orphan.jpg").write_bytes(_jpeg_bytes((9, 9, 9)))

    products = [
        ProductRow(
            product_id=1,
            sku="S1",
            slug="s1",
            name="P1",
            category_id=10,
            brand_id=100,
            is_active=True,
            is_available=True,
            deleted_at=None,
            brand_name="BrandA",
            category_name="Cat",
        ),
        ProductRow(
            product_id=2,
            sku="S2",
            slug="s2",
            name="P2",
            category_id=10,
            brand_id=200,
            is_active=True,
            is_available=True,
            deleted_at=None,
            brand_name="BrandB",
            category_name="Cat",
        ),
    ]
    images = [
        ImageRow(1, 1, "/static/uploads/products/1/a.jpg", True, 0),
        ImageRow(2, 2, "/static/uploads/products/2/b.jpg", True, 0),
        ImageRow(3, 1, "https://remote.example/x.jpg", False, 1),
        ImageRow(4, 1, "/static/uploads/products/1/missing.jpg", False, 2),
    ]

    async def fake_products(session, include_deleted=True):
        return products

    async def fake_images(session):
        return images

    monkeypatch.setattr("scripts.image_audit.inventory.fetch_products", fake_products)
    monkeypatch.setattr("scripts.image_audit.inventory.fetch_product_images", fake_images)

    out1 = tmp_path / "out1"
    out1.mkdir()
    out2 = tmp_path / "out2"
    out2.mkdir()

    db = ReadOnlyDbContext(
        session=AsyncMock(),
        dialect="sqlite",
        database_name="testdb",
        database_user="testuser",
        transaction_read_only="sqlite-test",
    )

    async def _run():
        s1 = await run_inventory(
            db=db,
            storage_root=storage,
            output_dir=out1,
            repository_root=repo,
        )
        s2 = await run_inventory(
            db=db,
            storage_root=storage,
            output_dir=out2,
            repository_root=repo,
        )
        return s1, s2

    s1, s2 = asyncio.run(_run())
    assert s1["network_requests_performed"] == 0
    assert s1["database_modified"] is False
    assert s1["storage_modified"] is False
    assert s1["storage_mutations"] == 0
    assert s1["exact_duplicate_sha_groups"] >= 1
    assert s1["cross_product_duplicate_sha_groups"] >= 1
    assert s1["cross_brand_duplicate_sha_groups"] >= 1
    assert s1["unreferenced_storage_files"] >= 1
    assert s1["external_remote_rows"] == 1
    assert s1["missing_local_file_rows"] == 1
    assert s1["database_read_only"] is False
    assert (out1 / "inventory.json").read_text() == (out2 / "inventory.json").read_text()
    assert (out1 / "checksums.sha256").exists()
    dup = (out1 / "duplicate-exact-sha.csv").read_text()
    assert "1/a.jpg" in dup and "2/b.jpg" in dup
    unref = (out1 / "unreferenced-storage-assets.csv").read_text()
    assert "orphan.jpg" in unref
    remote = (out1 / "remote-unverified.csv").read_text()
    assert "remote.example" in remote
    inv = (out1 / "inventory.json").read_text()
    assert "SECRET" not in inv


def test_no_storage_scan_skips_fs_and_marks_local_unverified(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    storage = tmp_path / "missing-storage"
    out = tmp_path / "out"
    out.mkdir()

    products = [
        ProductRow(
            product_id=1,
            sku="S1",
            slug="s1",
            name="P1",
            category_id=10,
            brand_id=100,
            is_active=True,
            is_available=True,
            deleted_at=None,
            brand_name="BrandA",
            category_name="Cat",
        ),
    ]
    images = [
        ImageRow(1, 1, "/static/uploads/products/1/a.jpg", True, 0),
        ImageRow(2, 1, "/static/uploads/products/1/missing.jpg", False, 1),
    ]

    async def fake_products(session, include_deleted=True):
        return products

    async def fake_images(session):
        return images

    monkeypatch.setattr("scripts.image_audit.inventory.fetch_products", fake_products)
    monkeypatch.setattr("scripts.image_audit.inventory.fetch_product_images", fake_images)

    db = ReadOnlyDbContext(
        session=AsyncMock(),
        dialect="sqlite",
        database_name="testdb",
        database_user="testuser",
        transaction_read_only="sqlite-test",
    )

    summary = asyncio.run(
        run_inventory(
            db=db,
            storage_root=storage,
            output_dir=out,
            storage_scan=False,
            repository_root=repo,
        )
    )
    assert summary["storage_scan_completed"] is False
    assert summary["storage_scan_skipped"] is True
    assert summary["missing_local_file_rows"] == 0
    assert summary["valid_local_image_rows"] == 0
    assert summary["local_unverified_rows"] == 2
    inv = (out / "inventory.json").read_text()
    assert "local_unverified" in inv
    assert "storage_scan_skipped" in inv


def test_status_order_symlink_before_missing(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    storage = tmp_path / "storage"
    storage.mkdir()
    out = tmp_path / "out"
    out.mkdir()

    products = [
        ProductRow(
            product_id=1,
            sku="S1",
            slug="s1",
            name="P1",
            category_id=10,
            brand_id=100,
            is_active=True,
            is_available=True,
            deleted_at=None,
            brand_name="BrandA",
            category_name="Cat",
        ),
    ]
    images = [ImageRow(1, 1, "/static/uploads/products/1/linked/x.jpg", True, 0)]

    async def fake_products(session, include_deleted=True):
        return products

    async def fake_images(session):
        return images

    monkeypatch.setattr("scripts.image_audit.inventory.fetch_products", fake_products)
    monkeypatch.setattr("scripts.image_audit.inventory.fetch_product_images", fake_images)

    index = {
        "1/linked": StorageEntry(
            relative_path="1/linked",
            status="symlink_rejected",
            reason_codes=["symlink_rejected"],
        )
    }

    def fake_scan(_root):
        return list(index.values())

    monkeypatch.setattr("scripts.image_audit.inventory.scan_storage_tree", fake_scan)

    db = ReadOnlyDbContext(
        session=AsyncMock(),
        dialect="sqlite",
        database_name="testdb",
        database_user="testuser",
        transaction_read_only="sqlite-test",
    )
    summary = asyncio.run(
        run_inventory(
            db=db,
            storage_root=storage,
            output_dir=out,
            repository_root=repo,
        )
    )
    assert summary["missing_local_file_rows"] == 0
    inv = (out / "inventory.json").read_text()
    assert "symlink_target" in inv


def test_excluded_deleted_product_not_false_orphan(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    storage = tmp_path / "storage"
    storage.mkdir()
    out = tmp_path / "out"
    out.mkdir()

    deleted_product = ProductRow(
        product_id=99,
        sku="DEL",
        slug="del",
        name="Deleted",
        category_id=10,
        brand_id=100,
        is_active=False,
        is_available=False,
        deleted_at="2020-01-01",
        brand_name="BrandA",
        category_name="Cat",
    )
    active_product = ProductRow(
        product_id=1,
        sku="S1",
        slug="s1",
        name="P1",
        category_id=10,
        brand_id=100,
        is_active=True,
        is_available=True,
        deleted_at=None,
        brand_name="BrandA",
        category_name="Cat",
    )
    images = [
        ImageRow(1, 1, "/static/uploads/products/1/a.jpg", True, 0),
        ImageRow(2, 99, "/static/uploads/products/99/a.jpg", True, 0),
    ]

    async def fake_products(session, include_deleted=True):
        if include_deleted:
            return [active_product, deleted_product]
        return [active_product]

    async def fake_images(session):
        return images

    monkeypatch.setattr("scripts.image_audit.inventory.fetch_products", fake_products)
    monkeypatch.setattr("scripts.image_audit.inventory.fetch_product_images", fake_images)

    db = ReadOnlyDbContext(
        session=AsyncMock(),
        dialect="sqlite",
        database_name="testdb",
        database_user="testuser",
        transaction_read_only="sqlite-test",
    )
    asyncio.run(
        run_inventory(
            db=db,
            storage_root=storage,
            output_dir=out,
            include_deleted_products=False,
            repository_root=repo,
        )
    )
    anom = (out / "database-anomalies.csv").read_text()
    assert "product_image_missing_product" not in anom
    assert "99" not in anom or "product_id" not in anom.split("99", 1)[0]


def test_duplicate_external_uses_scheme_host_port_path(tmp_path: Path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    storage = tmp_path / "storage"
    storage.mkdir()
    out = tmp_path / "out"
    out.mkdir()

    products = [
        ProductRow(
            product_id=1,
            sku="S1",
            slug="s1",
            name="P1",
            category_id=10,
            brand_id=100,
            is_active=True,
            is_available=True,
            deleted_at=None,
            brand_name="BrandA",
            category_name="Cat",
        ),
    ]
    images = [
        ImageRow(1, 1, "https://cdn.example:8443/a.jpg?x=1", True, 0),
        ImageRow(2, 1, "https://cdn.example:8443/a.jpg?y=2", False, 1),
    ]

    async def fake_products(session, include_deleted=True):
        return products

    async def fake_images(session):
        return images

    monkeypatch.setattr("scripts.image_audit.inventory.fetch_products", fake_products)
    monkeypatch.setattr("scripts.image_audit.inventory.fetch_product_images", fake_images)

    db = ReadOnlyDbContext(
        session=AsyncMock(),
        dialect="sqlite",
        database_name="testdb",
        database_user="testuser",
        transaction_read_only="sqlite-test",
    )
    asyncio.run(
        run_inventory(
            db=db,
            storage_root=storage,
            output_dir=out,
            storage_scan=False,
            repository_root=repo,
        )
    )
    anom = (out / "database-anomalies.csv").read_text()
    assert "duplicate_product_normalized_url" in anom


def test_atomic_output_and_checksum(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    write_json(out / "summary.json", {"a": 1, "b": 2})
    atomic_write_text(out / "inventory.csv", "image_id\n1\n")
    write_checksums(out, ["summary.json", "inventory.csv"])
    lines = (out / "checksums.sha256").read_text().strip().splitlines()
    assert len(lines) == 2
    assert all(len(line.split()[0]) == 64 for line in lines)


def test_atomic_publish_failure_leaves_output_empty(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.txt").write_text("keep-me")

    def bad_writer(staging: Path) -> None:
        write_json(staging / "summary.json", {"ok": True})
        raise RuntimeError("simulated failure")

    with pytest.raises(RuntimeError):
        publish_inventory_outputs(
            out,
            writers=[bad_writer],
            checksum_names=["summary.json"],
        )
    assert list(out.iterdir()) == []


def test_output_dir_inside_repository_rejects(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    inside = repo / "out"
    inside.mkdir()
    with pytest.raises(AuditError):
        prepare_output_dir(inside, repository_root=repo)


def test_non_empty_output_directory_rejects(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale.txt").write_text("x")
    with pytest.raises(AuditError):
        prepare_output_dir(out, repository_root=repo)


def test_prepare_empty_output_outside_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    prepare_output_dir(out, repository_root=repo)
