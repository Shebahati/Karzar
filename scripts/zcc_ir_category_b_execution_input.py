#!/usr/bin/env python3
"""Pinned Git-trackable Category B execution input for ticket #344.

The 721-row crawl lives under ignored ``/data/`` and is not the runtime SoT.
This module generates (offline) and verifies a 309-row draft-only snapshot
bound to the original source SHA-256 and the reviewed allowlist SHA-256.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from zcc_ir_category_b_preflight import build_preflight, proposed_sku, sha256

TICKET = "344"
EXPECTED_COUNT = 309
PINNED_SOURCE_SHA256 = "69505ee9874e5abc6d50f8c640226293e04101072a6d0233e81d5e7be69703d3"
PINNED_ALLOWLIST_SHA256 = "abd0c6871ad5fe31d10f1b63321bc5b7e16a7c011ccaf75642560059c8ec2b98"
PINNED_EXECUTION_INPUT_SHA256 = "2b25c777a9b59f8ce11370dab220c3be6da44a3af8ad69a6f5902bf553b25248"
REPO = Path(__file__).resolve().parents[1]
DEFAULT_ALLOWLIST = REPO / "docs/operations/ZCC-CATEGORY-B-ALLOWLIST-20260919.md"
DEFAULT_EXECUTION_INPUT = (
    REPO / "docs/operations/pipeline/zcc-category-b-ticket-344-execution-input.json"
)
ALLOWLIST_CATEGORY_ROW = re.compile(
    r"^\|\s*((?:ZCC|SANOU|STC)-[A-Z0-9./+_-]+)\s*\|\s*([^|]+)\|\s*(\d+)\s*\|"
)
RECORD_KEYS = (
    "sku",
    "brand",
    "category_id",
    "source_url",
    "name",
    "source_timestamp",
    "source_attributes",
)
FORBIDDEN_RECORD_KEYS = frozenset(
    {
        "base_price",
        "stock_quantity",
        "is_active",
        "is_available",
        "availability",
        "price_normalized",
        "price_raw",
        "price_status",
        "price_currency",
        "original_price",
        "gallery_image_urls",
        "main_image_url",
        "images",
        "thumbnail",
    }
)


def allowlist_rows(path: Path) -> list[tuple[str, str, int]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ALLOWLIST_CATEGORY_ROW.match(line)
        if not match:
            continue
        rows.append((match.group(1), match.group(2).strip(), int(match.group(3))))
    if len(rows) != EXPECTED_COUNT:
        raise ValueError("allowlist must bind exactly 309 SKU/category pairs")
    skus = [sku for sku, _brand, _cid in rows]
    duplicate = sorted(sku for sku, count in Counter(skus).items() if count != 1)
    if duplicate:
        raise ValueError("allowlist contains duplicate SKUs: " + ", ".join(duplicate[:5]))
    return rows


def _strip_forbidden(record: dict) -> dict:
    extra = set(record) - set(RECORD_KEYS)
    forbidden = extra | (set(record) & FORBIDDEN_RECORD_KEYS)
    if forbidden:
        raise ValueError("execution record contains forbidden fields: " + ", ".join(sorted(forbidden)))
    return {key: record[key] for key in RECORD_KEYS}


def generate_execution_input(source: Path, allowlist: Path) -> dict:
    """Build the 309-row draft snapshot from a checksummed 721-row crawl."""
    source_digest = sha256(source)
    allowlist_digest = sha256(allowlist)
    if source_digest != PINNED_SOURCE_SHA256:
        raise ValueError("source SHA-256 mismatch")
    if allowlist_digest != PINNED_ALLOWLIST_SHA256:
        raise ValueError("allowlist SHA-256 mismatch")
    preflight = build_preflight(source, allowlist, source_digest, allowlist_digest)
    if preflight["count"] != EXPECTED_COUNT:
        raise ValueError("preflight must bind exactly 309 SKUs")
    rows = json.loads(source.read_text(encoding="utf-8"))
    by_sku: dict[str, dict] = {}
    for row in rows:
        sku = proposed_sku(row)
        if sku:
            by_sku.setdefault(sku, []).append(row)
    records = []
    for sku, brand, category_id in allowlist_rows(allowlist):
        matches = by_sku.get(sku) or []
        if len(matches) != 1:
            raise ValueError(f"source must contain exactly one row for {sku}")
        row = matches[0]
        name = str(row.get("name_fa") or "").strip()
        if not name:
            raise ValueError(f"missing Persian name for {sku}")
        if str(row.get("brand_normalized") or "").strip() != brand:
            raise ValueError(f"brand mismatch for {sku}")
        source_url = str(row.get("source_url") or "").strip()
        if source_url != next(item["source_url"] for item in preflight["entries"] if item["sku"] == sku):
            raise ValueError(f"source URL mismatch for {sku}")
        records.append(
            _strip_forbidden(
                {
                    "sku": sku,
                    "brand": brand,
                    "category_id": category_id,
                    "source_url": source_url,
                    "name": name,
                    "source_timestamp": row.get("crawl_timestamp"),
                    "source_attributes": row.get("attributes") or {},
                }
            )
        )
    if len(records) != EXPECTED_COUNT or len({item["sku"] for item in records}) != EXPECTED_COUNT:
        raise ValueError("execution input must contain exactly 309 unique SKUs")
    return {
        "ticket": TICKET,
        "mode": "CATEGORY_B_INACTIVE_DRAFT_ONLY",
        "source_rows": 721,
        "source_sha256": source_digest,
        "allowlist_sha256": allowlist_digest,
        "count": EXPECTED_COUNT,
        "records": records,
        "commerce_fields": "OMITTED",
    }


def load_execution_input(path: Path, *, expected_count: int = EXPECTED_COUNT) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    verify_execution_input(document, expected_count=expected_count)
    if expected_count == EXPECTED_COUNT:
        digest = sha256(path)
        if PINNED_EXECUTION_INPUT_SHA256 != "REPLACE_AFTER_GENERATE" and digest != PINNED_EXECUTION_INPUT_SHA256:
            raise ValueError("execution input SHA-256 mismatch")
        if document.get("source_sha256") != PINNED_SOURCE_SHA256:
            raise ValueError("source SHA-256 mismatch")
        if document.get("allowlist_sha256") != PINNED_ALLOWLIST_SHA256:
            raise ValueError("allowlist SHA-256 mismatch")
        if document.get("ticket") != TICKET:
            raise ValueError("execution input ticket must be 344")
    return document


def verify_execution_input(document: dict, *, expected_count: int = EXPECTED_COUNT) -> None:
    records = document.get("records")
    if not isinstance(records, list):
        raise ValueError("execution input records must be a list")
    if document.get("count") != expected_count or len(records) != expected_count:
        raise ValueError(f"execution input must contain exactly {expected_count} records")
    skus = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("execution record must be an object")
        _strip_forbidden(record)
        sku = str(record["sku"]).strip()
        name = str(record["name"]).strip()
        brand = str(record["brand"]).strip()
        source_url = str(record["source_url"]).strip()
        if not sku or not name or not brand or not source_url:
            raise ValueError("execution record missing required draft fields")
        if not isinstance(record["category_id"], int) or record["category_id"] < 1:
            raise ValueError(f"invalid category_id for {sku}")
        if not isinstance(record["source_attributes"], dict):
            raise ValueError(f"source_attributes must be an object for {sku}")
        skus.append(sku)
    duplicate = sorted(sku for sku, count in Counter(skus).items() if count != 1)
    if duplicate:
        raise ValueError("execution input contains duplicate SKUs: " + ", ".join(duplicate[:5]))


def bind_allowlist(document: dict, allowlist: Path) -> None:
    if sha256(allowlist) != document["allowlist_sha256"]:
        raise ValueError("allowlist SHA-256 mismatch")
    expected = [(sku, brand, category_id) for sku, brand, category_id in allowlist_rows(allowlist)]
    actual = [(row["sku"], row["brand"], row["category_id"]) for row in document["records"]]
    if expected != actual:
        raise ValueError("execution input SKU/brand/category tuples must match the allowlist")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument("--output", type=Path, default=DEFAULT_EXECUTION_INPUT)
    args = parser.parse_args()
    if args.generate == args.verify:
        parser.error("choose exactly one of --generate or --verify")
    if args.generate:
        if args.source is None:
            parser.error("--generate requires --source")
        document = generate_execution_input(args.source, args.allowlist)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"count": document["count"], "sha256": sha256(args.output), "writes_performed": False}))
        return 0
    document = load_execution_input(args.output)
    bind_allowlist(document, args.allowlist)
    print(json.dumps({"count": document["count"], "verified": True, "writes_performed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
