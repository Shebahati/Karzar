"""Phase 2C manufacturer_code APPLY — frozen cohort validation (no DB I/O)."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

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

CHANGE_LOG_CONTRACT_REFERENCE = "app.crud.audit.record_product_change"
CHANGE_LOG_EXECUTION_PATH = "transactional SQL equivalent"
CHANGE_LOG_EQUIVALENT_FIELDS = (
    "product_id",
    "field_name",
    "old_value",
    "new_value",
    "reason",
    "actor_user_id",
)

SlugComparisonStatus = Literal[
    "NOT_AVAILABLE_IN_FROZEN_ARTIFACT",
    "COMPARABLE",
]

SlugDriftRows = Literal["NOT_APPLICABLE"] | int

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

# Owner-frozen cohort columns that are identity-comparable against live DB.
FROZEN_COMPARABLE_IDENTITY_COLUMNS = (
    "product_id",
    "brand_id",
    "sku",
    "current_name",
    "current_manufacturer_code",
    "candidate_manufacturer_code",
)

REHEARSAL_LOGIC_FILES = (
    "app/domain/phase2c_apply.py",
    "scripts/apply_manufacturer_identity_phase2c.py",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rehearsal_logic_file_sha256(repo_root: Path) -> dict[str, str]:
    """Content hashes for modules that control rehearsal / apply semantics."""
    out: dict[str, str] = {}
    for rel in REHEARSAL_LOGIC_FILES:
        path = repo_root / rel
        if not path.is_file():
            raise FileNotFoundError(f"rehearsal logic file missing: {rel}")
        out[rel] = sha256_file(path)
    return out


def frozen_artifact_has_slug_column(fieldnames: list[str] | None) -> bool:
    if not fieldnames:
        return False
    names = {n.strip() for n in fieldnames}
    return bool(names & {"slug", "current_slug", "frozen_slug"})


def slug_comparison_status_for_artifact(path: Path) -> SlugComparisonStatus:
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if frozen_artifact_has_slug_column(list(reader.fieldnames or [])):
            return "COMPARABLE"
    return "NOT_AVAILABLE_IN_FROZEN_ARTIFACT"


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
        fieldnames = list(reader.fieldnames or [])
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
    slug_status = (
        "COMPARABLE"
        if frozen_artifact_has_slug_column(fieldnames)
        else "NOT_AVAILABLE_IN_FROZEN_ARTIFACT"
    )
    return rows, {
        "sha256": digest,
        "rows": len(rows),
        "duplicate_brand_code_groups": len(dup_groups),
        "slug_comparison_status": slug_status,
        "fieldnames": fieldnames,
    }


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
    live_slug: str
    slug_comparison_status: SlugComparisonStatus
    frozen_slug: str | None
    status: str
    reason: str

    @property
    def name_drift(self) -> bool:
        return self.frozen_name != self.live_name

    @property
    def slug_drift(self) -> bool | None:
        """None when slug is not comparable; True/False when frozen slug exists."""
        if self.slug_comparison_status != "COMPARABLE":
            return None
        return (self.frozen_slug or "") != self.live_slug

    def to_csv_dict(self) -> dict[str, str]:
        if self.slug_comparison_status == "NOT_AVAILABLE_IN_FROZEN_ARTIFACT":
            slug_drift_cell = "NOT_APPLICABLE"
            frozen_slug_cell = "NOT_AVAILABLE_IN_FROZEN_ARTIFACT"
        else:
            slug_drift_cell = "yes" if self.slug_drift else ""
            frozen_slug_cell = self.frozen_slug or ""
        return {
            "product_id": self.product_id,
            "frozen sku": self.frozen_sku,
            "live sku": self.live_sku,
            "frozen brand_id": self.frozen_brand_id,
            "live brand_id": self.live_brand_id,
            "frozen candidate code": self.candidate_code,
            "live manufacturer_code": self.live_manufacturer_code,
            "name drift": "yes" if self.name_drift else "",
            "slug comparison": self.slug_comparison_status,
            "frozen slug": frozen_slug_cell,
            "live slug": self.live_slug,
            "slug drift": slug_drift_cell,
            "status": self.status,
            "reason": self.reason,
        }


def _frozen_slug_value(fr: dict[str, str]) -> str | None:
    for key in ("current_slug", "slug", "frozen_slug"):
        if key in fr:
            return (fr.get(key) or "").strip()
    return None


def reconcile_targets(
    frozen_rows: list[dict[str, str]],
    live_by_id: dict[str, dict[str, str]],
    *,
    slug_comparison_status: SlugComparisonStatus = "NOT_AVAILABLE_IN_FROZEN_ARTIFACT",
) -> list[TargetPreflightRow]:
    out: list[TargetPreflightRow] = []
    for fr in frozen_rows:
        pid = fr["product_id"]
        frozen_slug = (
            _frozen_slug_value(fr) if slug_comparison_status == "COMPARABLE" else None
        )
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
                    live_slug="",
                    slug_comparison_status=slug_comparison_status,
                    frozen_slug=frozen_slug,
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
        elif (fr.get("current_name") or "").strip() != (live.get("name") or "").strip():
            # Name is present on the frozen cohort — treat drift as an identity gate.
            status, reason = "BLOCKED", "name_mismatch"
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
                live_slug=(live.get("slug") or "").strip(),
                slug_comparison_status=slug_comparison_status,
                frozen_slug=frozen_slug,
                status=status,
                reason=reason,
            )
        )
    return out


def summarize_slug_drift(rows: list[TargetPreflightRow]) -> tuple[SlugComparisonStatus, SlugDriftRows]:
    if not rows:
        return "NOT_AVAILABLE_IN_FROZEN_ARTIFACT", "NOT_APPLICABLE"
    status = rows[0].slug_comparison_status
    if status == "NOT_AVAILABLE_IN_FROZEN_ARTIFACT":
        return status, "NOT_APPLICABLE"
    return status, sum(1 for r in rows if r.slug_drift)


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
    """Full frozen cohort SHA256 in reason (must fit product_change_logs.reason VARCHAR(255))."""
    reason = (
        "Phase 2C manufacturer identity owner-frozen backfill; "
        f"cohort_sha256={cohort_sha256}"
    )
    if len(reason) > 255:
        raise ValueError(f"change-log reason length {len(reason)} exceeds VARCHAR(255)")
    if cohort_sha256 not in reason:
        raise ValueError("change-log reason missing full cohort SHA256")
    return reason


def change_log_reason_includes_full_sha(reason: str, cohort_sha256: str) -> bool:
    return cohort_sha256 in reason and len(reason) <= 255


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"
