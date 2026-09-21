#!/usr/bin/env python3
"""Ticket #353 Hesabfa item-shell reconciliation for the pinned 201-SKU residual.

Default mode is offline plan generation. ``--precheck-only`` performs sequential
read-only ``item/getItems`` probes plus local mapping/product checks and writes
an exclusive audit with ``writes_performed=false``. ``--apply`` is fail-closed
and performs lookup-first link-or-create via
``app.services.hesabfa.item_push.reconcile_product_item_shell`` (approved service
path). ``--precheck-only`` and ``--apply`` are mutually exclusive.

This command does not authorize production mutation by itself.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from ingestion_boundary import ALLOW_ENV, CATEGORY_ENV  # noqa: E402
from zcc_ir_hesabfa_reconcile_input import (  # noqa: E402
    DEFAULT_EXECUTION_INPUT,
    EXPECTED_COUNT,
    PARENT_TICKET,
    PINNED_APPLY_AUDIT_SHA256,
    PINNED_APPLY_COMMIT,
    PINNED_EXECUTION_INPUT_SHA256,
    TICKET,
    load_execution_input,
    sha256_file,
)

BACKUP_NAME = re.compile(r"^karzar_\d{8}_\d{6}\.sql\.gz$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
ADMIN_TOKEN_ENV = "KARZAR_CATEGORY_B_ADMIN_TOKEN"
DEFAULT_DELAY_SECONDS = 0.75
DEFAULT_CIRCUIT_BREAKER = 5
SECRET_PATTERNS = (
    re.compile(r"(?i)authorization\s*[:=]\s*bearer\s+\S+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-+=/]+"),
    re.compile(r"(?i)(apiKey|loginToken|password|HESABFA_[A-Z0-9_]+)\s*[:=]\s*\S+"),
    re.compile(r"(?i)KARZAR_CATEGORY_B_ADMIN_TOKEN\s*[:=]\s*\S+"),
)
EXECUTION_INPUT_LOGICAL_ID = (
    "docs/operations/pipeline/zcc-hesabfa-reconcile-ticket-353-execution-input.json"
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


def validate_backup(backup: Path, expected_sha256: str) -> None:
    if not backup.is_file():
        raise RuntimeError("backup artifact missing")
    if backup.stat().st_size <= 0:
        raise RuntimeError("backup artifact empty")
    if not BACKUP_NAME.fullmatch(backup.name):
        raise RuntimeError("backup name must match karzar_YYYYMMDD_HHMMSS.sql.gz")
    if "backups" not in backup.resolve().parts:
        raise RuntimeError("backup must live under a backups/ directory")
    if sha256_file(backup) != expected_sha256:
        raise RuntimeError("backup SHA-256 mismatch")


def build_plan(execution_input: Path) -> dict[str, Any]:
    document = load_execution_input(execution_input)
    entries = []
    for record in document["records"]:
        entries.append(
            {
                "product_id": int(record["product_id"]),
                "sku": record["sku"],
                "failure_class": record["failure_class"],
                "source_audit": record["source_audit"],
            }
        )
    if len(entries) != EXPECTED_COUNT:
        raise ValueError("plan must contain exactly 201 entries")
    return {
        "ticket": TICKET,
        "parent_ticket": PARENT_TICKET,
        "mode": "HESABFA_ITEM_SHELL_RECONCILE_ONLY",
        "count": EXPECTED_COUNT,
        "execution_input": EXECUTION_INPUT_LOGICAL_ID,
        "execution_input_sha256": PINNED_EXECUTION_INPUT_SHA256,
        "apply_commit": PINNED_APPLY_COMMIT,
        "apply_audit_sha256": PINNED_APPLY_AUDIT_SHA256,
        "writes_performed": False,
        "entries": entries,
    }


def _audit_record(audit, event: dict) -> None:
    payload = dict(event)
    payload.setdefault("at", utc_now())
    audit.write(json.dumps(payload, ensure_ascii=False) + "\n")
    audit.flush()


def require_category_b_env() -> None:
    if os.getenv(ALLOW_ENV, "").strip() != "1" or os.getenv(CATEGORY_ENV, "").strip().upper() != "B":
        raise RuntimeError("both ADR-012 Category B environment variables must be present")


class CircuitBreaker:
    def __init__(self, threshold: int) -> None:
        self.threshold = threshold
        self.streak = 0
        self.last_class: str | None = None

    def observe(self, class_name: str, *, is_failure: bool) -> None:
        if not is_failure:
            self.streak = 0
            self.last_class = class_name
            return
        if class_name == self.last_class:
            self.streak += 1
        else:
            self.streak = 1
            self.last_class = class_name
        if self.streak >= self.threshold:
            raise RuntimeError(
                f"circuit breaker tripped on repeated class={class_name} streak={self.streak}"
            )


def _stock_ok(value: object) -> bool:
    return value in (0, 0.0, "0", "0.0") or (
        isinstance(value, int | float) and float(value) == 0.0
    )


async def _load_product_and_mapping(db, product_id: int, sku: str):
    from app.db.models.hesabfa import HesabfaItemMapping
    from app.db.models.product import Product
    from sqlalchemy import select

    product = (
        await db.execute(select(Product).where(Product.id == product_id))
    ).scalar_one_or_none()
    if product is None:
        raise RuntimeError(f"missing product id={product_id}")
    if product.deleted_at is not None:
        raise RuntimeError(f"deleted product id={product_id}")
    if product.sku != sku:
        raise RuntimeError(f"sku mismatch id={product_id}: db={product.sku} plan={sku}")
    if product.is_active or product.is_available or product.base_price is not None:
        raise RuntimeError(f"commerce drift id={product_id}")
    if not _stock_ok(product.stock_quantity):
        raise RuntimeError(f"stock drift id={product_id}")
    mapping = (
        await db.execute(
            select(HesabfaItemMapping).where(HesabfaItemMapping.product_id == product_id)
        )
    ).scalar_one_or_none()
    return product, mapping


async def _probe_remote(client, sku: str) -> dict[str, Any]:
    from app.services.hesabfa.item_push import _find_hesabfa_item_by_product_code
    from app.services.hesabfa.mapping import _normalize_sku

    page = await client.get_items(
        take=20,
        skip=0,
        filters=[{"Property": "ProductCode", "Operator": 1, "Value": sku}],
    )
    matches = []
    normalized = _normalize_sku(sku)
    for item in page.get("List") or []:
        code = _normalize_sku(str(item.get("ProductCode") or item.get("productCode") or ""))
        if code == normalized:
            matches.append(item)
    if len(matches) > 1:
        return {"state": "ambiguous_duplicate_remote", "matches": len(matches)}
    if len(matches) == 1:
        item = matches[0]
        return {
            "state": "remote_present",
            "hesabfa_code": str(item.get("Code") or item.get("code") or "").strip() or None,
        }
    # Conservative second-pass only when filtered list empty (same as push path).
    found = await _find_hesabfa_item_by_product_code(client, sku)
    if found is None:
        return {"state": "remote_absent", "hesabfa_code": None}
    return {
        "state": "remote_present",
        "hesabfa_code": str(found.get("Code") or found.get("code") or "").strip() or None,
    }


async def run_precheck(
    plan: dict[str, Any],
    *,
    audit_dir: Path,
    deployed_git_sha: str,
    delay_seconds: float,
    circuit_breaker: int,
    sleep_fn: Callable[[float], Any] | None = None,
) -> dict[str, Any]:
    from app.db.database import AsyncSessionLocal
    from app.services.hesabfa.client import get_hesabfa_client, hesabfa_integration_active

    if not hesabfa_integration_active():
        raise RuntimeError("Hesabfa integration inactive")
    if not GIT_SHA.fullmatch(deployed_git_sha):
        raise RuntimeError("--deployed-git-sha must be a 40-character Git SHA")
    audit_dir.mkdir(parents=True, exist_ok=False)
    client = get_hesabfa_client()
    sleeper = sleep_fn or asyncio.sleep
    breaker = CircuitBreaker(circuit_breaker)
    started = utc_now()
    counts: dict[str, int] = {
        "remote_present_locally_mapped": 0,
        "remote_present_mapping_missing": 0,
        "remote_absent": 0,
        "probe_failed": 0,
        "ambiguous_duplicate_remote": 0,
    }
    with (audit_dir / "precheck-audit.jsonl").open("x", encoding="utf-8") as audit:
        _audit_record(
            audit,
            {
                "event": "precheck_begin",
                "ticket": TICKET,
                "parent_ticket": PARENT_TICKET,
                "plan_sha256": digest(plan),
                "execution_input_sha256": PINNED_EXECUTION_INPUT_SHA256,
                "deployed_git_sha": deployed_git_sha,
                "count": plan["count"],
                "delay_seconds": delay_seconds,
                "circuit_breaker": circuit_breaker,
                "writes_performed": False,
                "started_at": started,
            },
        )
        async with AsyncSessionLocal() as db:
            for index, entry in enumerate(plan["entries"]):
                sku = entry["sku"]
                product_id = entry["product_id"]
                try:
                    product, mapping = await _load_product_and_mapping(db, product_id, sku)
                    remote = await _probe_remote(client, sku)
                    if remote["state"] == "ambiguous_duplicate_remote":
                        class_name = "ambiguous_duplicate_remote"
                    elif remote["state"] == "remote_absent":
                        class_name = "remote_absent"
                    elif mapping is not None and mapping.hesabfa_code:
                        class_name = "remote_present_locally_mapped"
                    else:
                        class_name = "remote_present_mapping_missing"
                    counts[class_name] += 1
                    breaker.observe(class_name, is_failure=class_name in {"probe_failed", "ambiguous_duplicate_remote"})
                    _audit_record(
                        audit,
                        {
                            "event": "probe",
                            "product_id": product_id,
                            "sku": sku,
                            "failure_class": entry["failure_class"],
                            "classification": class_name,
                            "hesabfa_code": remote.get("hesabfa_code"),
                            "local_mapping_present": mapping is not None,
                            "product_active": bool(product.is_active),
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    class_name = "probe_failed"
                    counts[class_name] += 1
                    breaker.observe(class_name, is_failure=True)
                    _audit_record(
                        audit,
                        {
                            "event": "probe",
                            "product_id": product_id,
                            "sku": sku,
                            "failure_class": entry["failure_class"],
                            "classification": class_name,
                            "error": redact_secrets(str(exc)),
                        },
                    )
                if index + 1 < len(plan["entries"]):
                    await sleeper(delay_seconds)
        ended = utc_now()
        _audit_record(
            audit,
            {
                "event": "precheck_complete",
                "ended_at": ended,
                "writes_performed": False,
                "counts": counts,
            },
        )
    return {"started_at": started, "ended_at": ended, "counts": counts, "writes_performed": False}


async def run_apply(
    plan: dict[str, Any],
    *,
    audit_dir: Path,
    deployed_git_sha: str,
    backup: Path,
    backup_sha256: str,
    delay_seconds: float,
    circuit_breaker: int,
    sleep_fn: Callable[[float], Any] | None = None,
) -> dict[str, Any]:
    from app.db.database import AsyncSessionLocal
    from app.services.hesabfa.client import get_hesabfa_client, hesabfa_integration_active
    from app.services.hesabfa.item_push import reconcile_product_item_shell

    require_category_b_env()
    validate_backup(backup, backup_sha256)
    if not GIT_SHA.fullmatch(deployed_git_sha):
        raise RuntimeError("--deployed-git-sha must be a 40-character Git SHA")
    if not hesabfa_integration_active():
        raise RuntimeError("Hesabfa integration inactive")
    # Precheck-equivalent remote classification is mandatory before first save.
    # Apply still lookup-first per record.
    audit_dir.mkdir(parents=True, exist_ok=False)
    client = get_hesabfa_client()
    sleeper = sleep_fn or asyncio.sleep
    breaker = CircuitBreaker(circuit_breaker)
    started = utc_now()
    created = 0
    linked = 0
    already = 0
    with (audit_dir / "audit.jsonl").open("x", encoding="utf-8") as audit:
        _audit_record(
            audit,
            {
                "event": "begin",
                "ticket": TICKET,
                "parent_ticket": PARENT_TICKET,
                "plan_sha256": digest(plan),
                "execution_input_sha256": PINNED_EXECUTION_INPUT_SHA256,
                "deployed_git_sha": deployed_git_sha,
                "backup": str(backup),
                "backup_sha256": backup_sha256,
                "count": plan["count"],
                "delay_seconds": delay_seconds,
                "writes_performed": False,
                "started_at": started,
            },
        )
        try:
            async with AsyncSessionLocal() as db:
                for index, entry in enumerate(plan["entries"]):
                    product, _mapping = await _load_product_and_mapping(
                        db, entry["product_id"], entry["sku"]
                    )
                    _audit_record(
                        audit,
                        {
                            "event": "reconcile_intent",
                            "product_id": entry["product_id"],
                            "sku": entry["sku"],
                            "failure_class": entry["failure_class"],
                        },
                    )
                    result = await reconcile_product_item_shell(
                        db, product, client=client, allow_save=True
                    )
                    await db.commit()
                    if result.action == "created":
                        created += 1
                    elif result.action == "linked_existing":
                        linked += 1
                    elif result.action == "already_mapped":
                        already += 1
                    else:
                        raise RuntimeError(f"unexpected reconcile action={result.action}")
                    breaker.observe(result.action, is_failure=False)
                    _audit_record(
                        audit,
                        {
                            "event": "reconciled",
                            "product_id": entry["product_id"],
                            "sku": entry["sku"],
                            "action": result.action,
                            "hesabfa_code": result.hesabfa_code,
                            "save_performed": result.save_performed,
                        },
                    )
                    if index + 1 < len(plan["entries"]):
                        await sleeper(delay_seconds)
            ended = utc_now()
            _audit_record(
                audit,
                {
                    "event": "complete",
                    "ended_at": ended,
                    "writes_performed": True,
                    "created": created,
                    "linked_existing": linked,
                    "already_mapped": already,
                },
            )
            return {
                "started_at": started,
                "ended_at": ended,
                "created": created,
                "linked_existing": linked,
                "already_mapped": already,
                "writes_performed": True,
            }
        except Exception as exc:
            _audit_record(
                audit,
                {
                    "event": "terminal_failure",
                    "error": redact_secrets(str(exc)),
                    "created": created,
                    "linked_existing": linked,
                    "already_mapped": already,
                    "state": "MANUAL_RECONCILIATION_OR_DB_ROLLBACK_REQUIRED",
                },
            )
            raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-input", type=Path, default=DEFAULT_EXECUTION_INPUT)
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
    parser.add_argument("--delay-seconds", type=float, default=DEFAULT_DELAY_SECONDS)
    parser.add_argument("--circuit-breaker", type=int, default=DEFAULT_CIRCUIT_BREAKER)
    args = parser.parse_args(argv)
    if args.ticket != TICKET:
        parser.error("--ticket must be 353")
    if args.delay_seconds < 0.25:
        parser.error("--delay-seconds must be >= 0.25")
    if args.circuit_breaker < 2:
        parser.error("--circuit-breaker must be >= 2")

    plan = build_plan(args.execution_input)
    plan_sha = digest(plan)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "ticket": TICKET,
        "parent_ticket": PARENT_TICKET,
        "count": plan["count"],
        "plan_sha256": plan_sha,
        "execution_input_sha256": PINNED_EXECUTION_INPUT_SHA256,
        "writes_performed": False,
        "applied": False,
    }
    if args.precheck_only:
        summary["mode"] = "precheck-only"
    print(json.dumps(summary))
    if not args.apply and not args.precheck_only:
        return 0

    if args.confirm_count != EXPECTED_COUNT or args.confirm_plan_sha256 != plan_sha:
        parser.error("confirmed plan hash and count must match the generated 201-SKU plan")
    if not args.audit_dir or not args.deployed_git_sha:
        parser.error("live mode requires --audit-dir and --deployed-git-sha")

    if args.precheck_only:
        result = asyncio.run(
            run_precheck(
                plan,
                audit_dir=args.audit_dir,
                deployed_git_sha=args.deployed_git_sha,
                delay_seconds=args.delay_seconds,
                circuit_breaker=args.circuit_breaker,
            )
        )
        print(json.dumps({"precheck": result, "writes_performed": False}))
        return 0

    if not args.backup or not args.backup_sha256:
        parser.error("--apply requires --backup and --backup-sha256")
    require_category_b_env()
    if not os.getenv(ADMIN_TOKEN_ENV):
        # Token not used for Hesabfa path (service uses server credentials) but
        # retain Category B operator discipline: require env presence without printing.
        parser.error(f"{ADMIN_TOKEN_ENV} is required for --apply operator attestation")
    result = asyncio.run(
        run_apply(
            plan,
            audit_dir=args.audit_dir,
            deployed_git_sha=args.deployed_git_sha,
            backup=args.backup,
            backup_sha256=args.backup_sha256,
            delay_seconds=args.delay_seconds,
            circuit_breaker=args.circuit_breaker,
        )
    )
    print(json.dumps({"apply": result}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
