"""READ-ONLY manifest validator."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from zcc_ir_phase2.manifest import ALLOWED_OPERATIONS, FORBIDDEN_OPERATIONS

SKU_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-/]{0,120}$")


class ManifestValidationError(Exception):
    pass


def _load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ManifestValidationError("manifest must be a JSON object")
    return data


def validate_manifest(path: Path) -> list[str]:
    """Return list of errors (empty if valid)."""
    errors: list[str] = []
    data = _load_manifest(path)
    entries = data.get("entries")
    if not isinstance(entries, list):
        errors.append("entries must be a list")
        return errors
    seen_skus: set[str] = set()
    seen_identity: set[tuple[str, str]] = set()
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry[{i}] not an object")
            continue
        op = entry.get("operation")
        if op in FORBIDDEN_OPERATIONS:
            errors.append(f"entry[{i}] forbidden operation {op}")
        if op not in ALLOWED_OPERATIONS:
            errors.append(f"entry[{i}] unsupported operation {op}")
        if op == "HOLD" and entry.get("primary_state", "").startswith("HOLD_") is False:
            pass
        if not entry.get("source_url"):
            errors.append(f"entry[{i}] missing source_url provenance")
        identity = entry.get("source_identity") or {}
        brand = identity.get("brand")
        if op == "CREATE_PLAN" and not brand:
            errors.append(f"entry[{i}] CREATE_PLAN missing brand")
        mfg = identity.get("manufacturer_code") or ""
        if brand and mfg:
            key = (str(brand), str(mfg))
            if key in seen_identity:
                errors.append(f"duplicate manufacturer identity {key}")
            seen_identity.add(key)
        planned = entry.get("planned_fields") or {}
        identity_block = planned.get("identity") or {}
        sku = identity_block.get("sku_proposal")
        if sku:
            if sku in seen_skus:
                errors.append(f"duplicate target SKU {sku}")
            seen_skus.add(str(sku))
            if not SKU_RE.match(str(sku)):
                errors.append(f"malformed sku_proposal {sku}")
        cat_id = entry.get("category_id")
        if op == "CREATE_PLAN" and not cat_id:
            errors.append(f"entry[{i}] CREATE_PLAN missing category_id")
        commerce = (planned.get("commerce_observations") or {}) if planned else {}
        price = commerce.get("observed_price")
        if price is not None and str(price) in {"0", "0.0", ""}:
            errors.append(f"entry[{i}] price=0 must not be sellable")
        images = (planned.get("images") or {}) if planned else {}
        main = images.get("main_image_source_url")
        if main:
            parsed = urlparse(str(main))
            if parsed.scheme not in {"http", "https"}:
                errors.append(f"entry[{i}] malformed image URL")
        if op != "HOLD" and entry.get("primary_state", "").startswith("HOLD_"):
            errors.append(f"entry[{i}] HOLD state with non-HOLD operation")
    if not data.get("IMPORT_MANIFEST_SHA256"):
        errors.append("missing IMPORT_MANIFEST_SHA256")
    elif data.get("IMPORT_MANIFEST_SHA256") != _expected_sha(data):
        errors.append("IMPORT_MANIFEST_SHA256 mismatch (manifest mutated)")
    return errors


def _expected_sha(data: dict[str, Any]) -> str:
    from zcc_ir_phase2.manifest import manifest_sha256

    clone = dict(data)
    clone.pop("IMPORT_MANIFEST_SHA256", None)
    return manifest_sha256(clone)
