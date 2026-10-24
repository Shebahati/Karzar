"""Production backup attestation gate (artifact SHA, not attestation-file checksum)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from catalog_target.sales_wave_apply import ApplyAbort

BACKUP_MAX_AGE_HOURS = 72

BACKUP_ATTESTATION_FILENAME = "PRODUCTION_BACKUP_ATTESTATION.json"
BACKUP_COMPLETION_COMPLETED = "COMPLETED"
RESTORE_VALIDATION_VERIFIED = "VERIFIED"
PLACEHOLDER_MARKERS = frozenset(
    {
        "PENDING_OWNER_PRODUCTION_BACKUP_ATTESTATION",
        "PENDING",
        "PLACEHOLDER",
    }
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_backup_attestation(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ApplyAbort("missing_production_backup_attestation")
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_iso8601(value: str) -> datetime:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    return datetime.fromisoformat(raw).astimezone(UTC)


def assert_production_backup_attestation_gate(
    *,
    attestation_path: Path,
    confirm_backup_artifact_sha256: str,
    verified_database_identity: str = "",
    reference_time: datetime | None = None,
) -> None:
    if not confirm_backup_artifact_sha256:
        raise ApplyAbort("missing_confirm_backup_artifact_sha256")

    doc = load_backup_attestation(attestation_path)
    if str(doc.get("backup_completion_status") or "") != BACKUP_COMPLETION_COMPLETED:
        raise ApplyAbort("backup_not_completed")

    if str(doc.get("restore_validation_status") or "") != RESTORE_VALIDATION_VERIFIED:
        raise ApplyAbort("restore_validation_not_verified")

    artifact_sha = str(doc.get("backup_artifact_sha256") or "").strip()
    if not artifact_sha or artifact_sha in PLACEHOLDER_MARKERS:
        raise ApplyAbort("backup_artifact_sha256_missing_or_placeholder")
    if artifact_sha != confirm_backup_artifact_sha256:
        raise ApplyAbort("confirm_backup_artifact_sha256_mismatch_attestation")

    location = str(doc.get("backup_artifact_location") or "").strip()
    if not location or any(marker in location.upper() for marker in PLACEHOLDER_MARKERS):
        raise ApplyAbort("backup_artifact_location_missing_or_placeholder")

    if not str(doc.get("backup_created_at") or "").strip():
        raise ApplyAbort("backup_created_at_missing")

    db_identity = str(doc.get("production_database_identity") or "").strip()
    if not db_identity:
        raise ApplyAbort("production_database_identity_missing_in_attestation")
    if not verified_database_identity:
        raise ApplyAbort("missing_verified_production_database_identity")
    if db_identity != verified_database_identity:
        raise ApplyAbort("verified_production_database_identity_mismatch_attestation")

    backup_created_raw = str(doc.get("backup_created_at") or "").strip()
    attestation_signed_raw = str(doc.get("attestation_signed_at") or "").strip()
    try:
        backup_created = _parse_iso8601(backup_created_raw)
        attestation_signed = _parse_iso8601(attestation_signed_raw)
    except ValueError:
        raise ApplyAbort("backup_timestamp_parse_failed") from None
    now = reference_time or datetime.now(UTC)
    if backup_created > attestation_signed:
        raise ApplyAbort("backup_created_after_attestation_signed")
    if now - backup_created > timedelta(hours=BACKUP_MAX_AGE_HOURS):
        raise ApplyAbort("backup_artifact_stale_relative_to_operation")

    if not str(doc.get("attested_by") or "").strip():
        raise ApplyAbort("backup_attested_by_missing")
    if not str(doc.get("attestation_signed_at") or "").strip():
        raise ApplyAbort("backup_attestation_signed_at_missing")

    artifact_path = Path(location)
    if not artifact_path.is_file():
        raise ApplyAbort("backup_artifact_file_not_found_at_declared_location")
    if "audit/" in location or "/Projects/Karzar" in location:
        raise ApplyAbort("backup_artifact_must_not_live_inside_repository_tree")

    actual = sha256_file(artifact_path)
    if actual != artifact_sha:
        raise ApplyAbort("backup_artifact_sha256_mismatch_on_disk")


def assert_backup_evidence_gate(*, confirm_backup_evidence_sha256: str, backup_evidence_path: Path) -> None:
    del confirm_backup_evidence_sha256
    del backup_evidence_path
    raise ApplyAbort("deprecated_backup_gate_use_production_backup_attestation")
