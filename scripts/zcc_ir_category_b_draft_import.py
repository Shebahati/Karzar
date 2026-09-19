#!/usr/bin/env python3
"""Ticket #344 Category B writer for the reviewed ZCC draft allowlist.

Default mode is offline plan generation.  ``--apply`` is deliberately hard to
reach: it requires the ADR-012 production opt-in, a fresh VPS DB backup,
operator-confirmed plan hash/count, a temporary admin token, and an exclusive
audit directory.  It creates inactive, unavailable drafts only; it never
writes price, stock, images, or active-state true.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib import error, parse, request

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from ingestion_boundary import is_production_base, resolve_api_base  # noqa: E402
from zcc_ir_category_b_preflight import build_preflight, proposed_sku, sha256  # noqa: E402

TICKET = "344"
EXPECTED_COUNT = 309
ALLOWLIST_CATEGORY_ROW = re.compile(r"^\|\s*((?:ZCC|SANOU|STC)-[A-Z0-9./+_-]+)\s*\|\s*[^|]+\|\s*(\d+)\s*\|")


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def allowlist_categories(path: Path) -> dict[str, int]:
    values = {match.group(1): int(match.group(2)) for line in path.read_text(encoding="utf-8").splitlines() if (match := ALLOWLIST_CATEGORY_ROW.match(line))}
    if len(values) != EXPECTED_COUNT:
        raise ValueError("allowlist must bind exactly 309 SKU/category pairs")
    return values


def build_draft_plan(source: Path, allowlist: Path, source_sha: str, allowlist_sha: str) -> dict:
    """Bind source to allowlist and emit only non-commercial draft payloads."""
    preflight = build_preflight(source, allowlist, source_sha, allowlist_sha)
    categories = allowlist_categories(allowlist)
    rows = json.loads(source.read_text(encoding="utf-8"))
    by_sku = {proposed_sku(row): row for row in rows if proposed_sku(row)}
    entries = []
    for item in preflight["entries"]:
        row = by_sku[item["sku"]]
        name = str(row.get("name_fa") or "").strip()
        if not name:
            raise ValueError(f"missing Persian name for {item['sku']}")
        entries.append(
            {
                "sku": item["sku"],
                "brand": item["brand"],
                "category_id": categories[item["sku"]],
                "source_url": item["source_url"],
                "payload": {
                    "sku": item["sku"],
                    "name": name,
                    "is_active": False,
                    "is_available": False,
                    "base_price": None,
                    "stock_quantity": 0,
                    "specifications": {
                        "source_attributes": row.get("attributes") or {},
                        "source_url": item["source_url"],
                        "source_timestamp": row.get("crawl_timestamp"),
                    },
                },
            }
        )
    if len(entries) != EXPECTED_COUNT or len({entry["sku"] for entry in entries}) != EXPECTED_COUNT:
        raise ValueError("Category B scope must be exactly 309 unique SKUs")
    return {"ticket": TICKET, "mode": "CATEGORY_B_INACTIVE_DRAFT_ONLY", "source_sha256": source_sha,
            "allowlist_sha256": allowlist_sha, "count": len(entries), "entries": entries,
            "commerce_fields": "OMITTED", "writes_performed": False}


def api_json(method: str, base: str, path: str, token: str, data: object | None = None) -> object:
    body = None if data is None else json.dumps(data).encode()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    try:
        with request.urlopen(request.Request(base + path, data=body, headers=headers, method=method), timeout=30) as response:
            return json.load(response)
    except error.HTTPError as exc:
        detail = exc.read(500).decode("utf-8", errors="replace")
        raise RuntimeError(f"API {method} {path} failed HTTP {exc.code}: {detail}") from None


def data_list(value: object, label: str) -> list[dict]:
    values = value.get("data") if isinstance(value, dict) else None
    if not isinstance(values, list):
        raise RuntimeError(f"unexpected {label} response")
    return values


def apply(plan: dict, api_base: str, token: str, backup: Path, audit_dir: Path) -> None:
    """Run the bounded writer after all command-line and environment locks pass."""
    brands = data_list(api_json("GET", api_base, "/brands/", token), "brands")
    categories = data_list(api_json("GET", api_base, "/categories/", token), "categories")
    brand_ids = {str(item.get("name")): item.get("id") for item in brands}
    category_ids = {item.get("id") for item in categories if item.get("is_selectable")}
    if any(entry["brand"] not in brand_ids for entry in plan["entries"]):
        raise RuntimeError("approved brand missing on destination; refusing brand creation")
    for entry in plan["entries"]:
        matches = data_list(api_json("GET", api_base, "/products/?limit=100&search=" + parse.quote(entry["sku"]), token), "products")
        if any(product.get("sku") == entry["sku"] for product in matches):
            raise RuntimeError(f"destination SKU already exists: {entry['sku']}")
    audit_dir.mkdir(parents=True, exist_ok=False)
    with (audit_dir / "audit.jsonl").open("x", encoding="utf-8") as audit:
        def record(event: dict) -> None:
            audit.write(json.dumps(event, ensure_ascii=False) + "\n")
            audit.flush()
            os.fsync(audit.fileno())
        record({"event": "begin", "ticket": TICKET, "plan_sha256": digest(plan), "backup": str(backup), "backup_sha256": sha256(backup)})
        for entry in plan["entries"]:
            payload = dict(entry["payload"])
            payload["brand_id"] = brand_ids[entry["brand"]]
            if entry["category_id"] not in category_ids:
                raise RuntimeError(f"allowlist category is not selectable: {entry['category_id']}")
            payload["category_id"] = entry["category_id"]
            record({"event": "create_intent", "sku": entry["sku"], "source_url": entry["source_url"]})
            created = api_json("POST", api_base, "/products/", token, payload)
            if created.get("sku") != entry["sku"] or created.get("is_active") or created.get("is_available"):
                raise RuntimeError(f"postcondition failed for {entry['sku']}")
            record({"event": "created", "sku": entry["sku"], "id": created.get("id")})
        record({"event": "complete", "created": plan["count"]})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--allowlist", required=True, type=Path)
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
    args = parser.parse_args()
    if args.ticket != TICKET:
        parser.error("--ticket must be #344")
    plan = build_draft_plan(args.source, args.allowlist, args.source_sha256, args.allowlist_sha256)
    plan_sha = digest(plan)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ticket": TICKET, "count": plan["count"], "plan_sha256": plan_sha, "applied": False}))
    if not args.apply:
        return 0
    if not all([args.confirm_plan_sha256, args.backup, args.backup_sha256, args.audit_dir]) or args.confirm_count != EXPECTED_COUNT:
        parser.error("--apply requires confirmed plan/count, backup SHA-256, and audit directory")
    if args.confirm_plan_sha256 != plan_sha or sha256(args.backup) != args.backup_sha256:
        parser.error("confirmed plan or backup SHA-256 mismatch")
    api_base = resolve_api_base()
    if not is_production_base(api_base):
        parser.error("Category B writer requires explicit production KARZAR_API_BASE")
    token = os.getenv("KARZAR_CATEGORY_B_ADMIN_TOKEN", "")
    if not token:
        parser.error("KARZAR_CATEGORY_B_ADMIN_TOKEN is required; never supply admin passwords")
    apply(plan, api_base, token, args.backup, args.audit_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
