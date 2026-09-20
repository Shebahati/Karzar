#!/usr/bin/env python3
"""Ticket #344 Category B writer for the pinned 309-SKU ZCC draft input.

Default mode is offline plan generation from the Git-tracked execution input.
``--apply`` is fail-closed: production URL, ADR-012 env vars, backup artifact,
deployed Git SHA, confirmed plan hash/count, admin token, and an exclusive
audit directory are all required. It creates inactive unavailable drafts only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from decimal import Decimal
from pathlib import Path
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


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


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
        "execution_input": str(execution_input),
        "count": len(entries),
        "entries": entries,
        "commerce_fields": "OMITTED",
        "writes_performed": False,
    }


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError("Redirect refused; production destination must remain explicit")


class UrlTransport:
    def __init__(self, api_base: str, token: str) -> None:
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.posts = 0

    def _call(self, method: str, path: str, data: object | None = None) -> object:
        body = None if data is None else json.dumps(data).encode()
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
        try:
            with opener.open(
                request.Request(self.api_base + path, data=body, headers=headers, method=method),
                timeout=30,
            ) as response:
                return json.load(response)
        except error.HTTPError as exc:
            detail = exc.read(500).decode("utf-8", errors="replace")
            raise RuntimeError(f"API {method} {path} failed HTTP {exc.code}: {detail}") from None

    def get(self, path: str) -> object:
        return self._call("GET", path)

    def get_product_by_sku(self, sku: str) -> dict | None:
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
        self.posts += 1
        created = self._call("POST", "/products/", payload)
        if not isinstance(created, dict):
            raise RuntimeError("unexpected product create response")
        return created


def data_list(value: object, label: str) -> list[dict]:
    values = value.get("data") if isinstance(value, dict) else None
    if not isinstance(values, list):
        raise RuntimeError(f"unexpected {label} response")
    return values


def unique_brand_ids(brands: list[dict], required: set[str]) -> dict[str, int]:
    grouped: dict[str, list[int]] = {}
    for item in brands:
        name = str(item.get("name") or "").strip()
        brand_id = item.get("id")
        if not name or not isinstance(brand_id, int):
            continue
        grouped.setdefault(name, []).append(brand_id)
    resolved = {}
    for name in sorted(required):
        ids = grouped.get(name) or []
        if len(ids) == 0:
            raise RuntimeError(f"approved brand missing on destination: {name}")
        if len(ids) != 1:
            raise RuntimeError(f"approved brand is not unique on destination: {name}")
        resolved[name] = ids[0]
    return resolved


def selectable_category_ids(categories: list[dict]) -> set[int]:
    return {item.get("id") for item in categories if item.get("is_selectable") and isinstance(item.get("id"), int)}


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


def precheck_destination(plan: dict, transport: UrlTransport) -> dict[str, int]:
    if getattr(transport, "posts", 0):
        raise RuntimeError("destination prechecks must run before any POST")
    brands = data_list(transport.get("/brands/"), "brands")
    categories = data_list(transport.get("/categories/"), "categories")
    required_brands = {entry["brand"] for entry in plan["entries"]}
    brand_ids = unique_brand_ids(brands, required_brands)
    selectable = selectable_category_ids(categories)
    missing_categories = sorted(
        {entry["category_id"] for entry in plan["entries"] if entry["category_id"] not in selectable}
    )
    if missing_categories:
        raise RuntimeError("allowlist category is missing or not selectable: " + ",".join(map(str, missing_categories)))
    existing = []
    for entry in plan["entries"]:
        found = transport.get_product_by_sku(entry["sku"])
        if found is not None:
            existing.append(entry["sku"])
    if existing:
        raise RuntimeError("destination SKU already exists: " + ",".join(existing[:10]))
    if getattr(transport, "posts", 0):
        raise RuntimeError("POST occurred during destination prechecks")
    return brand_ids


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
    if plan["ticket"] != TICKET or plan["count"] != EXPECTED_COUNT:
        raise RuntimeError("apply plan is not the approved 309-SKU ticket 344 scope")
    validate_backup(backup, backup_sha256)
    client = transport or UrlTransport(api_base, token)
    brand_ids = precheck_destination(plan, client)
    audit_dir.mkdir(parents=True, exist_ok=False)
    created: list[dict] = []
    with (audit_dir / "audit.jsonl").open("x", encoding="utf-8") as audit:

        def record(event: dict) -> None:
            audit.write(json.dumps(event, ensure_ascii=False) + "\n")
            audit.flush()
            os.fsync(audit.fileno())

        try:
            record(
                {
                    "event": "begin",
                    "ticket": TICKET,
                    "plan_sha256": digest(plan),
                    "deployed_git_sha": deployed_git_sha,
                    "backup": str(backup.resolve()),
                    "backup_sha256": backup_sha256,
                    "count": plan["count"],
                }
            )
            for entry in plan["entries"]:
                payload = dict(entry["payload"])
                payload["brand_id"] = brand_ids[entry["brand"]]
                payload["category_id"] = entry["category_id"]
                extra = set(payload) - ALLOWED_PAYLOAD_KEYS
                if extra or set(payload) & FORBIDDEN_PAYLOAD_KEYS:
                    raise RuntimeError(f"refusing forbidden fields for {entry['sku']}")
                record({"event": "create_intent", "sku": entry["sku"], "source_url": entry["source_url"]})
                created_product = client.post_product(payload)
                assert_created_postcondition(created_product, payload)
                created.append({"sku": entry["sku"], "id": created_product.get("id")})
                record({"event": "created", "sku": entry["sku"], "id": created_product.get("id")})
            record({"event": "complete", "created": plan["count"]})
        except Exception as exc:
            record(
                {
                    "event": "terminal_failure",
                    "state": RECONCILIATION_STATE,
                    "created_ids": [item["id"] for item in created],
                    "created_skus": [item["sku"] for item in created],
                    "created_count": len(created),
                    "remaining_count": plan["count"] - len(created),
                    "error": str(exc),
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
    if os.getenv(ALLOW_ENV, "").strip() != "1" or os.getenv(CATEGORY_ENV, "").strip().upper() != "B":
        raise RuntimeError("both ADR-012 Category B environment variables must be present")
    assert_destination_allowed(explicit, label="KARZAR_API_BASE")
    return explicit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-input", type=Path, default=DEFAULT_EXECUTION_INPUT)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--allowlist-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--apply", action="store_true")
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
    (args.output / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ticket": TICKET, "count": plan["count"], "plan_sha256": plan_sha, "applied": False}))
    if not args.apply:
        return 0
    if args.confirm_count != EXPECTED_COUNT or args.confirm_plan_sha256 != plan_sha:
        parser.error("confirmed plan hash and count must match the generated 309-SKU plan")
    if not args.backup or not args.backup_sha256 or not args.audit_dir or not args.deployed_git_sha or not args.api_base:
        parser.error("--apply requires backup, backup SHA-256, audit directory, deployed Git SHA, and --api-base")
    if not GIT_SHA.fullmatch(args.deployed_git_sha):
        parser.error("--deployed-git-sha must be a 40-character Git SHA")
    try:
        validate_backup(args.backup, args.backup_sha256)
        api_base = require_production_apply_env(args.api_base)
    except RuntimeError as exc:
        parser.error(str(exc))
    token = os.getenv("KARZAR_CATEGORY_B_ADMIN_TOKEN", "")
    if not token:
        parser.error("KARZAR_CATEGORY_B_ADMIN_TOKEN is required; never supply admin passwords")
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
