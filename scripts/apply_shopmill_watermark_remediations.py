#!/usr/bin/env python3
"""Dry-run / local-only apply of remediated ShopMill assets into product storage.

Does NOT talk to production. Requires an explicit --storage-root (typically
``data/uploads/products`` or a mounted copy of that tree) and writes files only
when ``--apply`` is passed.

DB ProductImage URL updates are intentionally out of scope (ADR-012 / HC-09).
When storage already serves ``/static/uploads/products/{relpath}``, replacing
the file bytes at the mapped relative path is sufficient if the URL path is
unchanged.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _copy_replacement(src: Path, dest: Path) -> None:
    """Copy replacement bytes, converting format when destination suffix differs."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    src_suf = src.suffix.lower()
    dest_suf = dest.suffix.lower()
    if src_suf == dest_suf or dest_suf == "":
        shutil.copy2(src, dest)
        return
    image = Image.open(src).convert("RGB")
    if dest_suf in {".jpg", ".jpeg"}:
        image.save(dest, format="JPEG", quality=95, optimize=True)
    elif dest_suf == ".png":
        image.save(dest, format="PNG", optimize=True)
    elif dest_suf == ".webp":
        image.save(dest, format="WEBP", quality=95, method=6)
    else:
        # Unknown destination type: refuse rather than write mismatched bytes.
        raise ValueError(f"unsupported destination suffix {dest_suf} for {dest}")


@dataclass
class PlanRow:
    rel_path: str
    replacement_path: str
    product_ids: str
    product_count: int
    sha256_original_manifest: str
    sha256_final_manifest: str
    current_source_exists: bool
    current_source_sha256: str
    classification: str
    notes: str


def _load_plans(manifest: Path) -> dict[str, dict]:
    """Unique by mapped relative path; aggregate product ids."""
    rows = list(csv.DictReader(manifest.open(encoding="utf-8")))
    plans: dict[str, dict] = {}
    for row in rows:
        if str(row.get("remediation_ok")).lower() not in {"1", "true"}:
            continue
        rel = (row.get("mapped_local_relative_path") or "").strip()
        src = Path(row.get("output_path") or "")
        if not rel:
            continue
        entry = plans.setdefault(
            rel,
            {
                "replacement": src,
                "product_ids": set(),
                "sha256_original": (row.get("sha256_original") or "").strip(),
                "sha256_final": (row.get("sha256_final") or "").strip(),
            },
        )
        pid = (row.get("product_id") or "").strip()
        if pid:
            entry["product_ids"].add(pid)
        if src.is_file():
            entry["replacement"] = src
        if row.get("sha256_final"):
            entry["sha256_final"] = row["sha256_final"].strip()
    return plans


