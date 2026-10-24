"""Owner-pinned manifest acceptance (independent of operator-local CSV re-hash)."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

from catalog_target.ast_price_catalog_constants import PRICING_POLICY_ID, SOURCE_ARCHIVE_SHA256
from catalog_target.sales_wave_apply import ApplyAbort

OWNER_MANIFEST_BUNDLE_FILENAME = "OWNER_MANIFEST_BUNDLE.json"
OWNER_MANIFEST_BUNDLE_UPDATE_FILENAME = "OWNER_MANIFEST_BUNDLE_UPDATE.json"
OWNER_MANIFEST_BUNDLE_CREATE_FILENAME = "OWNER_MANIFEST_BUNDLE_CREATE.json"

MANIFEST_ABSENT = "MANIFEST_ABSENT"
OWNER_MANIFEST_ACCEPTED = "OWNER_MANIFEST_ACCEPTED"
OWNER_MANIFEST_PENDING = "PENDING_OWNER_SIGNATURE"

ApplyCohortName = Literal["update", "create", "both"]


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def manifest_file_sha256(path: Path) -> str:
    if not path.is_file():
        return MANIFEST_ABSENT
    if path.stat().st_size == 0:
        return MANIFEST_ABSENT
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8") as f:
            if not list(csv.DictReader(f)):
                return MANIFEST_ABSENT
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_create_manifest_sha256(digest: str | None) -> str:
    value = (digest or "").strip()
    if not value or value == MANIFEST_ABSENT:
        return MANIFEST_ABSENT
    return value


def binding_digest(body: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


def build_cohort_owner_bundle(
    *,
    apply_cohort: ApplyCohortName,
    manifest_hashes: dict[str, str],
    expected_update_count: int,
    expected_create_count: int,
) -> dict[str, Any]:
    update_sha = manifest_hashes.get("UPDATE_PRODUCTS.csv", MANIFEST_ABSENT)
    create_sha = normalize_create_manifest_sha256(manifest_hashes.get("CREATE_PRODUCTS.csv"))
    ledger_sha = manifest_hashes.get("SOURCE_ROW_LEDGER.csv", "")
    binding = {
        "bundle_schema_version": "1",
        "apply_cohort": apply_cohort,
        "pricing_policy_id": PRICING_POLICY_ID,
        "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
        "update_manifest_sha256": update_sha,
        "create_manifest_sha256": create_sha,
        "ledger_manifest_sha256": ledger_sha,
        "expected_update_count": expected_update_count,
        "expected_create_count": expected_create_count,
    }
    digest = binding_digest(binding)
    return {
        **binding,
        "manifest_bundle_sha256": digest,
        "owner_acceptance_status": OWNER_MANIFEST_PENDING,
        "owner_acceptance_id": "",
        "owner_acceptance_at": "",
        "owner_acceptance_by": "",
        "owner_acceptance_note": (
            "Owner must set owner_acceptance_status=OWNER_MANIFEST_ACCEPTED, "
            "owner_acceptance_id, owner_acceptance_at, owner_acceptance_by. "
            "Operator APPLY must pass --confirm-owner-acceptance-id matching owner_acceptance_id. "
            "Do not auto-accept during APPLY."
        ),
    }


def write_owner_manifest_bundles(
    audit_sanitized_dir: Path,
    manifest_hashes: dict[str, str],
    *,
    update_count: int,
    create_count: int,
) -> dict[str, Path]:
    audit_sanitized_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    update_bundle = build_cohort_owner_bundle(
        apply_cohort="update",
        manifest_hashes=manifest_hashes,
        expected_update_count=update_count,
        expected_create_count=0,
    )
    update_path = audit_sanitized_dir / OWNER_MANIFEST_BUNDLE_UPDATE_FILENAME
    update_path.write_text(json.dumps(update_bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["update"] = update_path

    create_bundle = build_cohort_owner_bundle(
        apply_cohort="create",
        manifest_hashes=manifest_hashes,
        expected_update_count=0,
        expected_create_count=create_count,
    )
    create_path = audit_sanitized_dir / OWNER_MANIFEST_BUNDLE_CREATE_FILENAME
    create_path.write_text(json.dumps(create_bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths["create"] = create_path

    # Legacy combined pointer (read-only summary for docs).
    legacy = {
        "update_bundle_file": OWNER_MANIFEST_BUNDLE_UPDATE_FILENAME,
        "create_bundle_file": OWNER_MANIFEST_BUNDLE_CREATE_FILENAME,
        "note": "Production APPLY uses cohort-specific bundle files only.",
    }
    (audit_sanitized_dir / OWNER_MANIFEST_BUNDLE_FILENAME).write_text(
        json.dumps(legacy, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    paths["legacy"] = audit_sanitized_dir / OWNER_MANIFEST_BUNDLE_FILENAME
    return paths


def load_owner_manifest_bundle(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ApplyAbort("missing_owner_manifest_bundle")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_bundle_path(audit_dir: Path, cohort: ApplyCohortName) -> Path:
    sanitized = audit_dir / "sanitized"
    if cohort == "update":
        return sanitized / OWNER_MANIFEST_BUNDLE_UPDATE_FILENAME
    if cohort == "create":
        return sanitized / OWNER_MANIFEST_BUNDLE_CREATE_FILENAME
    raise ApplyAbort("both_cohort_requires_separate_owner_bundles_use_update_or_create")


def assert_owner_manifest_acceptance_gate(
    *,
    cohort: ApplyCohortName,
    bundle_path: Path,
    confirm_manifest_bundle_sha256: str,
    confirm_owner_acceptance_id: str,
    live_update_manifest_sha256: str,
    live_create_manifest_sha256: str,
    live_update_count: int,
    live_create_count: int,
) -> None:
    if cohort == "both":
        raise ApplyAbort("invalid_apply_cohort_both_for_production_use_update_or_create")
    if not confirm_manifest_bundle_sha256:
        raise ApplyAbort("missing_confirm_manifest_bundle_sha256")
    if not confirm_owner_acceptance_id:
        raise ApplyAbort("missing_confirm_owner_acceptance_id")

    bundle = load_owner_manifest_bundle(bundle_path)
    status = str(bundle.get("owner_acceptance_status") or "").strip()
    if status != OWNER_MANIFEST_ACCEPTED:
        raise ApplyAbort(f"owner_manifest_not_accepted:{status}")

    acceptance_id = str(bundle.get("owner_acceptance_id") or "").strip()
    if not acceptance_id or acceptance_id != confirm_owner_acceptance_id:
        raise ApplyAbort("confirm_owner_acceptance_id_mismatch")

    if str(bundle.get("owner_acceptance_at") or "").strip() == "":
        raise ApplyAbort("owner_acceptance_at_missing")
    if str(bundle.get("owner_acceptance_by") or "").strip() == "":
        raise ApplyAbort("owner_acceptance_by_missing")

    if str(bundle.get("apply_cohort") or "") != cohort:
        raise ApplyAbort("owner_bundle_cohort_mismatch")

    if str(bundle.get("pricing_policy_id") or "") != PRICING_POLICY_ID:
        raise ApplyAbort("owner_bundle_pricing_policy_mismatch")
    if str(bundle.get("source_archive_sha256") or "") != SOURCE_ARCHIVE_SHA256:
        raise ApplyAbort("owner_bundle_source_archive_mismatch")

    expected_bundle_sha = str(bundle.get("manifest_bundle_sha256") or "")
    if confirm_manifest_bundle_sha256 != expected_bundle_sha:
        raise ApplyAbort("confirm_manifest_bundle_sha256_mismatch")

    bound_update = str(bundle.get("update_manifest_sha256") or "")
    bound_create = normalize_create_manifest_sha256(str(bundle.get("create_manifest_sha256") or ""))
    if bound_update != live_update_manifest_sha256:
        raise ApplyAbort("live_update_manifest_sha256_mismatch_owner_bundle")
    if bound_create != normalize_create_manifest_sha256(live_create_manifest_sha256):
        raise ApplyAbort("live_create_manifest_sha256_mismatch_owner_bundle")

    if int(bundle.get("expected_update_count", -1)) != live_update_count:
        raise ApplyAbort("live_update_count_mismatch_owner_bundle")
    if int(bundle.get("expected_create_count", -1)) != live_create_count:
        raise ApplyAbort("live_create_count_mismatch_owner_bundle")


# Backward-compatible alias
def assert_owner_manifest_bundle_gate(
    *,
    confirm_manifest_bundle_sha256: str,
    bundle_path: Path,
) -> None:
    raise ApplyAbort("deprecated_gate_use_assert_owner_manifest_acceptance_gate")
