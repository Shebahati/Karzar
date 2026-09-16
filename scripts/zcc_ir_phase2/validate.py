"""READ-ONLY manifest validator (content vs commerce layers)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from zcc_ir_phase2.canonical_hash import canonical_import_plan_sha256
from zcc_ir_phase2.collision_clusters import build_logical_collision_clusters, index_to_cluster_id
from zcc_ir_phase2.collision_policy import summarize_collision_impact
from zcc_ir_phase2.manifest import ALLOWED_OPERATIONS, FORBIDDEN_OPERATIONS, manifest_sha256

SKU_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-/]{0,120}$")


class ManifestValidationError(Exception):
    pass


@dataclass
class ValidationDiagnostic:
    """One validator finding; multiple diagnostics may reference the same source row."""

    diagnostic_id: str
    error_type: str
    layer: str  # content | commerce
    source_url: str | None
    manufacturer_identity: str | None
    proposed_target_sku: str | None
    collision_group: str | None
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "diagnostic_id": self.diagnostic_id,
            "error_type": self.error_type,
            "layer": self.layer,
            "source_url": self.source_url,
            "manufacturer_identity": self.manufacturer_identity,
            "proposed_target_sku": self.proposed_target_sku,
            "collision_group": self.collision_group,
            "message": self.message,
        }


@dataclass
class ManifestValidationResult:
    content_errors: list[str] = field(default_factory=list)
    commerce_errors: list[str] = field(default_factory=list)
    diagnostics: list[ValidationDiagnostic] = field(default_factory=list)
    logical_collision_clusters: list[Any] = field(default_factory=list)
    collision_impact: Any | None = None

    @property
    def CONTENT_PLAN_VALID(self) -> bool:
        return not self.content_errors

    @property
    def CONTENT_SOURCE_QUALITY_VALID(self) -> bool:
        if self.collision_impact is None:
            return self.LOGICAL_COLLISION_GROUP_COUNT == 0
        return self.collision_impact.CONTENT_SOURCE_QUALITY_VALID

    @property
    def CONTENT_MUTATION_PLAN_VALID(self) -> bool:
        if self.collision_impact is None:
            return True
        return self.collision_impact.CONTENT_MUTATION_PLAN_VALID

    @property
    def MUTATION_BLOCKING_COLLISION_GROUPS(self) -> int:
        if self.collision_impact is None:
            return 0
        return self.collision_impact.MUTATION_BLOCKING_COLLISION_GROUPS

    @property
    def MUTATION_BLOCKING_AFFECTED_ROWS(self) -> int:
        if self.collision_impact is None:
            return 0
        return self.collision_impact.MUTATION_BLOCKING_AFFECTED_ROWS

    @property
    def COMMERCE_PLAN_VALID(self) -> bool:
        return not self.commerce_errors

    @property
    def CONTENT_BLOCKING_ERROR_COUNT(self) -> int:
        return sum(1 for d in self.diagnostics if d.layer == "content")

    @property
    def COMMERCE_BLOCKING_ERROR_COUNT(self) -> int:
        return sum(1 for d in self.diagnostics if d.layer == "commerce")

    @property
    def CONTENT_DIAGNOSTIC_ROW_COUNT(self) -> int:
        return len({d.source_url for d in self.diagnostics if d.layer == "content" and d.source_url})

    @property
    def CONTENT_COLLISION_AFFECTED_ROW_COUNT(self) -> int:
        urls: set[str] = set()
        for cluster in self.logical_collision_clusters:
            urls.update(cluster.source_urls)
        return len(urls)

    @property
    def LOGICAL_COLLISION_GROUP_COUNT(self) -> int:
        return len(self.logical_collision_clusters)

    @property
    def COLLISION_AFFECTED_SOURCE_ROWS(self) -> int:
        return self.CONTENT_COLLISION_AFFECTED_ROW_COUNT

    @property
    def DUPLICATE_IDENTITY_DIAGNOSTICS(self) -> int:
        return sum(1 for d in self.diagnostics if d.error_type == "DUPLICATE_MANUFACTURER_IDENTITY")

    @property
    def DUPLICATE_SKU_DIAGNOSTICS(self) -> int:
        return sum(1 for d in self.diagnostics if d.error_type == "DUPLICATE_TARGET_SKU")

    def all_errors(self) -> list[str]:
        return [*self.content_errors, *self.commerce_errors]

    def summary_dict(self, entries: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        blocking_urls = sorted(
            {d.source_url for d in self.diagnostics if d.layer == "content" and d.source_url}
        )
        target_skus = sorted(
            {
                d.proposed_target_sku
                for d in self.diagnostics
                if d.error_type == "DUPLICATE_TARGET_SKU" and d.proposed_target_sku
            }
        )
        logical_clusters = [
            {
                "cluster_id": c.cluster_id,
                "source_urls": list(c.source_urls),
                "reasons": list(c.reasons),
                "size": c.size,
            }
            for c in self.logical_collision_clusters
        ]
        collision_extra = (
            self.collision_impact.as_dict(entries)
            if self.collision_impact is not None and entries is not None
            else {}
        )
        return {
            "CONTENT_PLAN_VALID": self.CONTENT_PLAN_VALID,
            "CONTENT_SOURCE_QUALITY_VALID": self.CONTENT_SOURCE_QUALITY_VALID,
            "CONTENT_MUTATION_PLAN_VALID": self.CONTENT_MUTATION_PLAN_VALID,
            "COMMERCE_PLAN_VALID": self.COMMERCE_PLAN_VALID,
            "CONTENT_BLOCKING_ERROR_COUNT": self.CONTENT_BLOCKING_ERROR_COUNT,
            "COMMERCE_BLOCKING_ERROR_COUNT": self.COMMERCE_BLOCKING_ERROR_COUNT,
            "CONTENT_DIAGNOSTIC_ROW_COUNT": self.CONTENT_DIAGNOSTIC_ROW_COUNT,
            "CONTENT_COLLISION_AFFECTED_ROW_COUNT": self.CONTENT_COLLISION_AFFECTED_ROW_COUNT,
            "LOGICAL_COLLISION_GROUP_COUNT": self.LOGICAL_COLLISION_GROUP_COUNT,
            "COLLISION_AFFECTED_SOURCE_ROWS": self.COLLISION_AFFECTED_SOURCE_ROWS,
            "DUPLICATE_IDENTITY_DIAGNOSTICS": self.DUPLICATE_IDENTITY_DIAGNOSTICS,
            "DUPLICATE_SKU_DIAGNOSTICS": self.DUPLICATE_SKU_DIAGNOSTICS,
            "TOTAL_VALIDATOR_DIAGNOSTICS": len(self.diagnostics),
            "CONTENT_DIAGNOSTIC_SOURCE_ROWS": len(blocking_urls),
            "UNIQUE_BLOCKING_TARGET_IDENTITIES": len(
                {
                    d.manufacturer_identity
                    for d in self.diagnostics
                    if d.error_type == "DUPLICATE_MANUFACTURER_IDENTITY" and d.manufacturer_identity
                }
            ),
            "UNIQUE_BLOCKING_TARGET_SKUS": len(target_skus),
            "logical_collision_clusters": logical_clusters,
            "diagnostics": [d.as_dict() for d in self.diagnostics],
            **collision_extra,
        }


def _load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ManifestValidationError("manifest must be a JSON object")
    return data


def _mfg_key(entry: dict[str, Any]) -> tuple[str, str] | None:
    identity = entry.get("source_identity") or {}
    brand = identity.get("brand")
    mfg = identity.get("manufacturer_code") or ""
    if brand and mfg:
        return str(brand), str(mfg)
    return None


def _sku_proposal(entry: dict[str, Any]) -> str | None:
    planned = entry.get("planned_fields") or {}
    sku = (planned.get("identity") or {}).get("sku_proposal")
    return str(sku) if sku else None


def validate_manifest_layers(path: Path) -> ManifestValidationResult:
    """Validate manifest; split factual content planning from commerce sellability."""
    result = ManifestValidationResult()
    data = _load_manifest(path)
    entries = data.get("entries")
    if not isinstance(entries, list):
        result.content_errors.append("entries must be a list")
        result.diagnostics.append(
            ValidationDiagnostic(
                diagnostic_id="manifest-entries-invalid",
                error_type="MANIFEST_STRUCTURE",
                layer="content",
                source_url=None,
                manufacturer_identity=None,
                proposed_target_sku=None,
                collision_group=None,
                message="entries must be a list",
            )
        )
        return result

    result.logical_collision_clusters = build_logical_collision_clusters(entries)
    result.collision_impact = summarize_collision_impact(entries)
    collision_by_index = index_to_cluster_id(result.logical_collision_clusters)
    seen_skus: set[str] = set()
    seen_identity: set[tuple[str, str]] = set()
    diag_seq = 0

    def add_diag(
        *,
        layer: str,
        error_type: str,
        message: str,
        entry: dict[str, Any] | None,
        index: int | None,
        collision_group: str | None = None,
    ) -> None:
        nonlocal diag_seq
        diag_seq += 1
        url = (entry or {}).get("source_url") if entry else None
        ident = (entry or {}).get("source_identity") or {} if entry else {}
        mfg = ident.get("manufacturer_code")
        brand = ident.get("brand")
        mfg_label = f"{brand}|{mfg}" if brand and mfg else None
        sku = _sku_proposal(entry) if entry else None
        group = collision_group
        if entry is not None and index is not None:
            group = group or collision_by_index.get(index)
        diagnostic = ValidationDiagnostic(
            diagnostic_id=f"diag-{diag_seq:04d}",
            error_type=error_type,
            layer=layer,
            source_url=str(url) if url else None,
            manufacturer_identity=mfg_label,
            proposed_target_sku=sku,
            collision_group=group,
            message=message,
        )
        result.diagnostics.append(diagnostic)
        if layer == "content":
            result.content_errors.append(message)
        else:
            result.commerce_errors.append(message)

    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            add_diag(
                layer="content",
                error_type="ENTRY_STRUCTURE",
                message=f"entry[{i}] not an object",
                entry=None,
                index=i,
            )
            continue
        op = entry.get("operation")
        if op in FORBIDDEN_OPERATIONS:
            add_diag(
                layer="content",
                error_type="FORBIDDEN_OPERATION",
                message=f"entry[{i}] forbidden operation {op}",
                entry=entry,
                index=i,
            )
        if op not in ALLOWED_OPERATIONS:
            add_diag(
                layer="content",
                error_type="UNSUPPORTED_OPERATION",
                message=f"entry[{i}] unsupported operation {op}",
                entry=entry,
                index=i,
            )
        if not entry.get("source_url"):
            add_diag(
                layer="content",
                error_type="MISSING_PROVENANCE",
                message=f"entry[{i}] missing source_url provenance",
                entry=entry,
                index=i,
            )
        identity = entry.get("source_identity") or {}
        brand = identity.get("brand")
        if op == "CREATE_PLAN" and not brand:
            add_diag(
                layer="content",
                error_type="UNRESOLVED_BRAND",
                message=f"entry[{i}] CREATE_PLAN missing brand",
                entry=entry,
                index=i,
            )
        mfg = identity.get("manufacturer_code") or ""
        if brand and mfg:
            key = (str(brand), str(mfg))
            if key in seen_identity:
                add_diag(
                    layer="content",
                    error_type="DUPLICATE_MANUFACTURER_IDENTITY",
                    message=f"duplicate manufacturer identity {key}",
                    entry=entry,
                    index=i,
                )
            seen_identity.add(key)
        planned = entry.get("planned_fields") or {}
        identity_block = planned.get("identity") or {}
        sku = identity_block.get("sku_proposal")
        if sku:
            if sku in seen_skus:
                add_diag(
                    layer="content",
                    error_type="DUPLICATE_TARGET_SKU",
                    message=f"duplicate target SKU {sku}",
                    entry=entry,
                    index=i,
                )
            seen_skus.add(str(sku))
            if not SKU_RE.match(str(sku)):
                add_diag(
                    layer="content",
                    error_type="MALFORMED_TARGET_SKU",
                    message=f"malformed sku_proposal {sku}",
                    entry=entry,
                    index=i,
                )
        cat_id = entry.get("category_id")
        if op == "CREATE_PLAN" and not cat_id:
            add_diag(
                layer="content",
                error_type="UNRESOLVED_CATEGORY",
                message=f"entry[{i}] CREATE_PLAN missing category_id",
                entry=entry,
                index=i,
            )
        images = (planned.get("images") or {}) if planned else {}
        main = images.get("main_image_source_url")
        if main:
            parsed = urlparse(str(main))
            if parsed.scheme not in {"http", "https"}:
                add_diag(
                    layer="content",
                    error_type="MALFORMED_IMAGE_URL",
                    message=f"entry[{i}] malformed image URL",
                    entry=entry,
                    index=i,
                )
        if op != "HOLD" and str(entry.get("primary_state", "")).startswith("HOLD_"):
            add_diag(
                layer="content",
                error_type="OPERATION_STATE_MISMATCH",
                message=f"entry[{i}] HOLD state with non-HOLD operation",
                entry=entry,
                index=i,
            )

        commerce = (planned.get("commerce_observations") or {}) if planned else {}
        price = commerce.get("observed_price")
        if price is not None and str(price) in {"0", "0.0", ""}:
            add_diag(
                layer="commerce",
                error_type="COMMERCE_INVALID_PRICE",
                message=f"entry[{i}] COMMERCE_INVALID: price=0 must not be sellable",
                entry=entry,
                index=i,
            )

    if not data.get("karzar_snapshot_sha256"):
        add_diag(
            layer="content",
            error_type="MISSING_SNAPSHOT_SHA",
            message="missing karzar_snapshot_sha256 (required for approval binding)",
            entry=None,
            index=None,
        )

    canonical = data.get("CANONICAL_IMPORT_PLAN_SHA256")
    if canonical:
        expected = canonical_import_plan_sha256(data)
        if canonical != expected:
            add_diag(
                layer="content",
                error_type="CANONICAL_HASH_MISMATCH",
                message="CANONICAL_IMPORT_PLAN_SHA256 mismatch (manifest mutated)",
                entry=None,
                index=None,
            )
    else:
        add_diag(
            layer="content",
            error_type="MISSING_CANONICAL_HASH",
            message="missing CANONICAL_IMPORT_PLAN_SHA256 (owner approval identity)",
            entry=None,
            index=None,
        )

    legacy = data.get("IMPORT_MANIFEST_SHA256")
    if legacy:
        clone = dict(data)
        clone.pop("IMPORT_MANIFEST_SHA256", None)
        if legacy != manifest_sha256(clone):
            add_diag(
                layer="content",
                error_type="LEGACY_HASH_MISMATCH",
                message="IMPORT_MANIFEST_SHA256 mismatch (manifest mutated)",
                entry=None,
                index=None,
            )

    return result


def validate_manifest(path: Path) -> list[str]:
    """Return combined errors (legacy CLI). Prefer validate_manifest_layers for reporting."""
    return validate_manifest_layers(path).all_errors()
