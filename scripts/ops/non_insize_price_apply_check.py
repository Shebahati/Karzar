#!/usr/bin/env python3
"""Validate a non-INSIZE price manifest without printing row prices.

Money is parsed with Decimal. Binary float is not used.
"""

from __future__ import annotations

import hashlib
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

FACTOR = Decimal("1.20")
ONE_TOMAN = Decimal("1")
REASON = "owner_non_insize_price_increase_20pct_2026_09_29"

EXPECTED_TARGET = 4065
EXPECTED_CLASS_A = 4058
EXPECTED_CLASS_B = 7
EXPECTED_FRACTIONAL = 17
INSIZE_BRAND_ID = 3


def money(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or isinstance(value, float):
        raise SystemExit("manifest used a non-decimal price")
    return Decimal(str(value))


def round_half_up_toman(value: Decimal) -> Decimal:
    return (value * FACTOR).quantize(ONE_TOMAN, rounding=ROUND_HALF_UP)


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        if raw.strip() == r"\.":
            raise SystemExit(f"unsafe manifest terminator on line {line_no}")
        rows.append(json.loads(raw))
    return rows


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_manifest(path: Path) -> dict[str, object]:
    rows = load_jsonl(path)
    class_a = 0
    class_b = 0
    fractional = 0
    rounding_delta = Decimal("0")
    old_total = Decimal("0")
    raw_total = Decimal("0")
    rounded_total = Decimal("0")
    seen: set[int] = set()
    discount_drift = 0

    for row in rows:
        product_id = row["product_id"]
        if not isinstance(product_id, int):
            raise SystemExit("product_id must be an integer")
        if product_id in seen:
            raise SystemExit("duplicate product_id in manifest")
        seen.add(product_id)

        brand_id = row["brand_id"]
        if brand_id == INSIZE_BRAND_ID:
            raise SystemExit("INSIZE row present in manifest")
        if row["deleted_at"] is not None:
            raise SystemExit("soft-deleted row present in manifest")

        old_base = money(row["old_base_price"])
        new_base = money(row["new_base_price"])
        old_original = money(row["old_original_price"])
        new_original = money(row["new_original_price"])
        if old_base is None or old_base <= 0 or new_base is None:
            raise SystemExit("invalid base price in manifest")
        if new_base != round_half_up_toman(old_base):
            raise SystemExit("new base does not match ROUND_HALF_UP")
        if new_base != new_base.to_integral_value():
            raise SystemExit("new base is not a whole toman")

        raw = old_base * FACTOR
        if raw != raw.to_integral_value():
            fractional += 1
        rounding_delta += new_base - raw
        old_total += old_base
        raw_total += raw
        rounded_total += new_base

        price_class = row["price_class"]
        if price_class == "A":
            class_a += 1
            if old_original is not None or new_original is not None:
                raise SystemExit("class A original price is not null")
        elif price_class == "B":
            class_b += 1
            if old_original is None or new_original is None or old_original <= old_base:
                raise SystemExit("class B original price is not a discount")
            if new_original != round_half_up_toman(old_original):
                raise SystemExit("new original does not match ROUND_HALF_UP")
            old_pct = int(((Decimal("1") - (old_base / old_original)) * Decimal("100")).quantize(
                ONE_TOMAN, rounding=ROUND_HALF_UP
            ))
            new_pct = int(((Decimal("1") - (new_base / new_original)) * Decimal("100")).quantize(
                ONE_TOMAN, rounding=ROUND_HALF_UP
            ))
            if old_pct != new_pct:
                discount_drift += 1
        else:
            raise SystemExit(f"unexpected price class {price_class}")

    if len(rows) != EXPECTED_TARGET:
        raise SystemExit(f"target_count={len(rows)}")
    if class_a != EXPECTED_CLASS_A or class_b != EXPECTED_CLASS_B:
        raise SystemExit(f"class_a={class_a} class_b={class_b}")
    if fractional != EXPECTED_FRACTIONAL:
        raise SystemExit(f"fractional_raw={fractional}")
    if discount_drift != 0:
        raise SystemExit(f"class_b_discount_drift={discount_drift}")

    return {
        "rows": len(rows),
        "class_a": class_a,
        "class_b": class_b,
        "fractional_raw": fractional,
        "old_total": old_total,
        "raw_total": raw_total,
        "rounded_total": rounded_total,
        "rounding_delta": rounding_delta,
        "sha256": file_sha256(path),
        "reason": REASON,
    }


def compare_prices(manifest_path: Path, current_path: Path, *, field: str) -> int:
    """Return the number of product ids whose current price text differs."""
    expected = {row["product_id"]: money(row[field]) for row in load_jsonl(manifest_path)}
    current = {row["product_id"]: money(row["base_price"]) for row in load_jsonl(current_path)}
    if field == "new_original_price":
        current = {row["product_id"]: money(row["original_price"]) for row in load_jsonl(current_path)}
    mismatched = 0
    for product_id, price in expected.items():
        if current.get(product_id) != price:
            mismatched += 1
    if len(current) != len(expected):
        mismatched += abs(len(current) - len(expected))
    return mismatched


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: non_insize_price_apply_check.py validate|compare MANIFEST [CURRENT]", file=sys.stderr)
        return 2
    command = argv[1]
    manifest = Path(argv[2])
    if command == "validate":
        summary = validate_manifest(manifest)
        print(f"manifest_rows={summary['rows']}")
        print(f"class_a={summary['class_a']}")
        print(f"class_b={summary['class_b']}")
        print(f"fractional_raw={summary['fractional_raw']}")
        print(f"old_total={summary['old_total']}")
        print(f"raw_total={summary['raw_total']}")
        print(f"rounded_total={summary['rounded_total']}")
        print(f"rounding_delta={summary['rounding_delta']}")
        print(f"manifest_sha256={summary['sha256']}")
        print("decimal_rounding_matches=YES")
        return 0
    if command == "compare":
        if len(argv) != 4:
            return 2
        summary = validate_manifest(manifest)
        base_miss = compare_prices(manifest, Path(argv[3]), field="new_base_price")
        original_rows = []
        for row in load_jsonl(manifest):
            if row["price_class"] != "B":
                continue
            original_rows.append(row)
        current = {row["product_id"]: money(row["original_price"]) for row in load_jsonl(Path(argv[3]))}
        original_miss = 0
        for row in original_rows:
            if current.get(row["product_id"]) != money(row["new_original_price"]):
                original_miss += 1
        # Class A originals must still be null on the current export.
        class_a_ids = {row["product_id"] for row in load_jsonl(manifest) if row["price_class"] == "A"}
        for row in load_jsonl(Path(argv[3])):
            if row["product_id"] in class_a_ids and money(row["original_price"]) is not None:
                original_miss += 1
        print(f"post_commit_base_mismatches={base_miss}")
        print(f"post_commit_original_mismatches={original_miss}")
        print(f"manifest_sha256={summary['sha256']}")
        return 0 if base_miss == 0 and original_miss == 0 else 3
    if command == "state":
        if len(argv) != 4:
            return 2
        current_rows = {row["product_id"]: row for row in load_jsonl(Path(argv[3]))}
        new_miss = 0
        old_miss = 0
        for row in load_jsonl(manifest):
            current = current_rows.get(row["product_id"])
            if current is None:
                new_miss += 1
                old_miss += 1
                continue
            base = money(current["base_price"])
            original = money(current["original_price"])
            if base != money(row["new_base_price"]) or original != money(row["new_original_price"]):
                new_miss += 1
            if base != money(row["old_base_price"]) or original != money(row["old_original_price"]):
                old_miss += 1
        if new_miss == 0:
            print("price_state=applied")
            return 0
        if old_miss == 0:
            print("price_state=unchanged")
            return 0
        print("price_state=diverged")
        print(f"new_mismatches={new_miss}")
        print(f"old_mismatches={old_miss}")
        return 3
    if command == "compare-insize":
        before = {(row["product_id"], row["base_price"], row["original_price"]) for row in load_jsonl(manifest)}
        after = {(row["product_id"], row["base_price"], row["original_price"]) for row in load_jsonl(Path(argv[3]))}
        print(f"insize_price_rows_changed={len(before.symmetric_difference(after))}")
        print(f"insize_rows_before={len(before)}")
        print(f"insize_rows_after={len(after)}")
        return 0 if before == after else 3
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
            raise SystemExit(2) from exc
        raise