def _classify(
    *,
    dest: Path,
    replacement: Path,
    sha_original: str,
    sha_final: str,
) -> tuple[str, str, str]:
    """Return (classification, current_sha, notes)."""
    if not replacement.is_file():
        return "OTHER BLOCKER", "", "replacement_missing"
    if not dest.is_file():
        return "MISSING SOURCE", "", "serving_file_absent"
    current = _sha256(dest)
    if sha_original and current == sha_original:
        return "EXACT MATCH", current, "current_matches_manifest_original"
    if sha_final and current == sha_final:
        return "EXACT MATCH", current, "already_equals_repaired_final"
    if sha_original and current != sha_original:
        return "SOURCE CHANGED", current, "serving_bytes_differ_from_manifest_original"
    return "AMBIGUOUS", current, "no_manifest_original_hash_to_compare"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="remediation-manifest.csv from IMG-SHOPMILL-WATERMARK-CLEANUP",
    )
    p.add_argument(
        "--storage-root",
        type=Path,
        required=True,
        help="Product uploads root (e.g. data/uploads/products)",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Actually copy files (default: dry-run)",
    )
    p.add_argument(
        "--allow-missing-storage-root",
        action="store_true",
        help="Create storage-root if missing (dry-run still reports MISSING SOURCE)",
    )
    p.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Optional machine-readable dry-run/apply report path",
    )
    p.add_argument(
        "--require-exact-match",
        action="store_true",
        help="With --apply, only overwrite EXACT MATCH targets",
    )
    args = p.parse_args(argv)

    storage = args.storage_root.resolve()
    if not storage.is_dir():
        if args.allow_missing_storage_root and not args.apply:
            storage.mkdir(parents=True, exist_ok=True)
        else:
            print(f"storage-root missing: {storage}", file=sys.stderr)
            return 2

    plans = _load_plans(args.manifest)
    plan_rows: list[PlanRow] = []
    for rel, meta in sorted(plans.items()):
        dest = storage / rel
        replacement: Path = meta["replacement"]
        classification, current_sha, notes = _classify(
            dest=dest,
            replacement=replacement,
            sha_original=meta["sha256_original"],
            sha_final=meta["sha256_final"],
        )
        # If replacement path from manifest points at vanished /var/tmp, try durable rescue
        if notes == "replacement_missing":
            durable = (
                REPO_ROOT
                / ".local-rescue"
                / "shopmill-watermark-cleanup"
                / "repaired_assets"
                / Path(meta["sha256_original"]).name
            )
            # repaired files are named {sha}{ext}
            candidates = list(
                (
                    REPO_ROOT / ".local-rescue/shopmill-watermark-cleanup/repaired_assets"
                ).glob(f"{meta['sha256_original']}.*")
            ) if meta["sha256_original"] else []
            if candidates:
                replacement = candidates[0]
                classification, current_sha, notes = _classify(
                    dest=dest,
                    replacement=replacement,
                    sha_original=meta["sha256_original"],
                    sha_final=meta["sha256_final"],
                )
                notes = f"{notes};replacement_resolved_from_durable_rescue"

        pids = sorted(meta["product_ids"], key=lambda x: int(x) if x.isdigit() else x)
        plan_rows.append(
            PlanRow(
                rel_path=rel,
                replacement_path=str(replacement),
                product_ids=",".join(pids),
                product_count=len(pids),
                sha256_original_manifest=meta["sha256_original"],
                sha256_final_manifest=meta["sha256_final"],
                current_source_exists=dest.is_file(),
                current_source_sha256=current_sha,
                classification=classification,
                notes=notes,
            )
        )

    counts = Counter(r.classification for r in plan_rows)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"mode={mode}")
    print(f"storage_root={storage}")
    print(f"planned_unique_paths={len(plan_rows)}")
    print(f"classification_counts={dict(counts)}")
    print(f"products_affected={sum(r.product_count for r in plan_rows)}")

    replaced = 0
    skipped = 0
    errors: list[str] = []

    for row in plan_rows:
        dest = storage / row.rel_path
        action = "COPY" if args.apply else "DRY"
        print(
            f"{action} class={row.classification} {row.replacement_path} -> {dest} "
            f"products={row.product_count} notes={row.notes}"
        )
        if not args.apply:
            continue
        if args.require_exact_match and row.classification != "EXACT MATCH":
            skipped += 1
            continue
        if row.classification in {"SOURCE CHANGED", "AMBIGUOUS", "OTHER BLOCKER"}:
            skipped += 1
            errors.append(f"refusing {row.rel_path}: {row.classification} ({row.notes})")
            continue
        if row.classification == "MISSING SOURCE":
            # Creating new file where absent is allowed only if operator opts in later;
            # default refuse to avoid inventing paths not previously served.
            skipped += 1
            errors.append(f"refusing create-missing {row.rel_path}")
            continue
        try:
            if dest.is_file():
                bak = dest.with_suffix(dest.suffix + ".shopmill-bak")
                if not bak.exists():
                    shutil.copy2(dest, bak)
            _copy_replacement(Path(row.replacement_path), dest)
            print(f"  sha256={_sha256(dest)}")
            replaced += 1
        except (OSError, ValueError) as exc:
            errors.append(f"{row.rel_path}: {exc}")

    report = {
        "observed_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "storage_root": str(storage),
        "planned_unique_paths": len(plan_rows),
        "classification_counts": dict(counts),
        "products_affected": sum(r.product_count for r in plan_rows),
        "replaced": replaced,
        "skipped": skipped,
        "errors": errors,
        "rows": [asdict(r) for r in plan_rows],
    }
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"report_json={args.report_json}")

    if errors and args.apply:
        print(f"errors={len(errors)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
