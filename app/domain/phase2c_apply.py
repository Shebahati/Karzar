"""Phase 2C manufacturer_code APPLY — frozen cohort validation (no DB I/O)."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.domain.phase2c_evidence import (
    CONFLICT_HEURISTIC_UNRESOLVED,
    CONFLICT_NO,
    CONFLICT_RESOLVED_T1,
    CONFLICT_RESOLVED_T2,
    CONFLICT_RESOLVED_T3,
    CONFLICT_STRONG,
    has_stable_locator,
)

OWNER_FROZEN_SHA256 = "43620d24842b946652f8e2a0256aa75e45fbdf1b591b0374dcb84dea21417b03"
OWNER_FROZEN_ROWS = 1350

_VALID_CONFLICT = frozenset(
    {
        CONFLICT_NO,
        CONFLICT_RESOLVED_T1,
        CONFLICT_RESOLVED_T2,
        CONFLICT_RESOLVED_T3,
    }
)

FROZEN_REQUIRED_COLUMNS = (
    "product_id",
    "brand_id",
    "sku",
    "current_manufacturer_code",
    "candidate_manufacturer_code",
    "authority_tier",
    "source_id",
    "source_path",
    "source_sha256",
    "raw_source_code",
    "conflict_status",
    "classification_reason",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_freeze_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_frozen_artifact(
    path: Path,
    *,
    expected_sha256: str | None = None,
    expected_rows: int = OWNER_FROZEN_ROWS,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Structural validation before any DB access."""
    if not path.is_file():
        raise ValueError(f"frozen artifact missing: {path}")
    digest = sha256_file(path)
    exp_sha = expected_sha256 or OWNER_FROZEN_SHA256
    if digest != exp_sha:
        raise ValueError(f"frozen SHA256 mismatch: got {digest}, expected {exp_sha}")
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            rows.append({k: (v or "").strip() for k, v in raw.items()})
    if len(rows) != expected_rows:
        raise ValueError(f"frozen row count {len(rows)} != expected {expected_rows}")
    seen_pids: set[str] = set()
    brand_code_groups: dict[str, list[str]] = {}
    errors: list[str] = []
    for i, row in enumerate(rows, start=2):
        for col in FROZEN_REQUIRED_COLUMNS:
            if col not in row:
                errors.append(f"line {i}: missing column {col}")
        pid = row.get("product_id", "")
        if not pid:
            errors.append(f"line {i}: empty product_id")
            continue
        if pid in seen_pids:
            errors.append(f"line {i}: duplicate product_id {pid}")
        seen_pids.add(pid)
        if not row.get("brand_id"):
            errors.append(f"line {i}: empty brand_id")
        if not row.get("sku"):
            errors.append(f"line {i}: empty sku")
        cur = row.get("current_manufacturer_code", "")
        if cur:
            errors.append(f"line {i}: current_manufacturer_code must be empty at apply time")
        cand = row.get("candidate_manufacturer_code", "")
        if not cand:
            errors.append(f"line {i}: empty candidate_manufacturer_code")
        tier = row.get("authority_tier", "")
        if tier not in ("1", "2"):
            errors.append(f"line {i}: authority_tier must be 1 or 2, got {tier}")
        if not row.get("source_id"):
            errors.append(f"line {i}: missing source_id")
        if not row.get("source_path"):
            errors.append(f"line {i}: missing source_path")
        if not row.get("source_sha256"):
            errors.append(f"line {i}: missing source_sha256")
        if not row.get("raw_source_code"):
            errors.append(f"line {i}: missing raw_source_code")
        if not has_stable_locator(row):
            errors.append(f"line {i}: missing stable source locator")
        cs = row.get("conflict_status", "")
        if cs not in _VALID_CONFLICT:
            errors.append(f"line {i}: invalid conflict_status {cs}")
        if cs in (CONFLICT_HEURISTIC_UNRESOLVED, CONFLICT_STRONG):
            errors.append(f"line {i}: forbidden conflict_status on frozen row")
        if not row.get("classification_reason"):
            errors.append(f"line {i}: missing classification_reason")
        key = f"{row.get('brand_id')}|{cand}"
        brand_code_groups.setdefault(key, []).append(pid)
    dup_groups = {k: v for k, v in brand_code_groups.items() if len(v) > 1}
    if dup_groups:
        errors.append(f"duplicate brand_id+candidate groups: {len(dup_groups)}")
    if errors:
        raise ValueError("frozen structural validation failed:\n" + "\n".join(errors[:50]))
    return rows, {"sha256": digest, "rows": len(rows), "duplicate_brand_code_groups": len(dup_groups)}


