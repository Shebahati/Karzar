"""Owner-pinned manifest bundle (independent of operator-local CSV re-hash)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from catalog_target.ast_price_catalog_constants import PRICING_POLICY_ID, SOURCE_ARCHIVE_SHA256
from catalog_target.sales_wave_apply import ApplyAbort

OWNER_MANIFEST_BUNDLE_FILENAME = "OWNER_MANIFEST_BUNDLE.json"


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def manifest_bundle_digest(
    *,
    update_manifest_sha256: str,
    create_manifest_sha256: str,
    ledger_manifest_sha256: str,
) -> str:
    body = {
        "pricing_policy_id": PRICING_POLICY_ID,
        "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
        "update_manifest_sha256": update_manifest_sha256,
        "create_manifest_sha256": create_manifest_sha256,
        "ledger_manifest_sha256": ledger_manifest_sha256,
    }
    return hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


def build_owner_manifest_bundle(manifest_hashes: dict[str, str]) -> dict[str, Any]:
    update_sha = manifest_hashes.get("UPDATE_PRODUCTS.csv", "")
    create_sha = manifest_hashes.get("CREATE_PRODUCTS.csv", "")
    ledger_sha = manifest_hashes.get("SOURCE_ROW_LEDGER.csv", "")
    digest = manifest_bundle_digest(
        update_manifest_sha256=update_sha,
        create_manifest_sha256=create_sha,
        ledger_manifest_sha256=ledger_sha,
    )
    return {
        "pricing_policy_id": PRICING_POLICY_ID,
        "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
        "update_manifest_sha256": update_sha,
        "create_manifest_sha256": create_sha,
        "ledger_manifest_sha256": ledger_sha,
        "manifest_bundle_sha256": digest,
        "owner_acceptance_status": "PENDING_OWNER_SIGNATURE",
        "owner_acceptance_note": (
            "Confirm manifest_bundle_sha256 from this committed file; "
            "re-hashing local CSV files is not owner acceptance."
        ),
    }


def write_owner_manifest_bundle(audit_sanitized_dir: Path, manifest_hashes: dict[str, str]) -> Path:
    audit_sanitized_dir.mkdir(parents=True, exist_ok=True)
    path = audit_sanitized_dir / OWNER_MANIFEST_BUNDLE_FILENAME
    payload = build_owner_manifest_bundle(manifest_hashes)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_owner_manifest_bundle(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ApplyAbort("missing_owner_manifest_bundle")
    return json.loads(path.read_text(encoding="utf-8"))


def assert_owner_manifest_bundle_gate(
    *,
    confirm_manifest_bundle_sha256: str,
    bundle_path: Path,
) -> None:
    if not confirm_manifest_bundle_sha256:
        raise ApplyAbort("missing_confirm_manifest_bundle_sha256")
    bundle = load_owner_manifest_bundle(bundle_path)
    expected = str(bundle.get("manifest_bundle_sha256") or "")
    if confirm_manifest_bundle_sha256 != expected:
        raise ApplyAbort(
            f"confirm_manifest_bundle_sha256_mismatch:expected={expected}:got={confirm_manifest_bundle_sha256}"
        )


def assert_backup_evidence_gate(*, confirm_backup_evidence_sha256: str, backup_evidence_path: Path) -> None:
    if not confirm_backup_evidence_sha256:
        raise ApplyAbort("missing_confirm_backup_evidence_sha256")
    if not backup_evidence_path.is_file():
        raise ApplyAbort("missing_backup_evidence_file")
    h = hashlib.sha256()
    with backup_evidence_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    actual = h.hexdigest()
    if actual != confirm_backup_evidence_sha256:
        raise ApplyAbort(f"confirm_backup_evidence_sha256_mismatch:expected={actual}")
