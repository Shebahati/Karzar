#!/usr/bin/env python3
"""Ticket #344 Category B writer for the pinned 309-SKU ZCC draft input.

Default mode is offline plan generation from the Git-tracked execution input.
``--precheck-only`` performs authenticated destination GETs only and writes an
exclusive audit with ``writes_performed=false``. ``--apply`` is fail-closed:
production URL, ADR-012 env vars, backup artifact, deployed Git SHA, confirmed
plan hash/count, admin token, and an exclusive audit directory are all
required. It creates inactive unavailable drafts only. ``--precheck-only`` and
``--apply`` are mutually exclusive.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib import error, parse, request

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from ingestion_boundary import (  # noqa: E402
    ALLOW_ENV,
    CATEGORY_ENV,
    assert_destination_allowed,
    is_production_base,
)
from zcc_ir_category_b_execution_input import (  # noqa: E402
    DEFAULT_ALLOWLIST,
    DEFAULT_EXECUTION_INPUT,
    EXPECTED_COUNT,
    PINNED_ALLOWLIST_SHA256,
    PINNED_EXECUTION_INPUT_SHA256,
    PINNED_SOURCE_SHA256,
    TICKET,
    bind_allowlist,
    load_execution_input,
)
from zcc_ir_category_b_preflight import sha256  # noqa: E402

ALLOWED_PAYLOAD_KEYS = frozenset(
    {
        "sku",
        "name",
        "is_active",
        "is_available",
        "base_price",
        "stock_quantity",
        "specifications",
        "brand_id",
        "category_id",
    }
)
FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "original_price",
        "images",
        "thumbnail",
        "pdf_catalog_url",
        "is_published",
        "published",
    }
)
BACKUP_NAME = re.compile(r"^karzar_\d{8}_\d{6}\.sql\.gz$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
RECONCILIATION_STATE = "MANUAL_RECONCILIATION_OR_DB_ROLLBACK_REQUIRED"
EXECUTION_INPUT_LOGICAL_ID = (
    "docs/operations/pipeline/zcc-category-b-ticket-344-execution-input.json"
)
ADMIN_TOKEN_ENV = "KARZAR_CATEGORY_B_ADMIN_TOKEN"
SECRET_PATTERNS = (
    re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+\S+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-+=/]+"),
    re.compile(r"(?i)KARZAR_CATEGORY_B_ADMIN_TOKEN\s*[:=]\s*\S+"),
)


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def draft_payload(record: dict) -> dict:
    payload = {
        "sku": record["sku"],
        "name": record["name"],
        "is_active": False,
        "is_available": False,
        "base_price": None,
        "stock_quantity": 0,
        "specifications": {
            "source_attributes": record.get("source_attributes") or {},
            "source_url": record["source_url"],
            "source_timestamp": record.get("source_timestamp"),
        },
    }
    forbidden = set(payload) & FORBIDDEN_PAYLOAD_KEYS
    extra = set(payload) - ALLOWED_PAYLOAD_KEYS
    if forbidden or extra:
        raise ValueError("draft payload contains forbidden commerce or publication fields")
    if payload["is_active"] or payload["is_available"] or payload["base_price"] is not None:
        raise ValueError("draft payload must omit commerce publication")
    if payload["stock_quantity"] != 0:
        raise ValueError("draft payload stock_quantity must be 0")
    return payload


def build_draft_plan(
    execution_input: Path,
    allowlist: Path,
    source_sha: str,
    allowlist_sha: str,
) -> dict:
    if source_sha != PINNED_SOURCE_SHA256:
        raise ValueError("source SHA-256 mismatch")
    if allowlist_sha != PINNED_ALLOWLIST_SHA256:
        raise ValueError("allowlist SHA-256 mismatch")
    document = load_execution_input(execution_input)
    bind_allowlist(document, allowlist)
    if document["source_sha256"] != source_sha or document["allowlist_sha256"] != allowlist_sha:
        raise ValueError("execution input hashes do not match pinned values")
    file_digest = sha256(execution_input)
    if file_digest != PINNED_EXECUTION_INPUT_SHA256:
        raise ValueError("execution input SHA-256 mismatch")
    entries = []
    for record in document["records"]:
        entries.append(
            {
                "sku": record["sku"],
                "brand": record["brand"],
                "category_id": record["category_id"],
                "source_url": record["source_url"],
                "payload": draft_payload(record),
            }
        )
    if len(entries) != EXPECTED_COUNT or len({entry["sku"] for entry in entries}) != EXPECTED_COUNT:
        raise ValueError("Category B scope must be exactly 309 unique SKUs")
    return {
        "ticket": TICKET,
        "mode": "CATEGORY_B_INACTIVE_DRAFT_ONLY",
        "source_sha256": source_sha,
        "allowlist_sha256": allowlist_sha,
        "execution_input": EXECUTION_INPUT_LOGICAL_ID,
        "execution_input_sha256": PINNED_EXECUTION_INPUT_SHA256,
        "count": len(entries),
        "entries": entries,
        "commerce_fields": "OMITTED",
        "writes_performed": False,
    }


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError("Redirect refused; production destination must remain explicit")


class UrlTransport:
    """Authenticated HTTP transport. Mutations are allowed unless subclassed."""

    allow_mutations = True

    def __init__(self, api_base: str, token: str) -> None:
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.posts = 0
        self.gets = 0
        self.sku_lookups = 0
        self.methods_called: list[str] = []

    def _call(self, method: str, path: str, data: object | None = None) -> object:
        method_upper = method.upper()
        self.methods_called.append(method_upper)
        if method_upper != "GET":
            if not self.allow_mutations:
                raise RuntimeError(
                    f"read-only transport forbids {method_upper} before network dispatch"
                )
            if method_upper not in {"POST", "PUT", "PATCH", "DELETE"}:
                raise RuntimeError(f"unsupported HTTP method: {method_upper}")
        elif data is not None:
            raise RuntimeError("GET requests must not carry a body")
        if data is not None and not self.allow_mutations:
            raise RuntimeError("read-only transport forbids request bodies")
        body = None if data is None else json.dumps(data).encode()
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
        try:
            with opener.open(
                request.Request(
                    self.api_base + path, data=body, headers=headers, method=method_upper
                ),
                timeout=30,
            ) as response:
                return json.load(response)
        except error.HTTPError as exc:
            detail = redact_secrets(exc.read(500).decode("utf-8", errors="replace"))
            raise RuntimeError(
                f"API {method_upper} {path} failed HTTP {exc.code}: {detail}"
            ) from None

    def get(self, path: str) -> object:
        self.gets += 1
        return self._call("GET", path)

    def get_product_by_sku(self, sku: str) -> dict | None:
        self.sku_lookups += 1
        path = "/products/sku/" + parse.quote(sku, safe="")
        try:
            payload = self._call("GET", path)
        except RuntimeError as exc:
            if "HTTP 404" in str(exc):
                return None
            raise
        if not isinstance(payload, dict):
            raise RuntimeError("unexpected product-by-SKU response")
        return payload

    def post_product(self, payload: dict) -> dict:
        if not self.allow_mutations:
            raise RuntimeError("read-only transport forbids POST before network dispatch")
        self.posts += 1
        created = self._call("POST", "/products/", payload)
        if not isinstance(created, dict):
            raise RuntimeError("unexpected product create response")
        return created


class ReadOnlyUrlTransport(UrlTransport):
    """Hard GET-only transport for authenticated destination prechecks."""

    allow_mutations = False

    def post_product(self, payload: dict) -> dict:
        raise RuntimeError("read-only transport forbids POST before network dispatch")


@dataclass(frozen=True)
class DestinationPrecheckResult:
    brand_ids: dict[str, int]
    sku_checked: int
    brands_required: int
    categories_required: int
    brands_resolved: int
    categories_selectable_matched: int


def data_list(value: object, label: str) -> list[dict]:
    if not isinstance(value, dict):
        raise RuntimeError(f"unexpected {label} response shape")
    values = value.get("data")
    if not isinstance(values, list):
        raise RuntimeError(f"unexpected {label} response")
    return values


def brand_match_keys(label: str) -> frozenset[str]:
    """Conservative destination brand keys: full trimmed label + ``|`` segments.

    Keys are Unicode-casefolded after trim. No punctuation stripping, fuzzy
    matching, transliteration, substring matching, or SKU-prefix guessing.
    """
    text = str(label or "").strip()
    if not text:
        return frozenset()
    keys = {text.casefold()}
    for segment in text.split("|"):
        part = segment.strip()
        if part:
            keys.add(part.casefold())
    return frozenset(keys)


def unique_brand_ids(brands: list[dict], required: set[str]) -> dict[str, int]:
    """Resolve required brand labels to destination IDs via conservative keys.

    A required label matches when its casefolded trimmed form equals any
    destination key from the full bilingual label or an exact ``|`` segment.
    Zero matches → missing; multiple distinct destination IDs → ambiguous.
    """
    key_to_ids: dict[str, set[int]] = {}
    for item in brands:
        if not isinstance(item, dict):
            raise RuntimeError("unexpected brands response shape")
        name = str(item.get("name") or "")
        brand_id = item.get("id")
        if not isinstance(brand_id, int):
            continue
        for key in brand_match_keys(name):
            key_to_ids.setdefault(key, set()).add(brand_id)
    resolved: dict[str, int] = {}
    for name in sorted(required):
        key = str(name or "").strip().casefold()
        if not key:
            raise RuntimeError(f"approved brand missing on destination: {name}")
        ids = sorted(key_to_ids.get(key) or [])
        if len(ids) == 0:
            raise RuntimeError(f"approved brand missing on destination: {name}")
        if len(ids) != 1:
            raise RuntimeError(f"approved brand is not unique on destination: {name}")
        resolved[name] = ids[0]
    return resolved


def selectable_category_ids(categories: list[dict]) -> set[int]:
    selectable: set[int] = set()
    for item in categories:
        if not isinstance(item, dict):
            raise RuntimeError("unexpected categories response shape")
        if item.get("is_selectable") and isinstance(item.get("id"), int):
            selectable.add(item["id"])
    return selectable


def validate_backup(backup: Path, expected_sha256: str) -> None:
    resolved = backup.resolve()
    if "backups" not in resolved.parts:
        raise RuntimeError("backup path must be under a backups/ directory")
    if not BACKUP_NAME.fullmatch(resolved.name):
        raise RuntimeError("backup filename must match karzar_YYYYMMDD_HHMMSS.sql.gz")
    if not resolved.is_file() or resolved.stat().st_size == 0:
        raise RuntimeError("backup artifact must be a non-empty .sql.gz file")
    if sha256(resolved) != expected_sha256:
        raise RuntimeError("backup SHA-256 mismatch")


def inactive_zero(value: object) -> bool:
    if value in (None, "", 0, 0.0, "0", "0.0", "0.00"):
        return True
    try:
        return Decimal(str(value)) == 0
    except Exception:
        return False


def assert_created_postcondition(created: dict, payload: dict) -> None:
    if created.get("sku") != payload["sku"]:
        raise RuntimeError(f"postcondition failed for {payload['sku']}: sku")
    if created.get("is_active") is not False:
        raise RuntimeError(f"postcondition failed for {payload['sku']}: is_active")
    if created.get("is_available") is not False:
        raise RuntimeError(f"postcondition failed for {payload['sku']}: is_available")
    if created.get("base_price") not in (None, ""):
        raise RuntimeError(f"postcondition failed for {payload['sku']}: base_price")
    if not inactive_zero(created.get("stock_quantity", "0")):
        raise RuntimeError(f"postcondition failed for {payload['sku']}: stock_quantity")
    if created.get("images"):
        raise RuntimeError(f"postcondition failed for {payload['sku']}: images")
    if created.get("thumbnail"):
        raise RuntimeError(f"postcondition failed for {payload['sku']}: thumbnail")


def assert_plan_scope(plan: dict) -> None:
    if plan.get("ticket") != TICKET or plan.get("count") != EXPECTED_COUNT:
        raise RuntimeError("apply plan is not the approved 309-SKU ticket 344 scope")
    entries = plan.get("entries")
    if not isinstance(entries, list) or len(entries) != EXPECTED_COUNT:
        raise RuntimeError("Category B scope must be exactly 309 unique SKUs")
    skus = [entry.get("sku") for entry in entries]
    if len(set(skus)) != EXPECTED_COUNT or any(not sku for sku in skus):
        raise RuntimeError("Category B scope must be exactly 309 unique SKUs")


def run_destination_precheck(plan: dict, transport: UrlTransport) -> DestinationPrecheckResult:
    """Shared destination validation used by --precheck-only and --apply.

    Completes all brand/category/SKU checks before returning. Never POSTs.
    """
    assert_plan_scope(plan)
    if getattr(transport, "posts", 0):
        raise RuntimeError("destination prechecks must run before any POST")
    brands = data_list(transport.get("/brands/"), "brands")
    categories = data_list(transport.get("/categories/"), "categories")
    required_brands = {entry["brand"] for entry in plan["entries"]}
    required_categories = {entry["category_id"] for entry in plan["entries"]}
    brand_ids = unique_brand_ids(brands, required_brands)
    selectable = selectable_category_ids(categories)
    missing_categories = sorted(required_categories - selectable)
    if missing_categories:
        raise RuntimeError(
            "allowlist category is missing or not selectable: "
            + ",".join(map(str, missing_categories))
        )
    existing = []
    for entry in plan["entries"]:
        found = transport.get_product_by_sku(entry["sku"])
        if found is not None:
            existing.append(entry["sku"])
    sku_checked = int(getattr(transport, "sku_lookups", len(plan["entries"])))
    if sku_checked != len(plan["entries"]):
        raise RuntimeError("destination SKU precheck did not cover every plan entry")
    if existing:
        raise RuntimeError("destination SKU already exists: " + ",".join(existing[:10]))
    if getattr(transport, "posts", 0):
        raise RuntimeError("POST occurred during destination prechecks")
    methods = getattr(transport, "methods_called", [])
    if any(method != "GET" for method in methods):
        raise RuntimeError("non-GET method observed during destination prechecks")
    return DestinationPrecheckResult(
        brand_ids=brand_ids,
        sku_checked=sku_checked,
        brands_required=len(required_brands),
        categories_required=len(required_categories),
        brands_resolved=len(brand_ids),
        categories_selectable_matched=len(required_categories),
    )


def _audit_record(audit, event: dict) -> None:
    safe = json.loads(redact_secrets(json.dumps(event, ensure_ascii=False)))
    audit.write(json.dumps(safe, ensure_ascii=False) + "\n")
    audit.flush()
    os.fsync(audit.fileno())


def write_precheck_audit(
    audit_dir: Path,
    *,
    plan: dict,
    deployed_git_sha: str,
    backup: Path,
    backup_sha256: str,
    started_at: str,
    result: DestinationPrecheckResult | None,
    error: str | None,
) -> Path:
    audit_dir.mkdir(parents=True, exist_ok=False)
    audit_path = audit_dir / "precheck-audit.jsonl"
    ended_at = utc_now()
    with audit_path.open("x", encoding="utf-8") as audit:
        _audit_record(
            audit,
            {
                "event": "precheck_begin",
                "mode": "precheck-only",
                "ticket": TICKET,
                "plan_sha256": digest(plan),
                "execution_input": EXECUTION_INPUT_LOGICAL_ID,
                "execution_input_sha256": plan.get("execution_input_sha256"),
                "source_sha256": plan.get("source_sha256"),
                "allowlist_sha256": plan.get("allowlist_sha256"),
                "deployed_git_sha": deployed_git_sha,
                "backup": str(backup),
                "backup_sha256": backup_sha256,
                "count": plan.get("count"),
                "writes_performed": False,
                "started_at": started_at,
            },
        )
        if error is None and result is not None:
            _audit_record(
                audit,
                {
                    "event": "precheck_complete",
                    "mode": "precheck-only",
                    "writes_performed": False,
                    "sku_checked": result.sku_checked,
                    "skus_absent": result.sku_checked,
                    "brands_required": result.brands_required,
                    "brands_resolved": result.brands_resolved,
                    "categories_required": result.categories_required,
                    "categories_selectable_matched": result.categories_selectable_matched,
                    "started_at": started_at,
                    "ended_at": ended_at,
                },
            )
        else:
            _audit_record(
                audit,
                {
                    "event": "precheck_failed",
                    "mode": "precheck-only",
                    "writes_performed": False,
                    "error": redact_secrets(error or "unknown"),
                    "started_at": started_at,
                    "ended_at": ended_at,
                },
            )
    return audit_path


def precheck_only(
    plan: dict,
    api_base: str,
    token: str,
    backup: Path,
    backup_sha256: str,
    audit_dir: Path,
    deployed_git_sha: str,
    transport: UrlTransport | None = None,
) -> DestinationPrecheckResult:
    assert_plan_scope(plan)
    validate_backup(backup, backup_sha256)
    if not GIT_SHA.fullmatch(deployed_git_sha):
        raise RuntimeError("--deployed-git-sha must be a 40-character Git SHA")
    client = transport or ReadOnlyUrlTransport(api_base, token)
    if hasattr(client, "allow_mutations"):
        client.allow_mutations = False  # type: ignore[misc]
    started_at = utc_now()
    try:
        result = run_destination_precheck(plan, client)
        if getattr(client, "posts", 0):
            raise RuntimeError("POST occurred during destination prechecks")
        write_precheck_audit(
            audit_dir,
            plan=plan,
            deployed_git_sha=deployed_git_sha,
            backup=backup,
            backup_sha256=backup_sha256,
            started_at=started_at,
            result=result,
            error=None,
        )
        return result
    except Exception as exc:
        failure = redact_secrets(str(exc))
        if not audit_dir.exists():
            write_precheck_audit(
                audit_dir,
                plan=plan,
                deployed_git_sha=deployed_git_sha,
                backup=backup,
                backup_sha256=backup_sha256,
                started_at=started_at,
                result=None,
                error=failure,
            )
        raise RuntimeError(failure) from None


def apply(
    plan: dict,
    api_base: str,
    token: str,
    backup: Path,
    backup_sha256: str,
    audit_dir: Path,
    deployed_git_sha: str,
    transport: UrlTransport | None = None,
) -> None:
    assert_plan_scope(plan)
    validate_backup(backup, backup_sha256)
    if transport is None:
        precheck_client: UrlTransport = ReadOnlyUrlTransport(api_base, token)
        write_client: UrlTransport = UrlTransport(api_base, token)
    else:
        precheck_client = transport
        write_client = transport
    precheck = run_destination_precheck(plan, precheck_client)
    if getattr(precheck_client, "posts", 0) or getattr(write_client, "posts", 0):
        raise RuntimeError("POST occurred during destination prechecks")
    brand_ids = precheck.brand_ids
    audit_dir.mkdir(parents=True, exist_ok=False)
    created: list[dict] = []
    with (audit_dir / "audit.jsonl").open("x", encoding="utf-8") as audit:

        def record(event: dict) -> None:
            _audit_record(audit, event)

        try:
            record(
                {
                    "event": "begin",
                    "ticket": TICKET,
                    "plan_sha256": digest(plan),
                    "execution_input": EXECUTION_INPUT_LOGICAL_ID,
                    "execution_input_sha256": plan.get("execution_input_sha256"),
                    "deployed_git_sha": deployed_git_sha,
                    "backup": str(backup),
                    "backup_sha256": backup_sha256,
                    "count": plan["count"],
                    "precheck_sku_checked": precheck.sku_checked,
                    "writes_performed": False,
                }
            )
            for entry in plan["entries"]:
                payload = dict(entry["payload"])
                payload["brand_id"] = brand_ids[entry["brand"]]
                payload["category_id"] = entry["category_id"]
                extra = set(payload) - ALLOWED_PAYLOAD_KEYS
                if extra or set(payload) & FORBIDDEN_PAYLOAD_KEYS:
                    raise RuntimeError(f"refusing forbidden fields for {entry['sku']}")
                record(
                    {
                        "event": "create_intent",
                        "sku": entry["sku"],
                        "source_url": entry["source_url"],
                    }
                )
                created_product = write_client.post_product(payload)
                assert_created_postcondition(created_product, payload)
                created.append({"sku": entry["sku"], "id": created_product.get("id")})
                record({"event": "created", "sku": entry["sku"], "id": created_product.get("id")})
            record({"event": "complete", "created": plan["count"], "writes_performed": True})
        except Exception as exc:
            record(
                {
                    "event": "terminal_failure",
                    "state": RECONCILIATION_STATE,
                    "created_ids": [item["id"] for item in created],
                    "created_skus": [item["sku"] for item in created],
                    "created_count": len(created),
                    "remaining_count": plan["count"] - len(created),
                    "error": redact_secrets(str(exc)),
                }
            )
            raise


def require_production_apply_env(api_base: str) -> str:
    explicit = api_base.rstrip("/")
    env_base = (os.getenv("KARZAR_API_BASE") or "").rstrip("/")
    if not explicit or not env_base:
        raise RuntimeError("Category B writer requires explicit production KARZAR_API_BASE")
    if explicit != env_base:
        raise RuntimeError("KARZAR_API_BASE must match --api-base")
    if not is_production_base(explicit):
        raise RuntimeError("Category B writer requires explicit production KARZAR_API_BASE")
    if (
        os.getenv(ALLOW_ENV, "").strip() != "1"
        or os.getenv(CATEGORY_ENV, "").strip().upper() != "B"
    ):
        raise RuntimeError("both ADR-012 Category B environment variables must be present")
    assert_destination_allowed(explicit, label="KARZAR_API_BASE")
    return explicit


def _require_live_gates(
    parser: argparse.ArgumentParser, args: argparse.Namespace, plan_sha: str
) -> str:
    if args.confirm_count != EXPECTED_COUNT or args.confirm_plan_sha256 != plan_sha:
        parser.error("confirmed plan hash and count must match the generated 309-SKU plan")
    if (
        not args.backup
        or not args.backup_sha256
        or not args.audit_dir
        or not args.deployed_git_sha
        or not args.api_base
    ):
        parser.error(
            "live mode requires backup, backup SHA-256, audit directory, deployed Git SHA, and --api-base"
        )
    if not GIT_SHA.fullmatch(args.deployed_git_sha):
        parser.error("--deployed-git-sha must be a 40-character Git SHA")
    try:
        validate_backup(args.backup, args.backup_sha256)
        api_base = require_production_apply_env(args.api_base)
    except RuntimeError as exc:
        parser.error(str(exc))
    token = os.getenv(ADMIN_TOKEN_ENV, "")
    if not token:
        parser.error(f"{ADMIN_TOKEN_ENV} is required; never supply admin passwords")
    return api_base


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-input", type=Path, default=DEFAULT_EXECUTION_INPUT)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--allowlist-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ticket", required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--precheck-only", action="store_true")
    parser.add_argument("--confirm-plan-sha256")
    parser.add_argument("--confirm-count", type=int)
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--backup-sha256")
    parser.add_argument("--audit-dir", type=Path)
    parser.add_argument("--deployed-git-sha")
    parser.add_argument("--api-base")
    args = parser.parse_args(argv)
    if args.ticket != TICKET:
        parser.error("--ticket must be 344")
    plan = build_draft_plan(
        args.execution_input,
        args.allowlist,
        args.source_sha256,
        args.allowlist_sha256,
    )
    plan_sha = digest(plan)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary: dict[str, Any] = {
        "ticket": TICKET,
        "count": plan["count"],
        "plan_sha256": plan_sha,
        "execution_input": EXECUTION_INPUT_LOGICAL_ID,
        "execution_input_sha256": PINNED_EXECUTION_INPUT_SHA256,
        "applied": False,
        "writes_performed": False,
    }
    if args.precheck_only:
        summary["mode"] = "precheck-only"
    print(json.dumps(summary))
    if not args.apply and not args.precheck_only:
        return 0
    api_base = _require_live_gates(parser, args, plan_sha)
    token = os.getenv(ADMIN_TOKEN_ENV, "")
    if args.precheck_only:
        precheck_only(
            plan,
            api_base,
            token,
            args.backup,
            args.backup_sha256,
            args.audit_dir,
            args.deployed_git_sha,
        )
        return 0
    apply(
        plan,
        api_base,
        token,
        args.backup,
        args.backup_sha256,
        args.audit_dir,
        args.deployed_git_sha,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