def validate_freeze_manifest(manifest: dict[str, Any], artifact_sha: str) -> None:
    checks = {
        "frozen_row_count": OWNER_FROZEN_ROWS,
        "frozen_csv_sha256": artifact_sha,
        "replay_identical": True,
        "conflict_accounting_reconciles": True,
    }
    prov = manifest.get("frozen_provenance") or {}
    if prov.get("complete_frozen_rows") != OWNER_FROZEN_ROWS:
        raise ValueError("manifest frozen_provenance.complete_frozen_rows mismatch")
    if prov.get("incomplete_frozen_rows", 0) != 0:
        raise ValueError("manifest reports incomplete frozen rows")
    for key, expected in checks.items():
        if manifest.get(key) != expected:
            raise ValueError(f"manifest {key}={manifest.get(key)!r} expected {expected!r}")


@dataclass(frozen=True)
class TargetPreflightRow:
    product_id: str
    frozen_sku: str
    live_sku: str
    frozen_brand_id: str
    live_brand_id: str
    candidate_code: str
    live_manufacturer_code: str
    frozen_name: str
    live_name: str
    frozen_slug: str
    live_slug: str
    status: str
    reason: str

    def to_csv_dict(self) -> dict[str, str]:
        name_drift = "yes" if self.frozen_name != self.live_name else ""
        slug_drift = "yes" if self.frozen_slug != self.live_slug else ""
        return {
            "product_id": self.product_id,
            "frozen sku": self.frozen_sku,
            "live sku": self.live_sku,
            "frozen brand_id": self.frozen_brand_id,
            "live brand_id": self.live_brand_id,
            "frozen candidate code": self.candidate_code,
            "live manufacturer_code": self.live_manufacturer_code,
            "name drift": name_drift,
            "slug drift": slug_drift,
            "status": self.status,
            "reason": self.reason,
        }


def reconcile_targets(
    frozen_rows: list[dict[str, str]],
    live_by_id: dict[str, dict[str, str]],
) -> list[TargetPreflightRow]:
    out: list[TargetPreflightRow] = []
    for fr in frozen_rows:
        pid = fr["product_id"]
        live = live_by_id.get(pid)
        if not live:
            out.append(
                TargetPreflightRow(
                    product_id=pid,
                    frozen_sku=fr["sku"],
                    live_sku="",
                    frozen_brand_id=fr["brand_id"],
                    live_brand_id="",
                    candidate_code=fr["candidate_manufacturer_code"],
                    live_manufacturer_code="",
                    frozen_name=fr.get("current_name", ""),
                    live_name="",
                    frozen_slug="",
                    live_slug="",
                    status="BLOCKED",
                    reason="missing_target_product",
                )
            )
            continue
        live_mc = (live.get("manufacturer_code") or "").strip()
        live_sku = (live.get("sku") or "").strip()
        live_brand = str(live.get("brand_id") or "").strip()
        deleted = live.get("deleted_at") or ""
        status = "PASS"
        reason = ""
        if deleted.strip():
            status, reason = "BLOCKED", "deleted_target"
        elif live_mc:
            status, reason = "BLOCKED", "manufacturer_code_already_populated"
        elif live_sku != fr["sku"]:
            status, reason = "BLOCKED", "sku_mismatch"
        elif live_brand != fr["brand_id"]:
            status, reason = "BLOCKED", "brand_mismatch"
        out.append(
            TargetPreflightRow(
                product_id=pid,
                frozen_sku=fr["sku"],
                live_sku=live_sku,
                frozen_brand_id=fr["brand_id"],
                live_brand_id=live_brand,
                candidate_code=fr["candidate_manufacturer_code"],
                live_manufacturer_code=live_mc,
                frozen_name=fr.get("current_name", ""),
                live_name=(live.get("name") or "").strip(),
                frozen_slug="",
                live_slug=(live.get("slug") or "").strip(),
                status=status,
                reason=reason,
            )
        )
    return out


def target_preflight_snapshot_rows(
    frozen_rows: list[dict[str, str]],
    live_by_id: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    snap: list[dict[str, str]] = []
    for fr in frozen_rows:
        pid = fr["product_id"]
        live = live_by_id.get(pid, {})
        snap.append(
            {
                "product_id": pid,
                "sku": (live.get("sku") or fr["sku"]).strip(),
                "brand_id": str(live.get("brand_id") or fr["brand_id"]),
                "manufacturer_code": (live.get("manufacturer_code") or "").strip(),
            }
        )
    snap.sort(key=lambda r: int(r["product_id"]))
    return snap


def snapshot_sha256(rows: list[dict[str, str]], fields: tuple[str, ...]) -> str:
    lines = []
    for r in rows:
        lines.append("|".join(r.get(f, "") for f in fields))
    body = "\n".join(lines) + ("\n" if lines else "")
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def change_log_reason(cohort_sha256: str) -> str:
    short = cohort_sha256[:16]
    reason = f"Phase 2C manufacturer identity owner-frozen backfill; cohort_sha256={short}"
    return reason[:255]


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
