"""Read-only consolidation of batch discovery outputs."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .atomic import atomic_write_text, refuse_overwrite_if_corrupt_json
from .contracts import (
    PROVENANCE_OCCURRENCE_FIELDS,
    DiscoveryError,
    candidate_content_fingerprint,
    fill_provenance,
    normalize_sha256,
    validate_source_manifest_row,
)
from .output import (
    _csv_text,
    file_sha256,
    rename_and_classify,
    semantic_manifest_sha256,
    write_outputs,
    write_summary_and_state,
)
from .paths import (
    assert_batch_roots_nofollow,
    assert_run_output_roots_nofollow,
    assert_under_assets,
    inspect_local_asset_nofollow,
    inventory_assets_by_sha,
    iter_local_asset_files,
    resolve_manifest_asset_path,
)

# Coherent prior-output contract (all required for --allow-replace recognition).
_ALLOWED_TOP_LEVEL = frozenset({"assets", "manifests", "summary.json", "review", "logs"})
_ALLOWED_MANIFEST_FILES = frozenset(
    {
        "manifest.json",
        "manifest.csv",
        "rejected.csv",
        "run-state.json",
        "source-groups.csv",
        "cross-brand-duplicates.csv",
        "candidate-conflicts.csv",
        "candidate-conflicts.json",
        "candidate-provenance.csv",
        "candidate-provenance.json",
        "high-reuse-assets.csv",
        "preexisting-stale-files.csv",
        "duplicate-physical-assets.csv",
    }
)
_ALLOWED_REVIEW_FILES = frozenset({"contact-sheet.html"})
_PIPELINE_SUMMARY_MARKERS = (
    "IMG-01",
    "image-discovery",
    "image_discovery",
    "CONSOLIDATE",
    "pilot_id",
)

_CONTRACT_INTEGRITY_CODES = frozenset(
    {
        "missing_manifest_sha256",
        "invalid_manifest_sha256",
        "missing_candidate_id",
        "invalid_candidate_id",
        "candidate_id_mismatch",
        "missing_product_key",
        "missing_source_candidate_key",
        "missing_source_adapter",
        "invalid_image_role",
        "missing_required_manifest_field",
        "manifest_sha_mismatch",
        "destination_sha_mismatch",
        "missing_source_asset",
        "asset_path_escape",
        "asset_path_absolute",
        "asset_path_not_file",
        "asset_symlink_escape",
        "unexpected_asset_symlink",
        "unexpected_non_regular_asset",
    }
)


def _validate_consolidate_paths(*, input_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    inp = input_dir.resolve()
    out = output_dir.resolve()
    if inp == out:
        raise SystemExit("ERROR: consolidate --output-dir must differ from --input-dir")
    try:
        out.relative_to(inp)
        raise SystemExit("ERROR: --output-dir must not be nested under --input-dir")
    except ValueError:
        pass
    try:
        inp.relative_to(out)
        raise SystemExit("ERROR: --input-dir must not be nested under --output-dir")
    except ValueError:
        pass
    if out.parent.resolve() == inp and out.name and (inp / out.name).exists():
        raise SystemExit("ERROR: output would be rediscovered as an input batch")
    return inp, out


def _summary_identifies_pipeline(summary: dict[str, Any]) -> bool:
    blob = json.dumps(summary, ensure_ascii=False).lower()
    if any(m.lower() in blob for m in _PIPELINE_SUMMARY_MARKERS):
        return True
    pilot = str(summary.get("pilot_id") or "")
    return bool(pilot)


def recognize_prior_discovery_output(out: Path) -> tuple[bool, str, list[dict[str, str]]]:
    """Return (ok, reason, stale_rows).

    A coherent prior output requires manifests/manifest.json + summary.json + assets/,
    valid JSON shapes, pipeline identity, safe referenced assets, and no unknown files.
    Symlinked governed roots are never followed.
    """
    if not out.exists(follow_symlinks=False) and not out.is_symlink():
        return False, "output_missing", []

    try:
        assert_run_output_roots_nofollow(out, require_existing_root=True)
    except DiscoveryError as e:
        return False, e.reason_code, []

    children = list(out.iterdir())
    if not children:
        return False, "empty", []

    names = {p.name for p in children}
    unknown_top = sorted(names - _ALLOWED_TOP_LEVEL)
    if unknown_top:
        return False, f"unknown_top_level:{','.join(unknown_top)}", []

    man_path = out / "manifests" / "manifest.json"
    sum_path = out / "summary.json"
    assets = out / "assets"
    if not man_path.is_file() or not sum_path.is_file() or not assets.is_dir():
        return False, "incomplete_signature", []
    if man_path.is_symlink() or sum_path.is_symlink() or assets.is_symlink():
        return False, "unexpected_governed_symlink", []

    try:
        manifest = json.loads(man_path.read_text(encoding="utf-8"))
    except Exception:
        return False, "malformed_manifest", []
    if not isinstance(manifest, list):
        return False, "manifest_not_list", []

    try:
        summary = json.loads(sum_path.read_text(encoding="utf-8"))
    except Exception:
        return False, "malformed_summary", []
    if not isinstance(summary, dict):
        return False, "summary_not_object", []
    if not _summary_identifies_pipeline(summary):
        return False, "summary_not_pipeline", []

    # Unknown files under manifests/
    if (out / "manifests").is_dir():
        for p in (out / "manifests").iterdir():
            if p.is_dir():
                return False, f"unknown_nested_dir:manifests/{p.name}", []
            if p.name not in _ALLOWED_MANIFEST_FILES:
                return False, f"unknown_nested_file:manifests/{p.name}", []

    if (out / "review").exists():
        if not (out / "review").is_dir():
            return False, "review_not_dir", []
        for p in (out / "review").iterdir():
            if p.name not in _ALLOWED_REVIEW_FILES:
                return False, f"unknown_nested_file:review/{p.name}", []

    if (out / "logs").exists():
        if not (out / "logs").is_dir():
            return False, "logs_not_dir", []
        for p in (out / "logs").iterdir():
            if p.is_dir() or not p.name.endswith(".log"):
                return False, f"unknown_nested_file:logs/{p.name}", []

    # Validate every referenced asset; inventory all physical files (no-follow)
    try:
        on_disk = iter_local_asset_files(assets, fail_closed=True)
    except DiscoveryError as e:
        return False, e.reason_code, []

    on_disk_names = {p.name for p in on_disk}
    referenced_names: set[str] = set()
    for row in manifest:
        if not isinstance(row, dict):
            return False, "manifest_row_not_object", []
        rel = str(row.get("local_asset_path") or "")
        sha = normalize_sha256(str(row.get("sha256") or ""))
        try:
            path = resolve_manifest_asset_path(
                assets_root=assets, local_asset_path=rel, require_exists=True
            )
        except DiscoveryError as e:
            return False, e.reason_code, []
        disk_sha = file_sha256(path)
        if not sha or disk_sha != sha:
            return False, "prior_manifest_sha_mismatch", []
        referenced_names.add(path.name)

    stale_rows: list[dict[str, str]] = []
    for p in on_disk:
        if p.name in referenced_names:
            continue
        digest = file_sha256(p)
        stale_rows.append(
            {
                "relative_path": f"assets/{p.name}",
                "sha256": digest,
                "review_status": "pending_human_review",
                "notes": "stale_governed_asset_not_in_manifest",
            }
        )

    unknown_unreferenced = on_disk_names - referenced_names
    if stale_rows or unknown_unreferenced:
        return True, "recognized_with_stale_assets", stale_rows

    return True, "recognized_clean", []


def _reject_nonempty_without_replace(out: Path, *, allow_replace: bool) -> list[dict[str, str]]:
    """Fail closed: any non-empty output without coherent --allow-replace is rejected."""
    if not out.exists(follow_symlinks=False) and not out.is_symlink():
        return []
    try:
        assert_run_output_roots_nofollow(out)
    except DiscoveryError as e:
        raise SystemExit(
            f"ERROR: consolidate --output-dir rejected ({e.reason_code}: {e.reason_detail})"
        ) from e
    if out.is_symlink():
        raise SystemExit("ERROR: consolidate --output-dir must not be a symlink")
    children = list(out.iterdir()) if out.is_dir() else []
    if not children:
        return []
    top_names = sorted(p.name for p in children)
    if not allow_replace:
        raise SystemExit(
            "ERROR: consolidate --output-dir is non-empty; pass --allow-replace only for a "
            f"coherent governed prior output (found: {', '.join(top_names[:12])}"
            f"{'…' if len(top_names) > 12 else ''})"
        )

    ok, reason, stale = recognize_prior_discovery_output(out)
    if not ok:
        raise SystemExit(
            "ERROR: --allow-replace refused — output is not a coherent governed image-discovery "
            f"directory ({reason})"
        )
    if reason == "recognized_with_stale_assets":
        man = out / "manifests"
        man.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            man / "preexisting-stale-files.csv",
            _csv_text(
                ["relative_path", "sha256", "review_status", "notes"],
                stale,
            ),
        )
        raise SystemExit(
            "ERROR: --allow-replace refused — recognized prior output has stale governed assets; "
            "archive or choose a new empty output (see manifests/preexisting-stale-files.csv). "
            "Stale files were not deleted."
        )
    return stale


def _integrity_reject(
    *,
    cid: str,
    row: dict[str, Any],
    batch: str,
    man_rel: str,
    code: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "candidate_id": cid,
        "sku": row.get("sku"),
        "product_name": row.get("product_name"),
        "brand": row.get("brand"),
        "stage": "consolidate",
        "reason_code": code,
        "reason_detail": detail,
        "detail_url": row.get("source_detail_url"),
        "image_url": row.get("source_image_url"),
        "provenance_batch": batch,
        "provenance_manifest": man_rel,
        "provenance_source_adapter": row.get("source_adapter") or row.get("provenance_source_adapter"),
    }


def _write_duplicate_physical_report(out: Path, by_sha: dict[str, list[str]]) -> tuple[int, int]:
    rows = []
    dup_files = 0
    for sha, names in sorted(by_sha.items()):
        if len(names) < 2:
            continue
        dup_files += len(names)
        rows.append(
            {
                "sha256": sha,
                "path_count": len(names),
                "relative_paths": "|".join(f"assets/{n}" for n in sorted(names)),
                "review_status": "pending_human_review",
                "notes": "duplicate_physical_bytes",
            }
        )
    atomic_write_text(
        out / "manifests" / "duplicate-physical-assets.csv",
        _csv_text(
            ["sha256", "path_count", "relative_paths", "review_status", "notes"],
            rows,
        ),
    )
    return len(rows), dup_files


def consolidate_batches(
    *,
    input_dir: Path,
    output_dir: Path,
    repo_root: Path,
    allow_replace: bool = False,
) -> dict[str, Any]:
    from .core import validate_output_dir

    inp, _ = _validate_consolidate_paths(input_dir=input_dir, output_dir=output_dir)
    out = validate_output_dir(output_dir, repo_root)
    stale_existing = _reject_nonempty_without_replace(out, allow_replace=allow_replace)

    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "manifests").mkdir(exist_ok=True)

    manifests: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    integrity_rejects: list[dict[str, Any]] = []
    provenance_occurrences: list[dict[str, Any]] = []
    seen: dict[str, dict[str, Any]] = {}

    batch_dirs = sorted(p for p in inp.iterdir())
    for batch in batch_dirs:
        if batch.is_symlink():
            raise DiscoveryError(
                "consolidate",
                "unexpected_governed_symlink",
                f"batch directory is a symlink: {batch.name}",
            )
        if not batch.is_dir():
            continue
        man_path = batch / "manifests" / "manifest.json"
        manifests_dir = batch / "manifests"
        if manifests_dir.is_symlink() or man_path.is_symlink():
            raise DiscoveryError(
                "consolidate",
                "unexpected_governed_symlink",
                f"batch manifests root is a symlink: {batch.name}",
            )
        if not man_path.exists(follow_symlinks=False):
            continue
        try:
            assert_batch_roots_nofollow(batch)
        except DiscoveryError as e:
            raise DiscoveryError(
                "consolidate",
                e.reason_code,
                f"batch {batch.name}: {e.reason_detail}",
            ) from e
        try:
            rows = json.loads(man_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise DiscoveryError(
                "consolidate",
                "corrupt_previous_manifest",
                f"invalid manifest in batch {batch.name}",
            ) from e
        man_rel = "manifests/manifest.json"
        batch_assets = batch / "assets"

        for row in rows:
            row = dict(row)
            # Contract validation before any asset I/O
            code = validate_source_manifest_row(row)
            cid = str(row.get("candidate_id") or "")
            if code:
                integrity_rejects.append(
                    _integrity_reject(
                        cid=cid,
                        row=row,
                        batch=batch.name,
                        man_rel=man_rel,
                        code=code,
                        detail=f"source manifest contract failed: {code}",
                    )
                )
                provenance_occurrences.append(
                    {
                        "candidate_id": cid,
                        "provenance_batch": batch.name,
                        "provenance_manifest": man_rel,
                        "provenance_source_adapter": row.get("source_adapter") or "",
                        "source_asset_path": str(row.get("local_asset_path") or ""),
                        "source_asset_sha256": "",
                        "integrity_status": code,
                    }
                )
                continue

            row = fill_provenance(
                row,
                batch=batch.name,
                manifest=man_rel,
                adapter=str(row.get("source_adapter") or ""),
            )
            row["sha256"] = normalize_sha256(str(row.get("sha256") or ""))
            src_rel = str(row.get("local_asset_path") or "")
            integrity_status = "ok"
            disk_sha = ""
            src_path_str = src_rel
            sha = row["sha256"]

            try:
                src = resolve_manifest_asset_path(
                    assets_root=batch_assets,
                    local_asset_path=src_rel,
                    require_exists=True,
                )
                disk_sha = file_sha256(src)
                if disk_sha != sha:
                    integrity_status = "manifest_sha_mismatch"
                    integrity_rejects.append(
                        _integrity_reject(
                            cid=cid,
                            row=row,
                            batch=batch.name,
                            man_rel=man_rel,
                            code="manifest_sha_mismatch",
                            detail=f"disk={disk_sha} manifest={sha}",
                        )
                    )
                else:
                    if cid in seen:
                        prev = seen[cid]
                        if candidate_content_fingerprint(prev) == candidate_content_fingerprint(row):
                            pass
                        else:
                            conflicts.append(
                                {
                                    "candidate_id": cid,
                                    "reason_code": "duplicate_candidate_conflict",
                                    "batch_a": prev.get("provenance_batch"),
                                    "batch_b": row.get("provenance_batch"),
                                    "manifest_a": prev.get("provenance_manifest"),
                                    "manifest_b": row.get("provenance_manifest"),
                                    "source_adapter_a": prev.get("provenance_source_adapter"),
                                    "source_adapter_b": row.get("provenance_source_adapter"),
                                    "semantic_sha_a": candidate_content_fingerprint(prev),
                                    "semantic_sha_b": candidate_content_fingerprint(row),
                                    "detail": "same candidate_id with differing candidate content",
                                }
                            )
                            integrity_status = "conflict"
                    else:
                        ext = row.get("extension") or src.suffix.lstrip(".") or "jpg"
                        dest_name = f"pending__{sha[:12]}.{ext}"
                        dest = assert_under_assets(out / "assets", out / "assets" / dest_name)
                        if dest.exists(follow_symlinks=False):
                            inspect_local_asset_nofollow(dest, assets_root=out / "assets")
                            if file_sha256(dest) != sha:
                                integrity_status = "destination_sha_mismatch"
                                integrity_rejects.append(
                                    _integrity_reject(
                                        cid=cid,
                                        row=row,
                                        batch=batch.name,
                                        man_rel=man_rel,
                                        code="destination_sha_mismatch",
                                        detail=f"existing dest differs: {dest.name}",
                                    )
                                )
                            else:
                                row["local_asset_path"] = f"assets/{dest_name}"
                                row["sha256"] = sha
                                seen[cid] = row
                                manifests.append(row)
                        else:
                            dest.write_bytes(src.read_bytes())
                            if file_sha256(dest) != sha:
                                dest.unlink(missing_ok=True)
                                integrity_status = "destination_sha_mismatch"
                                integrity_rejects.append(
                                    _integrity_reject(
                                        cid=cid,
                                        row=row,
                                        batch=batch.name,
                                        man_rel=man_rel,
                                        code="destination_sha_mismatch",
                                        detail="write verify failed",
                                    )
                                )
                            else:
                                row["local_asset_path"] = f"assets/{dest_name}"
                                row["sha256"] = sha
                                seen[cid] = row
                                manifests.append(row)
            except DiscoveryError as e:
                integrity_status = e.reason_code
                integrity_rejects.append(
                    _integrity_reject(
                        cid=cid,
                        row=row,
                        batch=batch.name,
                        man_rel=man_rel,
                        code=e.reason_code,
                        detail=e.reason_detail,
                    )
                )

            provenance_occurrences.append(
                {
                    "candidate_id": cid,
                    "provenance_batch": batch.name,
                    "provenance_manifest": man_rel,
                    "provenance_source_adapter": row.get("provenance_source_adapter") or "",
                    "source_asset_path": src_path_str,
                    "source_asset_sha256": disk_sha,
                    "integrity_status": integrity_status,
                }
            )

        rej_path = batch / "manifests" / "rejected.csv"
        if rej_path.exists():
            with rej_path.open(newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    rr = fill_provenance(
                        dict(r),
                        batch=batch.name,
                        manifest="manifests/rejected.csv",
                        adapter=str(r.get("source_adapter") or ""),
                    )
                    rejected.append(rr)

    rejected.extend(integrity_rejects)
    integrity_failure_count = sum(
        1 for r in integrity_rejects if r.get("reason_code") in _CONTRACT_INTEGRITY_CODES
    )

    refuse_overwrite_if_corrupt_json(out / "manifests" / "candidate-provenance.json", code="corrupt_previous_manifest")
    atomic_write_text(
        out / "manifests" / "candidate-provenance.csv",
        _csv_text(PROVENANCE_OCCURRENCE_FIELDS, provenance_occurrences),
    )
    atomic_write_text(
        out / "manifests" / "candidate-provenance.json",
        json.dumps(provenance_occurrences, ensure_ascii=False, indent=2) + "\n",
    )

    # Duplicate physical inventory on output assets (no-follow)
    try:
        by_phys, _ = inventory_assets_by_sha(out / "assets", file_sha256=file_sha256, fail_closed=True)
        dup_groups, dup_files = _write_duplicate_physical_report(out, by_phys)
    except DiscoveryError as e:
        integrity_failure_count += 1
        integrity_rejects.append(
            _integrity_reject(
                cid="",
                row={},
                batch="output",
                man_rel="assets",
                code=e.reason_code,
                detail=e.reason_detail,
            )
        )
        rejected.extend(integrity_rejects[-1:])
        dup_groups, dup_files = 0, 0
        by_phys = {}

    def _fail(status: str, message: str, **extra: Any) -> None:
        cross_brand = rename_and_classify(manifests, out) if manifests else []
        write_outputs(
            out,
            manifests,
            rejected,
            cross_brand=cross_brand,
            conflicts=conflicts if conflicts else [],
            high_reuse=[],
            provenance_occurrences=provenance_occurrences,
        )
        summary = {
            "pilot_id": "IMG-01D-CONSOLIDATE",
            "accepted_rows": len(manifests),
            "rejected_rows": len(rejected),
            "conflict_rows": len(conflicts),
            "integrity_failure_count": integrity_failure_count,
            "stale_existing_names": [s.get("relative_path") if isinstance(s, dict) else s for s in stale_existing],
            "duplicate_physical_asset_groups": dup_groups,
            "duplicate_physical_asset_files": dup_files,
            "database_accessed": False,
            "repository_modified": False,
            "status": status,
            **extra,
        }
        refuse_overwrite_if_corrupt_json(out / "summary.json", code="corrupt_run_state")
        atomic_write_text(out / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        raise SystemExit(message)

    if conflicts:
        _fail(
            "conflict",
            f"ERROR: {len(conflicts)} candidate_id conflict(s); see manifests/candidate-conflicts.*",
        )

    if integrity_failure_count:
        _fail(
            "integrity_failure",
            f"ERROR: {integrity_failure_count} integrity failure(s); status=integrity_failure",
        )

    cross_brand = rename_and_classify(manifests, out)
    write_outputs(
        out,
        manifests,
        rejected,
        cross_brand=cross_brand,
        conflicts=[],
        provenance_occurrences=provenance_occurrences,
    )

    # Re-inventory after rename
    by_phys, _ = inventory_assets_by_sha(out / "assets", file_sha256=file_sha256, fail_closed=True)
    dup_groups, dup_files = _write_duplicate_physical_report(out, by_phys)

    by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in manifests:
        by_sha[m["sha256"]].append(m)

    semantic = semantic_manifest_sha256(manifests)
    summary = {
        "pilot_id": "IMG-01D-CONSOLIDATE",
        "batch_count": len(batch_dirs),
        "accepted_rows": len(manifests),
        "rejected_rows": len(rejected),
        "unique_assets": len(by_sha),
        "family_rows": sum(1 for m in manifests if m["image_specificity"] == "family"),
        "singleton_unverified_rows": sum(
            1 for m in manifests if m["image_specificity"] == "singleton_unverified"
        ),
        "sku_specific_rows": sum(1 for m in manifests if m["image_specificity"] == "sku"),
        "cross_brand_duplicate_rows": sum(
            1 for m in manifests if m["image_specificity"] == "cross_brand_duplicate"
        ),
        "cross_brand_duplicate_groups": len(cross_brand),
        "conflict_rows": 0,
        "integrity_failure_count": 0,
        "duplicate_physical_asset_groups": dup_groups,
        "duplicate_physical_asset_files": dup_files,
        "stale_existing_names": [s.get("relative_path") if isinstance(s, dict) else s for s in stale_existing],
        "status": "ok",
        "manifest_file_sha256": file_sha256(out / "manifests" / "manifest.json"),
        "manifest_semantic_sha256": semantic,
        "database_accessed": False,
        "repository_modified": False,
        "rights_status_policy": "review_required",
    }
    write_summary_and_state(out, summary, manifests, {})
    return json.loads((out / "summary.json").read_text(encoding="utf-8"))
