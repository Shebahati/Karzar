#!/usr/bin/env python3
"""Fail-closed, read-only preflight for the ZCC Category B draft allowlist.

This command never calls an API and rejects ``--apply``.  It binds an
operator-provided source crawl to the Git-reviewed 309-SKU allowlist before a
separate, reviewed Category B writer can be considered.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

PREFIX = {"ZCC.CT": "ZCC", "SAN OU": "SANOU", "STC": "STC"}
ALLOWLIST_ROW = re.compile(r"^\|\s*((?:ZCC|SANOU|STC)-[A-Z0-9./+_-]+)\s*\|")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def proposed_sku(row: dict) -> str | None:
    brand = row.get("brand_normalized")
    code = row.get("part_number") or row.get("manufacturer_code")
    if brand not in PREFIX or not code:
        return None
    sku = PREFIX[brand] + "-" + re.sub(r"\s+", "-", str(code).strip().upper())
    return sku if len(sku) <= 50 and re.fullmatch(r"[A-Z0-9./+_-]+", sku) else None


def load_allowlist(path: Path) -> list[str]:
    values = [m.group(1) for line in path.read_text(encoding="utf-8").splitlines() if (m := ALLOWLIST_ROW.match(line))]
    if not values:
        raise ValueError("allowlist contains no SKU rows")
    duplicate = sorted(sku for sku, count in Counter(values).items() if count != 1)
    if duplicate:
        raise ValueError("allowlist contains duplicate SKUs: " + ", ".join(duplicate[:5]))
    return values


def build_preflight(source_path: Path, allowlist_path: Path, expected_source_sha: str, expected_allowlist_sha: str) -> dict:
    if sha256(source_path) != expected_source_sha:
        raise ValueError("source SHA-256 mismatch")
    if sha256(allowlist_path) != expected_allowlist_sha:
        raise ValueError("allowlist SHA-256 mismatch")
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(source, list):
        raise ValueError("source must be a JSON list")
    allowlist = load_allowlist(allowlist_path)
    by_sku: dict[str, list[dict]] = {}
    for row in source:
        sku = proposed_sku(row)
        if sku:
            by_sku.setdefault(sku, []).append(row)
    missing = [sku for sku in allowlist if sku not in by_sku]
    ambiguous = [sku for sku in allowlist if len(by_sku.get(sku, [])) != 1]
    if missing or ambiguous:
        raise ValueError(f"allowlist/source mismatch: missing={len(missing)} ambiguous={len(ambiguous)}")
    entries = []
    for sku in allowlist:
        row = by_sku[sku][0]
        entries.append(
            {
                "sku": sku,
                "source_url": row.get("source_url"),
                "brand": row.get("brand_normalized"),
                "mode": "CREATE_INACTIVE_DRAFT_ONLY",
                "commerce": "OMITTED",
            }
        )
    return {
        "mode": "CATEGORY_B_PREFLIGHT_ONLY",
        "source_sha256": expected_source_sha,
        "allowlist_sha256": expected_allowlist_sha,
        "count": len(entries),
        "entries": entries,
        "writes_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--allowlist", required=True, type=Path)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--allowlist-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--apply", action="store_true", help="Rejected: no Category B writer exists in this command.")
    args = parser.parse_args()
    if args.apply:
        parser.error("--apply is forbidden; this command is preflight-only")
    if args.ticket != "344":
        parser.error("--ticket must reference the approved ZCC change ticket (#344)")
    plan = build_preflight(args.source, args.allowlist, args.source_sha256, args.allowlist_sha256)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "preflight.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ticket": args.ticket, "count": plan["count"], "writes_performed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
