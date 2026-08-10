"""Load and verify accepted IMG-FAST-01A seed artifact."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

from . import ACCEPTED_SEED_ARTIFACT_SHA256, BASELINE_SEED_TOTAL
from .contracts import DiscoveryError, SeedProduct

SEED_CSV = "internet-discovery-universe.csv"
CHECKSUMS_NAME = "checksums.sha256"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_zip_sha256(zip_path: Path, expected: str = ACCEPTED_SEED_ARTIFACT_SHA256) -> None:
    got = sha256_file(zip_path)
    if got.lower() != expected.lower():
        raise DiscoveryError(
            "seed_artifact_sha_mismatch",
            f"expected {expected}, got {got} for {zip_path}",
        )


def verify_checksums_from_dir(package_dir: Path) -> None:
    sums_path = package_dir / CHECKSUMS_NAME
    if not sums_path.is_file():
        raise DiscoveryError("missing_checksums", f"missing {sums_path}")
    failures: list[str] = []
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        digest, name = parts
        fp = package_dir / name
        if not fp.is_file():
            failures.append(f"missing file {name}")
            continue
        if sha256_file(fp).lower() != digest.lower():
            failures.append(f"checksum mismatch {name}")
    if failures:
        raise DiscoveryError("checksum_failures", "; ".join(failures))


def extract_seed_from_zip(zip_path: Path, work_dir: Path) -> Path:
    verify_zip_sha256(zip_path)
    work_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(work_dir)
    verify_checksums_from_dir(work_dir)
    seed_csv = work_dir / SEED_CSV
    if not seed_csv.is_file():
        raise DiscoveryError("missing_seed_csv", f"{SEED_CSV} not in artifact")
    return seed_csv


def load_seed_products(seed_csv: Path) -> list[SeedProduct]:
    rows: list[SeedProduct] = []
    seen: set[int] = set()
    with seed_csv.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = int(row["product_id"])
            if pid in seen:
                raise DiscoveryError("duplicate_seed_id", f"duplicate product_id {pid}")
            seen.add(pid)
            rows.append(
                SeedProduct(
                    product_id=pid,
                    sku=str(row.get("sku") or "").strip(),
                    brand_key=str(row.get("brand_key") or "").strip(),
                    category_id=int(row["category_id"]) if row.get("category_id") else None,
                    category_slug=str(row.get("category_slug") or "").strip(),
                    product_name=str(row.get("product_name") or "").strip(),
                    current_state=str(row.get("current_state") or "").strip(),
                    suggested_discovery_lane=str(row.get("suggested_discovery_lane") or "").strip(),
                    notes=str(row.get("notes") or "").strip(),
                )
            )
    if len(rows) != BASELINE_SEED_TOTAL:
        raise DiscoveryError(
            "seed_count_mismatch",
            f"expected {BASELINE_SEED_TOTAL} unique seed IDs, got {len(rows)}",
        )
    return rows


def write_accepted_seed_manifest(
    package_dir: Path,
    *,
    zip_path: Path,
    seed_products: list[SeedProduct],
) -> Path:
    out = package_dir / "accepted-seed-manifest.json"
    payload = {
        "accepted_artifact_zip": str(zip_path),
        "accepted_artifact_sha256": sha256_file(zip_path),
        "baseline_seed_total": len(seed_products),
        "seed_csv": SEED_CSV,
        "product_ids": [p.product_id for p in seed_products],
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
