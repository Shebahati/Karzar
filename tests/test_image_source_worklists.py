"""Focused tests for IMG-02B source worklists (synthetic fixtures only)."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

import pytest
from scripts.image_source_worklists.builder import (
    build_worklists,
    validate_image_presence,
)
from scripts.image_source_worklists.contracts import (
    AUTHORITATIVE_CHECKSUMS_DIGEST,
    WorklistError,
    normalize_brand,
    stable_work_item_id,
)
from scripts.image_source_worklists.inputs import (
    extract_review_zip,
    load_inventory,
    load_review_bundles,
)
from scripts.image_source_worklists.output import (
    copy_final_outputs,
    semantic_fingerprint,
    write_worklist_outputs,
)

REPO = Path(__file__).resolve().parents[1]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_checksums(directory: Path, names: list[str]) -> str:
    lines = []
    for name in names:
        digest = _sha((directory / name).read_bytes())
        lines.append(f"{digest}  {name}")
    text = "\n".join(lines) + "\n"
    (directory / "checksums.sha256").write_text(text, encoding="utf-8")
    return _sha(text.encode("utf-8"))


def _write_mini_inventory(directory: Path) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    # Minimal coverage rows — facts will be patched via summary to expected values
    # for unit tests we bypass full expected facts by using a custom loader path
    rows = [
        {
            "product_id": "1",
            "sku": "D-1",
            "name": "Dasqua missing active avail",
            "brand": "Dasqua | داسکوا",
            "category": "cat",
            "deleted": "false",
            "is_active": "true",
            "is_available": "true",
            "total_image_rows": "0",
            "has_any_image_row": "false",
        },
        {
            "product_id": "2",
            "sku": "D-2",
            "name": "Dasqua missing active unavail",
            "brand": "Dasqua | داسکوا",
            "category": "cat",
            "deleted": "false",
            "is_active": "true",
            "is_available": "false",
            "total_image_rows": "0",
            "has_any_image_row": "false",
        },
        {
            "product_id": "3",
            "sku": "D-3",
            "name": "Dasqua missing inactive",
            "brand": "Dasqua | داسکوا",
            "category": "cat",
            "deleted": "false",
            "is_active": "false",
            "is_available": "false",
            "total_image_rows": "0",
            "has_any_image_row": "false",
        },
        {
            "product_id": "4",
            "sku": "I-1",
            "name": "INSIZE with image",
            "brand": "INSIZE | اینسایز",
            "category": "cat",
            "deleted": "false",
            "is_active": "true",
            "is_available": "true",
            "total_image_rows": "1",
            "has_any_image_row": "true",
        },
        {
            "product_id": "5",
            "sku": "S-1",
            "name": "SAN OU with image",
            "brand": "SAN OU | سانو",
            "category": "cat",
            "deleted": "false",
            "is_active": "true",
            "is_available": "true",
            "total_image_rows": "1",
            "has_any_image_row": "true",
        },
        {
            "product_id": "6",
            "sku": "X-1",
            "name": "Other brand missing",
            "brand": "Mitutoyo | میتوتویو",
            "category": "cat",
            "deleted": "false",
            "is_active": "true",
            "is_available": "true",
            "total_image_rows": "0",
            "has_any_image_row": "false",
        },
        {
            "product_id": "7",
            "sku": "D-W",
            "name": "Dasqua watermark target",
            "brand": "Dasqua | داسکوا",
            "category": "cat",
            "deleted": "false",
            "is_active": "true",
            "is_available": "true",
            "total_image_rows": "2",
            "has_any_image_row": "true",
        },
    ]
    fields = list(rows[0].keys())
    with (directory / "product-coverage.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    summary = {
        "non_deleted_products": 5917,
        "products_with_image_rows": 1194,
        "products_without_image_rows": 4724,
        "valid_local_image_rows": 1193,
        "unique_local_asset_sha256s": 614,
    }
    (directory / "summary.json").write_text(json.dumps(summary) + "\n", encoding="utf-8")
    # placeholder required members for checksum file only
    for name in ("inventory.csv", "run-metadata.json"):
        (directory / name).write_text(name + "\n", encoding="utf-8")
    digest = _write_checksums(
        directory,
        [
            "product-coverage.csv",
            "summary.json",
            "inventory.csv",
            "run-metadata.json",
        ],
    )
    return digest


def _mini_inventory_obj(directory: Path) -> dict:
    """Build inventory object without enforcing authoritative global counts."""
    products = list(
        csv.DictReader((directory / "product-coverage.csv").open(encoding="utf-8-sig"))
    )
    non_deleted = [p for p in products if p["deleted"] == "false"]
    by_id = {p["product_id"]: p for p in non_deleted}
    brand_sku = {}
    for p in non_deleted:
        key = normalize_brand(p.get("brand"))
        if key is None:
            continue
        brand_sku[(key, p["sku"].strip())] = p["product_id"]
    return {
        "source_dir": str(directory),
        "checksums_digest": "synthetic",
        "products": non_deleted,
        "products_by_id": by_id,
        "brand_sku_index": brand_sku,
        "facts": {},
        "summary": {},
    }


def _bundle(
    *,
    batch_id: str,
    assets: int,
    assignments: list[dict],
    replace_rows: list[dict],
    watermark_rows: list[dict],
    manual_rows: list[dict],
) -> dict:
    asset_rows = [
        {
            "review_schema_version": "1",
            "batch_id": batch_id,
            "asset_id": f"asset{i}",
            "watermark_status": "none_visible",
            "quality_status": "good",
            "background_status": "clean_white",
            "crop_status": "good",
            "asset_decision": "KEEP",
            "rights_status": "review_required",
            "asset_notes": "",
        }
        for i in range(assets)
    ]
    return {
        "spec": {
            "batch_id": batch_id,
            "assets": assets,
            "assignments": len(assignments),
            "replace_required": len(replace_rows),
            "manual_review": len(manual_rows),
        },
        "assets": asset_rows,
        "assignments": assignments,
        "replace_rows": replace_rows,
        "watermark_rows": watermark_rows,
        "manual_rows": manual_rows,
        "aggregates": {
            "assets": assets,
            "assignments": len(assignments),
            "replace_required": len(replace_rows),
            "manual_review": len(manual_rows),
            "watermark_queue_rows": len(watermark_rows),
        },
    }


def test_brand_normalization_and_rejection():
    assert normalize_brand("Dasqua | داسکوا") == "dasqua"
    assert normalize_brand("INSIZE | اینسایز") == "insize"
    assert normalize_brand("SAN OU | سانو") == "san_ou"
    assert normalize_brand("Mitutoyo | میتوتویو") is None
    assert normalize_brand("insize") == "insize"
    with pytest.raises(WorklistError, match="ambiguous"):
        normalize_brand("Dasqua | INSIZE")


def test_missing_image_priorities_and_inactive_included(tmp_path: Path):
    inv_dir = tmp_path / "inv"
    _write_mini_inventory(inv_dir)
    inventory = _mini_inventory_obj(inv_dir)
    review = {"bundles": [], "evidence": [], "cumulative": {}}
    built = build_worklists(inventory, review)
    missing = [w for w in built["work_items"] if w["work_type"] == "missing_image"]
    by_sku = {w["sku"]: w for w in missing}
    assert by_sku["D-1"]["priority"] == "P0"
    assert by_sku["D-2"]["priority"] == "P1"
    assert by_sku["D-3"]["priority"] == "P2"
    assert "X-1" not in by_sku
    assert "I-1" not in by_sku


def test_replace_watermark_manual_precedence_and_reasons(tmp_path: Path):
    inv_dir = tmp_path / "inv"
    _write_mini_inventory(inv_dir)
    inventory = _mini_inventory_obj(inv_dir)
    # product 4 INSIZE: replace + watermark on same product via brand+sku
    # product 7 Dasqua watermark
    # product 1 Dasqua missing + manual
    assignments = [
        {
            "assignment_id": "a1",
            "asset_id": "aa",
            "image_id": "10",
            "product_id": "1",
            "sku": "D-1",
            "suitability_status": "insufficient_context",
            "assignment_decision": "MANUAL_REVIEW",
            "assignment_notes": "hold",
        }
    ]
    replace_rows = [
        {
            "assignment_id": "r1",
            "asset_id": "ra",
            "image_id": "11",
            "product_id": "4",
            "sku": "I-1",
            "product_name": "INSIZE with image",
            "brand_name": "INSIZE | اینسایز",
            "category_name": "cat",
            "suitability_status": "likely_mismatch",
            "assignment_decision": "REPLACE_REQUIRED",
            "assignment_notes": "wrong",
        }
    ]
    watermark_rows = [
        {
            "asset_id": "wa",
            "brand_name": "INSIZE | اینسایز",
            "sku": "I-1",
            "product_name": "INSIZE with image",
            "asset_decision": "PREFER_REPLACEMENT",
            "rights_status": "review_required",
            "asset_notes": "wm",
        },
        {
            "asset_id": "wb",
            "brands": "Dasqua | داسکوا",
            "skus": "D-W",
            "asset_decision": "PREFER_REPLACEMENT",
            "rights_status": "review_required",
            "asset_notes": "wm2",
        },
    ]
    review = {
        "bundles": [
            _bundle(
                batch_id="IMG-02A-02-PILOT-001",
                assets=1,
                assignments=assignments,
                replace_rows=replace_rows,
                watermark_rows=watermark_rows,
                manual_rows=assignments,
            )
        ],
        "evidence": [],
        "cumulative": {},
    }
    built = build_worklists(inventory, review)
    by_id = {w["product_id"]: w for w in built["work_items"]}
    assert by_id["1"]["work_type"] == "manual_review_hold"
    assert by_id["1"]["eligible_for_automatic_discovery"] == "false"
    assert by_id["1"]["status"] == "manual_hold"
    assert "missing_image" in by_id["1"]["work_reasons"]
    assert by_id["4"]["work_type"] == "replace_required"
    assert by_id["4"]["has_third_party_watermark"] == "true"
    assert "watermark_cleaner" in by_id["4"]["work_reasons"]
    assert by_id["7"]["work_type"] == "watermark_cleaner"
    assert by_id["7"]["priority"] == "P1"


def test_product_id_sku_consistency_failure(tmp_path: Path):
    inv_dir = tmp_path / "inv"
    _write_mini_inventory(inv_dir)
    inventory = _mini_inventory_obj(inv_dir)
    replace_rows = [
        {
            "assignment_id": "r1",
            "asset_id": "ra",
            "image_id": "11",
            "product_id": "4",
            "sku": "WRONG",
            "brand_name": "INSIZE | اینسایز",
            "suitability_status": "likely_mismatch",
            "assignment_decision": "REPLACE_REQUIRED",
            "assignment_notes": "",
        }
    ]
    review = {
        "bundles": [
            _bundle(
                batch_id="B",
                assets=1,
                assignments=[],
                replace_rows=replace_rows,
                watermark_rows=[],
                manual_rows=[],
            )
        ],
        "evidence": [],
        "cumulative": {},
    }
    with pytest.raises(WorklistError, match="SKU drift"):
        build_worklists(inventory, review)


def test_deterministic_ids_and_ordering(tmp_path: Path):
    inv_dir = tmp_path / "inv"
    _write_mini_inventory(inv_dir)
    inventory = _mini_inventory_obj(inv_dir)
    review = {"bundles": [], "evidence": [], "cumulative": {}}
    a = build_worklists(inventory, review)
    b = build_worklists(inventory, review)
    assert [w["work_item_id"] for w in a["work_items"]] == [
        w["work_item_id"] for w in b["work_items"]
    ]
    assert all(len(w["work_item_id"]) == 64 for w in a["work_items"])
    # stable hash helper does not use PYTHONHASHSEED / hash()
    assert stable_work_item_id(["a", "b"]) == stable_work_item_id(["a", "b"])


def test_output_outside_repo_and_nonempty_refusal(tmp_path: Path):
    inv_dir = tmp_path / "inv"
    _write_mini_inventory(inv_dir)
    inventory = _mini_inventory_obj(inv_dir)
    review = {
        "bundles": [],
        "evidence": [],
        "cumulative": {
            "assets_reviewed": 0,
            "assignments_reviewed": 0,
            "replace_required_assignments": 0,
            "manual_review_assignments": 0,
        },
    }
    built = build_worklists(inventory, review)
    review["evidence"] = []
    out = tmp_path / "out"
    write_worklist_outputs(
        out,
        repo_root=REPO,
        inventory=inventory,
        review_data={
            **review,
            "evidence": [
                {
                    "batch_id": "X",
                    "zip_name": "x.zip",
                    "zip_path": "/tmp/x.zip",
                    "outer_sha256": "0" * 64,
                    "extract_dir": "/tmp/x",
                    "aggregates": {},
                }
            ],
        },
        built=built,
    )
    assert (out / "worklist-all.csv").is_file()
    assert not list(out.glob("*.png"))
    # nonempty refusal
    with pytest.raises(WorklistError, match="not empty"):
        write_worklist_outputs(
            out,
            repo_root=REPO,
            inventory=inventory,
            review_data={
                **review,
                "evidence": [
                    {
                        "batch_id": "X",
                        "zip_name": "x.zip",
                        "zip_path": "/tmp/x.zip",
                        "outer_sha256": "0" * 64,
                        "extract_dir": "/tmp/x",
                        "aggregates": {},
                    }
                ],
            },
            built=built,
        )
    # inside repo forbidden
    with pytest.raises(WorklistError, match="outside repository"):
        write_worklist_outputs(
            REPO / "tmp-out-should-fail",
            repo_root=REPO,
            inventory=inventory,
            review_data={
                **review,
                "evidence": [
                    {
                        "batch_id": "X",
                        "zip_name": "x.zip",
                        "zip_path": "/tmp/x.zip",
                        "outer_sha256": "0" * 64,
                        "extract_dir": "/tmp/x",
                        "aggregates": {},
                    }
                ],
            },
            built=built,
        )


def test_rights_always_review_required(tmp_path: Path):
    inv_dir = tmp_path / "inv"
    _write_mini_inventory(inv_dir)
    inventory = _mini_inventory_obj(inv_dir)
    review = {"bundles": [], "evidence": [], "cumulative": {}}
    built = build_worklists(inventory, review)
    assert all(w["rights_status"] == "review_required" for w in built["work_items"])


def test_second_run_semantic_stability(tmp_path: Path):
    inv_dir = tmp_path / "inv"
    _write_mini_inventory(inv_dir)
    inventory = _mini_inventory_obj(inv_dir)
    review_data = {
        "bundles": [],
        "evidence": [
            {
                "batch_id": "X",
                "zip_name": "x.zip",
                "zip_path": "/tmp/x.zip",
                "outer_sha256": "0" * 64,
                "extract_dir": "/tmp/x",
                "aggregates": {},
            }
        ],
        "cumulative": {
            "assets_reviewed": 0,
            "assignments_reviewed": 0,
            "replace_required_assignments": 0,
            "manual_review_assignments": 0,
        },
    }
    built = build_worklists(inventory, review_data)
    out1 = tmp_path / "o1"
    out2 = tmp_path / "o2"
    write_worklist_outputs(
        out1, repo_root=REPO, inventory=inventory, review_data=review_data, built=built
    )
    write_worklist_outputs(
        out2, repo_root=REPO, inventory=inventory, review_data=review_data, built=built
    )
    assert semantic_fingerprint(out1) == semantic_fingerprint(out2)


def test_extract_rejects_symlink_member(tmp_path: Path):
    zpath = tmp_path / "bad.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        # Regular file only — symlink bit test via external_attr
        info = zipfile.ZipInfo("evil.txt")
        info.external_attr = (0o120777 << 16)
        zf.writestr(info, b"x")
    with pytest.raises(WorklistError, match="symlink"):
        extract_review_zip(zpath, tmp_path / "dest")


def test_review_bundle_batch_and_checksum_external_if_present():
    import uuid

    root = Path("/home/moahmmad/Projects/Karzar-image-review")
    extract = Path("/var/tmp/karzar-image-source-paths") / f"extract-hr-test-{uuid.uuid4().hex}"
    inv = Path("/var/tmp/karzar-image-audit/img02a01-20260803T121056Z")
    if not (root / "IMG-02A-02-pilot-001-human-review.zip").is_file():
        pytest.skip("external review bundles not present")
    if not inv.is_dir():
        pytest.skip("external inventory not present")
    inventory = load_inventory(inv, expected_checksums_digest=AUTHORITATIVE_CHECKSUMS_DIGEST)
    assert inventory["facts"]["unique_local_assets"] == 614
    review = load_review_bundles(root, extract_root=extract)
    assert review["cumulative"]["replace_required_assignments"] == 88
    assert review["cumulative"]["manual_review_assignments"] == 2
    # foreign checksum failure
    bad = extract / "pilot_001" / "checksums.sha256"
    bad.write_text("0" * 64 + "  asset-review.csv\n", encoding="utf-8")
    from scripts.image_source_worklists.contracts import BUNDLE_SPECS
    from scripts.image_source_worklists.inputs import _validate_bundle_dir

    with pytest.raises(WorklistError, match="checksum mismatch"):
        _validate_bundle_dir(extract / "pilot_001", BUNDLE_SPECS[0])


def _evidence_stub() -> dict:
    return {
        "batch_id": "X",
        "zip_name": "x.zip",
        "zip_path": "/tmp/x.zip",
        "outer_sha256": "0" * 64,
        "extract_dir": "/tmp/x",
        "aggregates": {},
    }


def _empty_review() -> dict:
    return {
        "bundles": [],
        "evidence": [_evidence_stub()],
        "cumulative": {
            "assets_reviewed": 0,
            "assignments_reviewed": 0,
            "replace_required_assignments": 0,
            "manual_review_assignments": 0,
        },
    }


def test_inventory_presence_accepted_cases():
    assert validate_image_presence(
        {"product_id": "1", "sku": "A", "total_image_rows": "0", "has_any_image_row": "false"}
    ) == (0, False)
    assert validate_image_presence(
        {"product_id": "2", "sku": "B", "total_image_rows": "1", "has_any_image_row": "true"}
    ) == (1, True)
    assert validate_image_presence(
        {"product_id": "3", "sku": "C", "total_image_rows": "2", "has_any_image_row": "true"}
    ) == (2, True)


@pytest.mark.parametrize(
    "total,has_any,match",
    [
        ("1", "false", "contradictory"),
        ("0", "true", "contradictory"),
        ("-1", "false", "negative"),
        ("abc", "false", "invalid non-negative"),
        ("1", "yes", "invalid boolean"),
        ("1", "1", "invalid boolean"),
        ("", "false", "invalid non-negative"),
    ],
)
def test_inventory_presence_rejected_cases(total: str, has_any: str, match: str):
    with pytest.raises(WorklistError, match=match):
        validate_image_presence(
            {
                "product_id": "9",
                "sku": "BAD",
                "total_image_rows": total,
                "has_any_image_row": has_any,
            }
        )


def test_contradictory_presence_not_classified_missing(tmp_path: Path):
    inv_dir = tmp_path / "inv"
    _write_mini_inventory(inv_dir)
    inventory = _mini_inventory_obj(inv_dir)
    # Force contradiction on product 1
    inventory["products"][0]["total_image_rows"] = "1"
    inventory["products"][0]["has_any_image_row"] = "false"
    with pytest.raises(WorklistError, match="contradictory"):
        build_worklists(inventory, {"bundles": [], "evidence": [], "cumulative": {}})


def test_nonempty_output_refusals(tmp_path: Path):
    inv_dir = tmp_path / "inv"
    _write_mini_inventory(inv_dir)
    inventory = _mini_inventory_obj(inv_dir)
    review = _empty_review()
    built = build_worklists(inventory, review)

    def refuse(path: Path) -> None:
        with pytest.raises(WorklistError, match="not empty"):
            write_worklist_outputs(
                path, repo_root=REPO, inventory=inventory, review_data=review, built=built
            )

    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (unrelated / "noise.txt").write_text("x", encoding="utf-8")
    before = (unrelated / "noise.txt").read_bytes()
    refuse(unrelated)
    assert (unrelated / "noise.txt").read_bytes() == before

    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / "worklist-all.csv").write_text("incomplete\n", encoding="utf-8")
    before_partial = list(partial.iterdir())
    refuse(partial)
    assert list(partial.iterdir()) == before_partial

    complete = tmp_path / "complete"
    write_worklist_outputs(
        complete, repo_root=REPO, inventory=inventory, review_data=review, built=built
    )
    before_complete = sorted(p.name for p in complete.iterdir())
    refuse(complete)
    assert sorted(p.name for p in complete.iterdir()) == before_complete

    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "subdir").mkdir()
    refuse(nested)

    with_symlink = tmp_path / "with_symlink"
    with_symlink.mkdir()
    target = tmp_path / "symlink-target.txt"
    target.write_text("t", encoding="utf-8")
    (with_symlink / "link").symlink_to(target)
    refuse(with_symlink)


def test_copy_final_non_destructive(tmp_path: Path):
    inv_dir = tmp_path / "inv"
    _write_mini_inventory(inv_dir)
    inventory = _mini_inventory_obj(inv_dir)
    review = _empty_review()
    built = build_worklists(inventory, review)
    source = tmp_path / "source-out"
    write_worklist_outputs(
        source, repo_root=REPO, inventory=inventory, review_data=review, built=built
    )

    absent = tmp_path / "final-absent"
    copy_final_outputs(source, absent, repo_root=REPO)
    assert (absent / "worklist-all.csv").is_file()

    empty_existing = tmp_path / "final-empty"
    empty_existing.mkdir()
    with pytest.raises(WorklistError, match="already exists"):
        copy_final_outputs(source, empty_existing, repo_root=REPO)

    nonempty_existing = tmp_path / "final-nonempty"
    nonempty_existing.mkdir()
    marker = nonempty_existing / "keep-me.txt"
    marker.write_text("keep", encoding="utf-8")
    with pytest.raises(WorklistError, match="already exists"):
        copy_final_outputs(source, nonempty_existing, repo_root=REPO)
    assert marker.read_text(encoding="utf-8") == "keep"

    link_dest = tmp_path / "final-link"
    link_dest.symlink_to(tmp_path / "somewhere-missing")
    with pytest.raises(WorklistError, match="symlink"):
        copy_final_outputs(source, link_dest, repo_root=REPO)

    with pytest.raises(WorklistError, match="outside repository"):
        copy_final_outputs(source, REPO / "should-not-copy-here", repo_root=REPO)


def _write_zip(path: Path, members: dict[str, bytes], *, symlink_name: str | None = None) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
        if symlink_name is not None:
            info = zipfile.ZipInfo(symlink_name)
            info.external_attr = (0o120777 << 16)
            zf.writestr(info, b"target")


def test_extract_flat_valid_bundle(tmp_path: Path):
    zpath = tmp_path / "flat.zip"
    _write_zip(zpath, {"a.csv": b"a", "b.csv": b"b"})
    dest = tmp_path / "dest-flat"
    extract_review_zip(zpath, dest)
    assert (dest / "a.csv").read_bytes() == b"a"
    assert (dest / "b.csv").read_bytes() == b"b"


def test_extract_single_root_valid_bundle(tmp_path: Path):
    zpath = tmp_path / "rooted.zip"
    _write_zip(zpath, {"bundle/a.csv": b"a", "bundle/b.csv": b"b"})
    dest = tmp_path / "dest-root"
    extract_review_zip(zpath, dest)
    assert (dest / "a.csv").read_bytes() == b"a"
    assert (dest / "b.csv").read_bytes() == b"b"
    assert not (dest / "bundle").exists()


def test_extract_rejects_duplicate_full_member(tmp_path: Path):
    zpath = tmp_path / "dup.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("a.csv", b"one")
        zf.writestr("a.csv", b"two")
    # ZipFile may collapse duplicates on write; force via ZipInfo if needed
    names = zipfile.ZipFile(zpath).namelist()
    if len(names) == len(set(names)):
        # Reconstruct with duplicate ZipInfo entries if possible
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.writestr(zipfile.ZipInfo("a.csv"), b"one")
            zf.writestr(zipfile.ZipInfo("a.csv"), b"two")
        names = zipfile.ZipFile(zpath).namelist()
    if len(names) == len(set(names)):
        pytest.skip("zipfile collapsed duplicate members")
    with pytest.raises(WorklistError, match="duplicate ZIP members"):
        extract_review_zip(zpath, tmp_path / "dest-dup")


def test_extract_rejects_same_basename_different_dirs(tmp_path: Path):
    zpath = tmp_path / "basename.zip"
    _write_zip(zpath, {"dir1/file.csv": b"1", "dir2/file.csv": b"2"})
    with pytest.raises(WorklistError, match="multiple top-level"):
        extract_review_zip(zpath, tmp_path / "dest-basename")


def test_extract_rejects_multiple_top_level_roots(tmp_path: Path):
    zpath = tmp_path / "multi.zip"
    _write_zip(zpath, {"a/x.csv": b"1", "b/y.csv": b"2"})
    with pytest.raises(WorklistError, match="multiple top-level"):
        extract_review_zip(zpath, tmp_path / "dest-multi")


def test_extract_rejects_nested_residual(tmp_path: Path):
    zpath = tmp_path / "nested.zip"
    _write_zip(zpath, {"root/sub/file.csv": b"1"})
    with pytest.raises(WorklistError, match="nested residual"):
        extract_review_zip(zpath, tmp_path / "dest-nested")


def test_extract_rejects_absolute_and_traversal(tmp_path: Path):
    abs_zip = tmp_path / "abs.zip"
    with zipfile.ZipFile(abs_zip, "w") as zf:
        zf.writestr("/abs.csv", b"x")
    with pytest.raises(WorklistError, match="absolute"):
        extract_review_zip(abs_zip, tmp_path / "dest-abs")

    trav = tmp_path / "trav.zip"
    _write_zip(trav, {"../evil.csv": b"x"})
    with pytest.raises(WorklistError, match="traversal"):
        extract_review_zip(trav, tmp_path / "dest-trav")


def test_extract_rejects_nonempty_and_symlink_destination(tmp_path: Path):
    zpath = tmp_path / "ok.zip"
    _write_zip(zpath, {"a.csv": b"a"})
    nonempty = tmp_path / "nonempty-dest"
    nonempty.mkdir()
    (nonempty / "existing.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(WorklistError, match="not empty"):
        extract_review_zip(zpath, nonempty)
    assert (nonempty / "existing.txt").read_text(encoding="utf-8") == "keep"

    link = tmp_path / "link-dest"
    link.symlink_to(tmp_path / "missing-target")
    with pytest.raises(WorklistError, match="symlink"):
        extract_review_zip(zpath, link)


def test_extract_rejects_basename_collision_under_single_root(tmp_path: Path):
    # After stripping root, two nested paths would map to same basename if flattened
    # by basename alone — fail closed on nested residual instead.
    zpath = tmp_path / "coll.zip"
    _write_zip(zpath, {"root/a/file.csv": b"1", "root/b/file.csv": b"2"})
    with pytest.raises(WorklistError, match="nested residual"):
        extract_review_zip(zpath, tmp_path / "dest-coll")
