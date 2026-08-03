"""Output writers, hashing, contact sheet, run-state comparison."""

from __future__ import annotations

import csv
import hashlib
import html
import io
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .atomic import atomic_write_text, load_json_object, refuse_overwrite_if_corrupt_json
from .contracts import (
    CONFLICT_FIELDS,
    CROSS_BRAND_FIELDS,
    GROUP_FIELDS,
    HIGH_REUSE_FIELDS,
    HIGH_REUSE_SKU_THRESHOLD,
    MANIFEST_FIELDS,
    PROVENANCE_OCCURRENCE_FIELDS,
    REJECT_FIELDS,
    SEMANTIC_FIELDS,
    DiscoveryError,
    normalize_identity_token,
    row_semantic_fingerprint,
)
from .paths import (
    assert_under_assets,
    governed_asset_filename,
    inspect_local_asset_nofollow,
    inventory_assets_by_sha,
    iter_local_asset_files,
    resolve_manifest_asset_path,
)


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_semantic_value(value: Any) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value


def semantic_manifest_payload(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(rows, key=lambda r: (str(r.get("sku") or ""), str(r.get("candidate_id") or "")))
    out: list[dict[str, Any]] = []
    for row in ordered:
        out.append({k: normalize_semantic_value(row.get(k)) for k in SEMANTIC_FIELDS})
    return out


def semantic_manifest_sha256(rows: list[dict[str, Any]]) -> str:
    blob = json.dumps(
        semantic_manifest_payload(rows),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def family_label(skus: list[str]) -> str:
    prefixes = sorted({s.rsplit("-", 1)[0] for s in skus})
    if len(skus) == 1:
        return skus[0]
    if len(prefixes) == 1:
        return f"{prefixes[0]}-family"
    return f"multi-{'-'.join(prefixes)}-family"


def shared_group_id(skus: list[str], brands: list[str], sha256: str) -> str:
    joined = ",".join(sorted(skus))
    brand_join = ",".join(sorted(normalize_identity_token(b) for b in brands))
    digest = hashlib.sha256(f"{brand_join}|{joined}|{sha256}".encode()).hexdigest()[:10]
    return f"grp-{safe_group_label(skus)}-{digest}"


def safe_group_label(skus: list[str]) -> str:
    from .paths import safe_path_segment

    return safe_path_segment(family_label(skus), max_len=32)


def classify_sha_group(rows: list[dict[str, Any]]) -> tuple[str, bool | str]:
    """Distinguish same-brand family vs cross-brand duplicate vs singleton."""
    skus = {str(r.get("sku") or "") for r in rows}
    brands = {normalize_identity_token(str(r.get("brand") or "")) for r in rows}
    brands.discard("")
    product_keys = {str(r.get("product_key") or "") for r in rows}
    product_keys.discard("")

    if len(brands) > 1:
        return "cross_brand_duplicate", "unknown"
    if len(skus) > 1:
        return "family", False
    if len(product_keys) <= 1 and len(rows) > 1:
        # same product, multiple candidates sharing bytes
        return "singleton_unverified", "unknown"
    return "singleton_unverified", "unknown"


def rename_and_classify(manifests: list[dict[str, Any]], out: Path, brand_slug: str = "asset") -> list[dict[str, Any]]:
    """Classify by content SHA; return cross-brand duplicate records."""
    by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in manifests:
        by_sha[m["sha256"]].append(m)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    # Fail closed on any unexpected symlink / non-regular entry before classification I/O
    iter_local_asset_files(assets, fail_closed=True)
    cross_brand: list[dict[str, Any]] = []

    for sha, group in by_sha.items():
        skus = sorted({str(x["sku"]) for x in group})
        brands = sorted({str(x.get("brand") or brand_slug) for x in group})
        specificity, variant_specific = classify_sha_group(group)
        gid = shared_group_id(skus, brands, sha)
        ext = group[0]["extension"]
        label = family_label(skus)
        # Prefer first brand for filename slug; never put raw hostile values in path
        final_name = governed_asset_filename(
            brand=brands[0] if brands else brand_slug,
            label=label,
            sha256=sha,
            extension=str(ext),
        )
        current = None
        for m in group:
            try:
                p = resolve_manifest_asset_path(
                    assets_root=assets,
                    local_asset_path=str(m.get("local_asset_path") or ""),
                    require_exists=True,
                )
                current = p
                break
            except DiscoveryError:
                continue
        if current is None:
            short = sha[:12]
            for cand in iter_local_asset_files(assets, fail_closed=True):
                if f"__{short}." not in cand.name:
                    continue
                if file_sha256(cand) == sha:
                    current = cand
                    break
        if current is None:
            continue
        dest = assert_under_assets(assets, assets / final_name)
        if current.name != dest.name:
            if dest.exists(follow_symlinks=False):
                inspect_local_asset_nofollow(dest, assets_root=assets)
                if file_sha256(dest) != sha:
                    raise DiscoveryError(
                        "fs",
                        "destination_sha_mismatch",
                        f"refuse overwrite differing hash: {dest.name}",
                    )
                if "pending__" in current.name or current.name.startswith("pending__"):
                    current.unlink(missing_ok=True)
            else:
                current.rename(dest)
                assert_under_assets(assets, dest)
        for m in group:
            m["local_asset_path"] = f"assets/{final_name}"
            m["image_specificity"] = specificity
            m["variant_specific"] = variant_specific
            m["shared_asset_group"] = gid
            if specificity == "cross_brand_duplicate":
                m["review_status"] = "pending_human_review"
        if specificity == "cross_brand_duplicate":
            cross_brand.append(
                {
                    "sha256": sha,
                    "brands": "|".join(brands),
                    "skus": "|".join(skus),
                    "candidate_ids": "|".join(sorted(str(x.get("candidate_id") or "") for x in group)),
                    "shared_asset_group": gid,
                    "review_status": "pending_human_review",
                    "notes": "identical_bytes_across_brands",
                }
            )
    return cross_brand


def referenced_asset_sha256s(manifest: list[dict[str, Any]]) -> set[str]:
    return {str(r["sha256"]) for r in manifest if r.get("sha256")}


def load_previous_manifest(out: Path, *, resume: bool) -> dict[str, dict[str, Any]]:
    path = out / "manifests" / "manifest.json"
    if not path.exists():
        return {}
    if not resume:
        return {}
    data = load_json_object(path, missing_ok=False, corrupt_code="corrupt_previous_manifest")
    if not isinstance(data, list):
        raise DiscoveryError("state", "corrupt_previous_manifest", "manifest.json root must be a list")
    from .contracts import validate_source_manifest_row

    out_map: dict[str, dict[str, Any]] = {}
    for row in data:
        if not isinstance(row, dict):
            raise DiscoveryError("state", "manifest_row_not_object", "manifest row must be an object")
        code = validate_source_manifest_row(row)
        if code:
            raise DiscoveryError(
                "state",
                code,
                f"prior manifest identity contract failed: {code}",
            )
        cid = str(row.get("candidate_id") or "").strip()
        out_map[cid] = row
    return out_map


def load_run_state(out: Path, *, resume: bool) -> dict[str, Any]:
    path = out / "manifests" / "run-state.json"
    if not path.exists():
        return {}
    if not resume:
        # Presence of corrupt state still blocks overwrite later; detect early only when resume
        try:
            load_json_object(path, missing_ok=True, corrupt_code="corrupt_run_state")
        except DiscoveryError:
            raise
        return {}
    data = load_json_object(path, missing_ok=False, corrupt_code="corrupt_run_state")
    if not isinstance(data, dict):
        raise DiscoveryError("state", "corrupt_run_state", "run-state.json root must be an object")
    return data


def compare_runs(
    *,
    previous_state: dict[str, Any],
    previous_manifest: list[dict[str, Any]],
    current_manifest: list[dict[str, Any]],
    current_semantic: str,
    asset_dir: Path,
) -> dict[str, Any]:
    prev_semantic = previous_state.get("semantic_manifest_sha256") or previous_state.get(
        "manifest_semantic_sha256"
    )
    prev_assets = set(previous_state.get("referenced_asset_sha256s") or previous_state.get("asset_sha256s") or [])
    cur_referenced = referenced_asset_sha256s(current_manifest)

    by_sha, unexpected_symlinks = inventory_assets_by_sha(
        asset_dir, file_sha256=file_sha256, fail_closed=True
    )
    # All physical paths per SHA (do not collapse to one filename)
    on_disk_set = set(by_sha.keys())
    duplicate_physical_asset_groups = sum(1 for names in by_sha.values() if len(names) > 1)
    duplicate_physical_asset_files = sum(len(names) for names in by_sha.values() if len(names) > 1)

    new_referenced = sorted(cur_referenced - prev_assets) if prev_assets else sorted(cur_referenced)
    removed_referenced = sorted(prev_assets - cur_referenced) if prev_assets else []
    stale_unreferenced = sorted(on_disk_set - cur_referenced)
    missing_referenced = sorted(cur_referenced - on_disk_set)

    prev_by_id = {
        str(r.get("candidate_id") or ""): r for r in previous_manifest if r.get("candidate_id")
    }
    cur_by_id = {
        str(r.get("candidate_id") or ""): r for r in current_manifest if r.get("candidate_id")
    }
    all_ids = set(prev_by_id) | set(cur_by_id)
    changed = 0
    unchanged = 0
    for cid in all_ids:
        if cid not in prev_by_id or cid not in cur_by_id:
            changed += 1
            continue
        if row_semantic_fingerprint(prev_by_id[cid]) == row_semantic_fingerprint(cur_by_id[cid]):
            unchanged += 1
        else:
            changed += 1

    asset_set_stable = bool(prev_assets) and prev_assets == cur_referenced and not missing_referenced

    return {
        "previous_semantic_manifest_sha256": prev_semantic,
        "current_semantic_manifest_sha256": current_semantic,
        "asset_set_stable": asset_set_stable,
        "semantic_manifest_stable": bool(prev_semantic) and prev_semantic == current_semantic,
        "new_referenced_assets": len(new_referenced),
        "removed_referenced_assets": len(removed_referenced),
        "stale_unreferenced_files": len(stale_unreferenced),
        "missing_referenced_files": len(missing_referenced),
        "new_unique_assets": len(new_referenced),
        "removed_assets": len(removed_referenced),
        "changed_rows": changed if prev_by_id else 0,
        "unchanged_rows": unchanged if prev_by_id else len(cur_by_id),
        "current_referenced_asset_sha256s": sorted(cur_referenced),
        "new_referenced_asset_sha256s": new_referenced,
        "removed_referenced_asset_sha256s": removed_referenced,
        "stale_unreferenced_asset_sha256s": stale_unreferenced,
        "missing_referenced_asset_sha256s": missing_referenced,
        "duplicate_physical_asset_groups": duplicate_physical_asset_groups,
        "duplicate_physical_asset_files": duplicate_physical_asset_files,
        "unexpected_symlinks": unexpected_symlinks,
        "on_disk_sha_to_paths": {k: sorted(v) for k, v in sorted(by_sha.items())},
    }


def _csv_text(fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    for row in rows:
        out = {k: row.get(k, "") for k in fieldnames}
        for bk in ("sku_confirmed", "manufacturer_confirmed", "variant_specific"):
            if bk in out and isinstance(out[bk], bool):
                out[bk] = str(out[bk]).lower()
        w.writerow(out)
    return buf.getvalue()


def high_reuse_asset_rows(
    manifests: list[dict[str, Any]],
    *,
    threshold: int = HIGH_REUSE_SKU_THRESHOLD,
) -> list[dict[str, Any]]:
    """Flag unusually reused same-brand SHAs for human review (does not reject)."""
    by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in manifests:
        if m.get("sha256"):
            by_sha[str(m["sha256"])].append(m)
    rows: list[dict[str, Any]] = []
    for sha, group in sorted(by_sha.items()):
        brands = {normalize_identity_token(str(g.get("brand") or "")) for g in group}
        brands.discard("")
        if len(brands) != 1:
            continue  # cross-brand handled separately
        skus = sorted({str(g.get("sku") or "") for g in group if g.get("sku")})
        if len(skus) <= threshold:
            continue
        prefixes = sorted({s.rsplit("-", 1)[0] for s in skus})
        pkeys = sorted({str(g.get("product_key") or "") for g in group if g.get("product_key")})
        rows.append(
            {
                "sha256": sha,
                "brand": next(iter(brands)),
                "product_key_count": len(pkeys),
                "sku_count": len(skus),
                "sku_prefix_count": len(prefixes),
                "candidate_ids": "|".join(sorted(str(g.get("candidate_id") or "") for g in group)),
                "shared_asset_group": group[0].get("shared_asset_group") or "",
                "review_status": "pending_human_review",
                "reason": f"same_brand_sha_shared_by_{len(skus)}_skus_threshold_{threshold}",
            }
        )
    return rows


def safe_href(url: str, *, allow_http: bool = False) -> str | None:
    """Return href only for https (or governed http); else None (render as text)."""
    u = (url or "").strip()
    if not u:
        return None
    lower = u.lower()
    if lower.startswith("https://"):
        return u
    if allow_http and lower.startswith("http://"):
        return u
    return None


def write_outputs(
    out: Path,
    manifests: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    *,
    cross_brand: list[dict[str, Any]] | None = None,
    conflicts: list[dict[str, Any]] | None = None,
    high_reuse: list[dict[str, Any]] | None = None,
    provenance_occurrences: list[dict[str, Any]] | None = None,
) -> None:
    man = out / "manifests"
    man.mkdir(parents=True, exist_ok=True)
    ordered = sorted(manifests, key=lambda m: (m["sku"], m.get("candidate_id") or ""))

    refuse_overwrite_if_corrupt_json(man / "manifest.json", code="corrupt_previous_manifest")

    atomic_write_text(man / "manifest.csv", _csv_text(MANIFEST_FIELDS, ordered))
    payload = [{k: m.get(k) for k in MANIFEST_FIELDS} for m in ordered]
    atomic_write_text(
        man / "manifest.json",
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write_text(
        man / "rejected.csv",
        _csv_text(
            REJECT_FIELDS,
            sorted(rejected, key=lambda x: (x.get("sku") or "", x.get("candidate_id") or "")),
        ),
    )

    by_sha: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in manifests:
        by_sha[m["sha256"]].append(m)
    group_rows = []
    for sha, group in sorted(by_sha.items(), key=lambda kv: kv[1][0].get("shared_asset_group") or ""):
        g0 = group[0]
        skus = sorted({x["sku"] for x in group})
        brands = sorted({str(x.get("brand") or "") for x in group})
        group_rows.append(
            {
                "shared_asset_group": g0["shared_asset_group"],
                "sha256": sha,
                "local_asset_path": g0["local_asset_path"],
                "source_image_url": g0.get("source_image_url", ""),
                "sku_count": len(skus),
                "skus": "|".join(skus),
                "brands": "|".join(brands),
                "image_specificity": g0.get("image_specificity", ""),
                "byte_size": g0.get("byte_size", ""),
                "width": g0.get("width", ""),
                "height": g0.get("height", ""),
            }
        )
    atomic_write_text(man / "source-groups.csv", _csv_text(GROUP_FIELDS, group_rows))

    if cross_brand is not None:
        atomic_write_text(man / "cross-brand-duplicates.csv", _csv_text(CROSS_BRAND_FIELDS, cross_brand))
    if conflicts is not None:
        refuse_overwrite_if_corrupt_json(man / "candidate-conflicts.json", code="corrupt_previous_manifest")
        atomic_write_text(man / "candidate-conflicts.csv", _csv_text(CONFLICT_FIELDS, conflicts))
        atomic_write_text(
            man / "candidate-conflicts.json",
            json.dumps(conflicts, ensure_ascii=False, indent=2) + "\n",
        )
    if high_reuse is None:
        high_reuse = high_reuse_asset_rows(ordered)
    atomic_write_text(man / "high-reuse-assets.csv", _csv_text(HIGH_REUSE_FIELDS, high_reuse))
    if provenance_occurrences is not None:
        refuse_overwrite_if_corrupt_json(man / "candidate-provenance.json", code="corrupt_previous_manifest")
        atomic_write_text(
            man / "candidate-provenance.csv",
            _csv_text(PROVENANCE_OCCURRENCE_FIELDS, provenance_occurrences),
        )
        atomic_write_text(
            man / "candidate-provenance.json",
            json.dumps(provenance_occurrences, ensure_ascii=False, indent=2) + "\n",
        )

    _write_contact_sheet(out, ordered)


def _write_contact_sheet(out: Path, manifests: list[dict[str, Any]]) -> None:
    review = out / "review"
    review.mkdir(parents=True, exist_ok=True)
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in manifests:
        by_group[m["shared_asset_group"]].append(m)
    parts = [
        "<!DOCTYPE html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>",
        "<title>Image Discovery Contact Sheet</title>",
        "<style>body{font-family:Tahoma,sans-serif;margin:24px}",
        "img{max-width:220px;max-height:220px}.g{border:1px solid #ddd;padding:12px;margin:12px 0;background:#fff}</style>",
        "</head><body>",
        "<h1>Image discovery — human review</h1>",
        "<p>rights_status=review_required · no commercial permission inferred</p>",
    ]
    for gid, group in sorted(by_group.items()):
        parts.append(f"<div class='g'><h2>{html.escape(gid)}</h2>")
        rel = "../" + group[0]["local_asset_path"]
        parts.append(f"<p><img src='{html.escape(rel)}' alt=''></p>")
        for m in sorted(group, key=lambda x: (x["sku"], x.get("candidate_id") or "")):
            dims = f"{m.get('width')}×{m.get('height')}" if m.get("width") != "" else "unavailable"
            parts.append("<dl>")
            for label, key in [
                ("SKU", "sku"),
                ("Product", "product_name"),
                ("Brand", "brand"),
                ("Product key", "product_key"),
                ("Candidate", "candidate_id"),
                ("Role", "image_role"),
                ("Source rank", "source_rank"),
                ("Specificity", "image_specificity"),
                ("Variant", "variant_specific"),
                ("Quality", "foreground_occupancy_status"),
                ("Review", "review_status"),
                ("Rights", "rights_status"),
                ("Provenance batch", "provenance_batch"),
                ("Provenance manifest", "provenance_manifest"),
                ("Manufacturer evidence", "manufacturer_evidence"),
                ("SKU evidence", "sku_evidence"),
            ]:
                parts.append(f"<dt>{html.escape(label)}</dt><dd>{html.escape(str(m.get(key, '')))}</dd>")
            detail_url = str(m.get("source_detail_url", "") or "")
            image_url = str(m.get("source_image_url", "") or "")
            detail_href = safe_href(detail_url)
            image_href = safe_href(image_url)
            if detail_href:
                parts.append(
                    f"<dt>Detail</dt><dd><a href='{html.escape(detail_href)}'>"
                    f"{html.escape(detail_url)}</a></dd>"
                )
            else:
                parts.append(f"<dt>Detail</dt><dd>{html.escape(detail_url)}</dd>")
            if image_href:
                parts.append(
                    f"<dt>Image</dt><dd><a href='{html.escape(image_href)}'>"
                    f"{html.escape(image_url)}</a></dd>"
                )
            else:
                parts.append(f"<dt>Image</dt><dd>{html.escape(image_url)}</dd>")
            parts.append(f"<dt>SHA-256</dt><dd>{html.escape(str(m.get('sha256','')))}</dd>")
            parts.append(f"<dt>Dimensions</dt><dd>{html.escape(dims)}</dd>")
            parts.append("</dl>")
        parts.append("</div>")
    parts.append("</body></html>")
    atomic_write_text(review / "contact-sheet.html", "\n".join(parts))


def write_summary_and_state(
    out: Path,
    summary: dict[str, Any],
    manifests: list[dict[str, Any]],
    comparison: dict[str, Any],
) -> None:
    man = out / "manifests"
    refuse_overwrite_if_corrupt_json(man / "run-state.json", code="corrupt_run_state")
    refuse_overwrite_if_corrupt_json(out / "summary.json", code="corrupt_run_state")

    summary = dict(summary)
    summary.update(comparison)
    summary["executed_at_utc"] = datetime.now(UTC).isoformat()
    atomic_write_text(out / "summary.json", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

    referenced = sorted(referenced_asset_sha256s(manifests))
    state = {
        "written_at_utc": datetime.now(UTC).isoformat(),
        "semantic_manifest_sha256": summary.get("manifest_semantic_sha256"),
        "manifest_file_sha256": summary.get("manifest_file_sha256"),
        "referenced_asset_sha256s": referenced,
        # retained for older readers; equals referenced set
        "asset_sha256s": referenced,
        "accepted_candidate_ids": sorted(str(m.get("candidate_id") or "") for m in manifests),
        "comparison": comparison,
    }
    atomic_write_text(man / "run-state.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")
