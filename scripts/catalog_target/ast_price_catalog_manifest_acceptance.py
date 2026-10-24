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
OWNER_MANIFEST_BUNDLE_UPDATE_STAGE_PREFIX = "OWNER_MANIFEST_BUNDLE_UPDATE_"

BINDING_FIELDS_V1 = (
    "bundle_schema_version",
    "apply_cohort",
    "pricing_policy_id",
    "source_archive_sha256",
    "update_manifest_sha256",
    "create_manifest_sha256",
    "ledger_manifest_sha256",
    "expected_update_count",
    "expected_create_count",
)

BINDING_FIELDS_V2 = BINDING_FIELDS_V1 + (
    "update_stage",
    "master_update_manifest_sha256",
    "stage_manifest_sha256",
    "product_id_allowlist_sha256",
    "owner_accepted_git_commit_sha",
)

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


def binding_body_from_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    version = str(bundle.get("bundle_schema_version") or "1")
    fields = BINDING_FIELDS_V2 if version == "2" else BINDING_FIELDS_V1
    return {key: bundle[key] for key in fields if key in bundle}


def recompute_manifest_bundle_sha256(bundle: dict[str, Any]) -> str:
    return binding_digest(binding_body_from_bundle(bundle))


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


def build_update_stage_owner_bundle(
    *,
    update_stage: str,
    master_update_manifest_sha256: str,
    stage_manifest_sha256: str,
    ledger_manifest_sha256: str,
    expected_update_count: int,
    product_id_allowlist_sha256: str,
    owner_accepted_git_commit_sha: str = "",
) -> dict[str, Any]:
    binding = {
        "bundle_schema_version": "2",
        "apply_cohort": "update",
        "update_stage": update_stage,
        "pricing_policy_id": PRICING_POLICY_ID,
        "source_archive_sha256": SOURCE_ARCHIVE_SHA256,
        "update_manifest_sha256": stage_manifest_sha256,
        "master_update_manifest_sha256": master_update_manifest_sha256,
        "stage_manifest_sha256": stage_manifest_sha256,
        "create_manifest_sha256": MANIFEST_ABSENT,
        "ledger_manifest_sha256": ledger_manifest_sha256,
        "expected_update_count": expected_update_count,
        "expected_create_count": 0,
        "product_id_allowlist_sha256": product_id_allowlist_sha256,
        "owner_accepted_git_commit_sha": owner_accepted_git_commit_sha,
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
            "Stage-scoped UPDATE canary bundle. Owner must bind owner_accepted_git_commit_sha "
            "to the repository commit under review, then accept with OWNER_MANIFEST_ACCEPTED."
        ),
    }


def write_update_stage_owner_bundles(
    sanitized_dir: Path,
    *,
    ledger_manifest_sha256: str,
    canary_registry: dict[str, Any],
) -> dict[str, Path]:
    sanitized_dir.mkdir(parents=True, exist_ok=True)
    master = str(canary_registry.get("master_update_manifest_sha256") or "")
    paths: dict[str, Path] = {}
    for stage in ("stage1", "stage2", "stage3"):
        meta = canary_registry.get("stages", {}).get(stage) or {}
        bundle = build_update_stage_owner_bundle(
            update_stage=stage,
            master_update_manifest_sha256=master,
            stage_manifest_sha256=str(meta.get("manifest_sha256") or ""),
            ledger_manifest_sha256=ledger_manifest_sha256,
            expected_update_count=int(meta.get("row_count") or 0),
            product_id_allowlist_sha256=str(meta.get("product_id_allowlist_sha256") or ""),
        )
        path = sanitized_dir / f"{OWNER_MANIFEST_BUNDLE_UPDATE_STAGE_PREFIX}{stage.upper()}.json"
        path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        paths[stage] = path
    return paths


def load_owner_manifest_bundle(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ApplyAbort("missing_owner_manifest_bundle")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_bundle_path(
    audit_dir: Path,
    cohort: ApplyCohortName,
    *,
    update_stage: str = "full",
) -> Path:
    sanitized = audit_dir / "sanitized"
    if cohort == "update":
        stage = (update_stage or "full").strip().lower()
        if stage in {"stage1", "stage2", "stage3"}:
            return sanitized / f"{OWNER_MANIFEST_BUNDLE_UPDATE_STAGE_PREFIX}{stage.upper()}.json"
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
    confirm_git_commit_sha: str = "",
    confirm_update_stage: str = "full",
    confirm_stage_manifest_sha256: str = "",
    confirm_master_update_manifest_sha256: str = "",
    confirm_product_id_allowlist_sha256: str = "",
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
    recomputed = recompute_manifest_bundle_sha256(bundle)
    if recomputed != expected_bundle_sha:
        raise ApplyAbort("manifest_bundle_digest_recompute_mismatch")
    if confirm_manifest_bundle_sha256 != expected_bundle_sha:
        raise ApplyAbort("confirm_manifest_bundle_sha256_mismatch")

    schema = str(bundle.get("bundle_schema_version") or "1")
    stage = (confirm_update_stage or "full").strip().lower()
    if schema == "2":
        bound_stage = str(bundle.get("update_stage") or "").strip().lower()
        if bound_stage != stage:
            raise ApplyAbort("owner_bundle_update_stage_mismatch")
        if not confirm_git_commit_sha:
            raise ApplyAbort("missing_confirm_git_commit_sha")
        bound_commit = str(bundle.get("owner_accepted_git_commit_sha") or "").strip()
        if not bound_commit or bound_commit != confirm_git_commit_sha:
            raise ApplyAbort("owner_accepted_git_commit_sha_mismatch")
        if not confirm_stage_manifest_sha256:
            raise ApplyAbort("missing_confirm_stage_manifest_sha256")
        if str(bundle.get("stage_manifest_sha256") or "") != confirm_stage_manifest_sha256:
            raise ApplyAbort("confirm_stage_manifest_sha256_mismatch")
        if confirm_stage_manifest_sha256 != live_update_manifest_sha256:
            raise ApplyAbort("live_stage_manifest_sha256_mismatch")
        if not confirm_master_update_manifest_sha256:
            raise ApplyAbort("missing_confirm_master_update_manifest_sha256")
        if str(bundle.get("master_update_manifest_sha256") or "") != confirm_master_update_manifest_sha256:
            raise ApplyAbort("confirm_master_update_manifest_sha256_mismatch")
        if not confirm_product_id_allowlist_sha256:
            raise ApplyAbort("missing_confirm_product_id_allowlist_sha256")
        if str(bundle.get("product_id_allowlist_sha256") or "") != confirm_product_id_allowlist_sha256:
            raise ApplyAbort("confirm_product_id_allowlist_sha256_mismatch")

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
