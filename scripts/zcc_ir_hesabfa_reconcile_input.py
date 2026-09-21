#!/usr/bin/env python3
"""Pinned Git-trackable Hesabfa reconciliation input for ticket #353 (parent #344).

Exactly 201 residual ZCC products whose post-create Hesabfa push failed.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

TICKET = "353"
PARENT_TICKET = "344"
EXPECTED_COUNT = 201
EXPECTED_CLASS_COUNTS = {
    "getItems_failed_before_save": 166,
    "save_returned_failure_lookup_first": 35,
}
ALLOWED_CLASSES = frozenset(EXPECTED_CLASS_COUNTS)
PINNED_APPLY_COMMIT = "d8f540e6cd0ab09a6c3f23ba0f74b0ddc9f6ed33"
PINNED_APPLY_AUDIT_SHA256 = (
    "8fabe6d565ba7855203bc0c69934cbe914ffa7a0aeb1d50307a165864aa7ed31"
)
# Filled after first write of the execution-input JSON.
PINNED_EXECUTION_INPUT_SHA256 = (
    "e8eac0709c0410febacdb1c8f64968c0195c60d23d8559ed9700a7763fb995cc"
)
REPO = Path(__file__).resolve().parents[1]
DEFAULT_EXECUTION_INPUT = (
    REPO
    / "docs/operations/pipeline/zcc-hesabfa-reconcile-ticket-353-execution-input.json"
)
RECORD_KEYS = ("product_id", "sku", "failure_class", "source_audit")


def sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_execution_input(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    verify_execution_input(document, path=path)
    return document


def verify_execution_input(document: dict, *, path: Path | None = None) -> None:
    if document.get("ticket") != TICKET:
        raise ValueError("execution input ticket must be 353")
    if document.get("parent_ticket") != PARENT_TICKET:
        raise ValueError("execution input parent_ticket must be 344")
    if document.get("count") != EXPECTED_COUNT:
        raise ValueError("execution input count must be 201")
    if document.get("apply_commit") != PINNED_APPLY_COMMIT:
        raise ValueError("execution input apply_commit mismatch")
    if document.get("apply_audit_sha256") != PINNED_APPLY_AUDIT_SHA256:
        raise ValueError("execution input apply_audit_sha256 mismatch")
    records = document.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_COUNT:
        raise ValueError("execution input must contain exactly 201 records")
    classes = Counter()
    skus: list[str] = []
    ids: list[int] = []
    for record in records:
        if set(record) != set(RECORD_KEYS):
            raise ValueError(f"unexpected record keys: {sorted(record)}")
        failure_class = record["failure_class"]
        if failure_class not in ALLOWED_CLASSES:
            raise ValueError(f"unknown failure_class: {failure_class}")
        classes[failure_class] += 1
        skus.append(record["sku"])
        ids.append(int(record["product_id"]))
    if dict(classes) != EXPECTED_CLASS_COUNTS:
        raise ValueError(f"failure_class counts mismatch: {dict(classes)}")
    if len(set(skus)) != EXPECTED_COUNT or len(set(ids)) != EXPECTED_COUNT:
        raise ValueError("execution input SKUs/product_ids must be unique")
    if path is not None:
        digest = sha256_file(path)
        if digest != PINNED_EXECUTION_INPUT_SHA256:
            raise ValueError(
                f"execution input SHA-256 mismatch: got {digest} want {PINNED_EXECUTION_INPUT_SHA256}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--input", type=Path, default=DEFAULT_EXECUTION_INPUT)
    args = parser.parse_args(argv)
    if not args.verify:
        parser.error("pass --verify")
    load_execution_input(args.input)
    print(
        json.dumps(
            {
                "ok": True,
                "ticket": TICKET,
                "count": EXPECTED_COUNT,
                "sha256": sha256_file(args.input),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
