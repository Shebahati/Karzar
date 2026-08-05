"""Worklist loading and checksum verification for IMG-02B candidate discovery."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

from . import CandidateDiscoveryError


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_worklist_checksums(worklist_root: Path) -> str:
    if not worklist_root.is_absolute():
        raise CandidateDiscoveryError("worklist", f"worklist root must be absolute: {worklist_root}")
    if worklist_root.is_symlink() or not worklist_root.is_dir():
        raise CandidateDiscoveryError("worklist", f"invalid worklist root: {worklist_root}")
    checksums = worklist_root / "checksums.sha256"
    if not checksums.is_file() or checksums.is_symlink():
        raise CandidateDiscoveryError("worklist", "checksums.sha256 missing")
    items = 0
    for line in checksums.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise CandidateDiscoveryError("worklist", f"malformed checksum line: {line!r}")
        expected, name = parts[0], parts[1].lstrip("*").strip()
        if "/" in name or ".." in name:
            raise CandidateDiscoveryError("worklist", f"unsafe checksum member: {name!r}")
        member = worklist_root / name
        if member.is_symlink() or not member.is_file():
            raise CandidateDiscoveryError("worklist", f"checksum member missing: {name}")
        actual = sha256_file(member)
        if actual != expected:
            raise CandidateDiscoveryError(
                "worklist", f"checksum mismatch {name}: {actual} != {expected}"
            )
        items += 1
    if items == 0:
        raise CandidateDiscoveryError("worklist", "checksums.sha256 empty")
    return sha256_file(checksums)


def load_worklist_rows(
    worklist_root: Path,
    *,
    brand_key: str,
    filename: str,
    include_ineligible: bool = False,
) -> list[dict[str, str]]:
    verify_worklist_checksums(worklist_root)
    path = worklist_root / filename
    if not path.is_file():
        raise CandidateDiscoveryError("worklist", f"missing {filename}")
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out: list[dict[str, str]] = []
    for row in rows:
        if (row.get("brand_key") or "").strip() != brand_key:
            raise CandidateDiscoveryError(
                "worklist",
                f"brand_key mismatch in {filename}: {row.get('brand_key')!r}",
            )
        if (row.get("work_type") or "").strip() == "manual_review_hold":
            continue
        eligible = (
            (row.get("eligible_for_automatic_discovery") or "").strip().casefold() == "true"
        )
        if not eligible and not include_ineligible:
            continue
        out.append(row)
    out.sort(
        key=lambda r: ((r.get("sku") or "").casefold(), int(r.get("product_id") or 0))
    )
    return out


def worklist_facts(worklist_root: Path) -> dict[str, Any]:
    verify_worklist_checksums(worklist_root)
    all_rows = list(
        csv.DictReader((worklist_root / "worklist-all.csv").open(encoding="utf-8-sig"))
    )
    hold = sum(1 for r in all_rows if r.get("work_type") == "manual_review_hold")
    elig = sum(
        1 for r in all_rows if (r.get("eligible_for_automatic_discovery") or "").casefold() == "true"
    )
    return {
        "work_item_total": len(all_rows),
        "eligible_for_automatic_discovery": elig,
        "manual_review_hold": hold,
        "checksums_digest": sha256_file(worklist_root / "checksums.sha256"),
    }
