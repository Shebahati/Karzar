"""Safety tests for the pinned ZCC Category B draft writer."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import zcc_ir_category_b_draft_import as writer  # noqa: E402
from zcc_ir_category_b_draft_import import (  # noqa: E402
    ALLOWED_PAYLOAD_KEYS,
    EXPECTED_COUNT,
    FORBIDDEN_PAYLOAD_KEYS,
    RECONCILIATION_STATE,
    apply,
    build_draft_plan,
    draft_payload,
    main,
)
from zcc_ir_category_b_execution_input import (  # noqa: E402
    DEFAULT_ALLOWLIST,
    DEFAULT_EXECUTION_INPUT,
    PINNED_ALLOWLIST_SHA256,
    PINNED_EXECUTION_INPUT_SHA256,
    PINNED_SOURCE_SHA256,
    bind_allowlist,
    load_execution_input,
    verify_execution_input,
)


class FakeTransport:
    def __init__(
        self,
        *,
        brands=None,
        categories=None,
        existing=None,
        created=None,
        fail_on=None,
    ) -> None:
        self.brands = [{"id": 8, "name": "ZCC.CT"}] if brands is None else brands
        self.categories = [{"id": 33, "is_selectable": True}] if categories is None else categories
        self.existing = set(existing or [])
        self.created_template = created or {}
        self.fail_on = fail_on
        self.posts = 0
        self.posted: list[dict] = []

    def get(self, path: str):
        if path == "/brands/":
            return {"data": self.brands}
        if path == "/categories/":
            return {"data": self.categories}
        raise AssertionError(path)

    def get_product_by_sku(self, sku: str):
        if sku in self.existing:
            return {"sku": sku, "id": 1}
        return None

    def post_product(self, payload: dict) -> dict:
        self.posts += 1
        self.posted.append(payload)
        if self.fail_on == payload["sku"]:
            raise RuntimeError("forced create failure")
        created = {
            "id": 100 + self.posts,
            "sku": payload["sku"],
            "is_active": False,
            "is_available": False,
            "base_price": None,
            "stock_quantity": "0",
            "images": [],
            "thumbnail": None,
        }
        created.update(self.created_template)
        return created


@pytest.fixture
def scope_count(monkeypatch):
    def _set(count: int) -> None:
        monkeypatch.setattr(writer, "EXPECTED_COUNT", count)

    return _set


def mini_record(sku: str = "ZCC-A", brand: str = "ZCC.CT", category_id: int = 33) -> dict:
    return {
        "sku": sku,
        "brand": brand,
        "category_id": category_id,
        "source_url": f"https://zcc.ir/product/{sku.lower()}/",
        "name": f"name {sku}",
        "source_timestamp": "2026-09-17T00:00:00Z",
        "source_attributes": {},
    }


def mini_plan(records: list[dict] | None = None) -> dict:
    entries = []
    for record in records or [mini_record()]:
        entries.append(
            {
                "sku": record["sku"],
                "brand": record["brand"],
                "category_id": record["category_id"],
                "source_url": record["source_url"],
                "payload": draft_payload(record),
            }
        )
    return {
        "ticket": "344",
        "count": len(entries),
        "entries": entries,
        "source_sha256": PINNED_SOURCE_SHA256,
        "allowlist_sha256": PINNED_ALLOWLIST_SHA256,
    }


def valid_backup(tmp_path: Path) -> tuple[Path, str]:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    backup = backup_dir / "karzar_20260919_120000.sql.gz"
    backup.write_bytes(b"sql-gzip-bytes")
    return backup, hashlib.sha256(backup.read_bytes()).hexdigest()


def test_pinned_execution_input_has_exactly_309_unique_records() -> None:
    document = load_execution_input(DEFAULT_EXECUTION_INPUT)
    bind_allowlist(document, DEFAULT_ALLOWLIST)
    skus = [row["sku"] for row in document["records"]]
    assert document["count"] == 309
    assert EXPECTED_COUNT == 309
    assert len(skus) == 309
    assert len(set(skus)) == 309
    assert document["source_sha256"] == PINNED_SOURCE_SHA256
    assert document["allowlist_sha256"] == PINNED_ALLOWLIST_SHA256
    assert hashlib.sha256(DEFAULT_EXECUTION_INPUT.read_bytes()).hexdigest() == PINNED_EXECUTION_INPUT_SHA256


def test_hash_mismatch_rejection(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source SHA-256 mismatch"):
        build_draft_plan(
            DEFAULT_EXECUTION_INPUT,
            DEFAULT_ALLOWLIST,
            "0" * 64,
            PINNED_ALLOWLIST_SHA256,
        )
    with pytest.raises(ValueError, match="allowlist SHA-256 mismatch"):
        build_draft_plan(
            DEFAULT_EXECUTION_INPUT,
            DEFAULT_ALLOWLIST,
            PINNED_SOURCE_SHA256,
            "0" * 64,
        )
    mutated = tmp_path / "mutated.json"
    document = json.loads(DEFAULT_EXECUTION_INPUT.read_text(encoding="utf-8"))
    document["records"][0]["name"] = "mutated"
    mutated.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="execution input SHA-256 mismatch"):
        load_execution_input(mutated)


def test_duplicate_sku_rejection() -> None:
    document = {"count": 2, "records": [mini_record("ZCC-A"), mini_record("ZCC-A")]}
    with pytest.raises(ValueError, match="duplicate"):
        verify_execution_input(document, expected_count=2)


def test_forbidden_commerce_publication_fields() -> None:
    record = mini_record()
    record["base_price"] = 10
    with pytest.raises(ValueError, match="forbidden"):
        verify_execution_input({"count": 1, "records": [record]}, expected_count=1)
    payload = draft_payload(mini_record())
    assert payload["is_active"] is False
    assert payload["is_available"] is False
    assert payload["base_price"] is None
    assert payload["stock_quantity"] == 0
    assert "images" not in payload
    assert "original_price" not in payload
    assert set(payload) <= ALLOWED_PAYLOAD_KEYS
    assert not (set(payload) & FORBIDDEN_PAYLOAD_KEYS)


def test_missing_production_gates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "plan-out"
    for key in (
        "KARZAR_API_BASE",
        "KARZAR_ALLOW_PRODUCTION_WRITE",
        "KARZAR_INGESTION_CATEGORY",
        "KARZAR_CATEGORY_B_ADMIN_TOKEN",
    ):
        monkeypatch.setenv(key, "")
    with pytest.raises(SystemExit):
        main(
            [
                "--execution-input",
                str(DEFAULT_EXECUTION_INPUT),
                "--allowlist",
                str(DEFAULT_ALLOWLIST),
                "--source-sha256",
                PINNED_SOURCE_SHA256,
                "--allowlist-sha256",
                PINNED_ALLOWLIST_SHA256,
                "--output",
                str(output),
                "--ticket",
                "344",
                "--apply",
                "--confirm-plan-sha256",
                "deadbeef",
                "--confirm-count",
                "309",
                "--backup",
                str(tmp_path / "backups" / "karzar_20260919_120000.sql.gz"),
                "--backup-sha256",
                "0" * 64,
                "--audit-dir",
                str(tmp_path / "audit"),
                "--deployed-git-sha",
                "a" * 40,
                "--api-base",
                "https://api.karzartools.com/api/v1",
            ]
        )


def test_no_post_before_destination_prechecks(tmp_path: Path, scope_count) -> None:
    scope_count(1)
    backup, backup_sha = valid_backup(tmp_path)
    plan = mini_plan()
    transport = FakeTransport(brands=[])
    with pytest.raises(RuntimeError, match="brand missing"):
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            tmp_path / "audit-missing-brand",
            "a" * 40,
            transport,
        )
    assert transport.posts == 0
    transport = FakeTransport(categories=[{"id": 33, "is_selectable": False}])
    with pytest.raises(RuntimeError, match="not selectable"):
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            tmp_path / "audit-bad-cat",
            "a" * 40,
            transport,
        )
    assert transport.posts == 0


def test_existing_destination_sku_rejection(tmp_path: Path, scope_count) -> None:
    scope_count(1)
    backup, backup_sha = valid_backup(tmp_path)
    plan = mini_plan()
    transport = FakeTransport(existing={"ZCC-A"})
    with pytest.raises(RuntimeError, match="already exists"):
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            tmp_path / "audit-existing",
            "a" * 40,
            transport,
        )
    assert transport.posts == 0


def test_invalid_or_missing_brand_or_category_rejection(tmp_path: Path, scope_count) -> None:
    scope_count(1)
    backup, backup_sha = valid_backup(tmp_path)
    plan = mini_plan([mini_record(brand="Missing")])
    with pytest.raises(RuntimeError, match="brand missing"):
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            tmp_path / "audit-brand",
            "a" * 40,
            FakeTransport(),
        )
    plan = mini_plan([mini_record(category_id=99)])
    with pytest.raises(RuntimeError, match="not selectable"):
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            tmp_path / "audit-cat",
            "a" * 40,
            FakeTransport(),
        )
    plan = mini_plan()
    transport = FakeTransport(brands=[{"id": 8, "name": "ZCC.CT"}, {"id": 9, "name": "ZCC.CT"}])
    with pytest.raises(RuntimeError, match="not unique"):
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            tmp_path / "audit-dup-brand",
            "a" * 40,
            transport,
        )
    assert transport.posts == 0


def test_backup_validation_rejection(tmp_path: Path, scope_count) -> None:
    scope_count(1)
    plan = mini_plan()
    transport = FakeTransport()
    loose = tmp_path / "karzar_20260919_120000.sql.gz"
    loose.write_bytes(b"x")
    with pytest.raises(RuntimeError, match="backups/"):
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            loose,
            hashlib.sha256(b"x").hexdigest(),
            tmp_path / "audit-backup",
            "a" * 40,
            transport,
        )
    backup, _digest = valid_backup(tmp_path)
    with pytest.raises(RuntimeError, match="backup SHA-256 mismatch"):
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            "0" * 64,
            tmp_path / "audit-backup-sha",
            "a" * 40,
            transport,
        )
    empty = tmp_path / "backups" / "karzar_20260919_120001.sql.gz"
    empty.write_bytes(b"")
    with pytest.raises(RuntimeError, match="non-empty"):
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            empty,
            hashlib.sha256(b"").hexdigest(),
            tmp_path / "audit-empty",
            "a" * 40,
            transport,
        )
    assert transport.posts == 0


def test_partial_failure_audit_contents(tmp_path: Path, scope_count) -> None:
    scope_count(2)
    backup, backup_sha = valid_backup(tmp_path)
    plan = mini_plan([mini_record("ZCC-A"), mini_record("ZCC-B")])
    transport = FakeTransport(fail_on="ZCC-B")
    audit_dir = tmp_path / "audit-partial"
    with pytest.raises(RuntimeError, match="forced create failure"):
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            audit_dir,
            "a" * 40,
            transport,
        )
    events = [json.loads(line) for line in (audit_dir / "audit.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events[0]["event"] == "begin"
    assert any(event["event"] == "create_intent" for event in events)
    assert any(event["event"] == "created" and event["sku"] == "ZCC-A" for event in events)
    failure = events[-1]
    assert failure["event"] == "terminal_failure"
    assert failure["state"] == RECONCILIATION_STATE
    assert failure["created_skus"] == ["ZCC-A"]
    assert failure["created_count"] == 1
    assert failure["remaining_count"] == 1
    assert transport.posts == 2


def test_successful_response_postcondition_validation(tmp_path: Path, scope_count) -> None:
    scope_count(1)
    backup, backup_sha = valid_backup(tmp_path)
    plan = mini_plan()
    transport = FakeTransport(created={"is_active": True})
    audit_dir = tmp_path / "audit-post"
    with pytest.raises(RuntimeError, match="postcondition failed"):
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            audit_dir,
            "a" * 40,
            transport,
        )
    failure = [json.loads(line) for line in (audit_dir / "audit.jsonl").read_text(encoding="utf-8").splitlines()][-1]
    assert failure["event"] == "terminal_failure"
    assert failure["created_count"] == 0
    ok = FakeTransport()
    apply(plan, "https://api.karzartools.com/api/v1", "token", backup, backup_sha, tmp_path / "audit-ok", "a" * 40, ok)
    assert ok.posts == 1
    assert ok.posted[0]["is_active"] is False
    assert ok.posted[0]["is_available"] is False
    assert ok.posted[0]["base_price"] is None
    assert ok.posted[0]["stock_quantity"] == 0
