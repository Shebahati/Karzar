"""Safety tests for the pinned ZCC Category B draft writer."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import zcc_ir_category_b_draft_import as writer  # noqa: E402
from zcc_ir_category_b_draft_import import (  # noqa: E402
    ALLOWED_PAYLOAD_KEYS,
    EXECUTION_INPUT_LOGICAL_ID,
    EXPECTED_COUNT,
    FORBIDDEN_PAYLOAD_KEYS,
    RECONCILIATION_STATE,
    ReadOnlyUrlTransport,
    UrlTransport,
    apply,
    brand_match_keys,
    build_draft_plan,
    digest,
    draft_payload,
    main,
    precheck_only,
    redact_secrets,
    run_destination_precheck,
    unique_brand_ids,
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
        brands_raw=None,
        categories_raw=None,
        sku_response_shape=None,
    ) -> None:
        self.brands = [{"id": 8, "name": "ZCC.CT"}] if brands is None else brands
        self.categories = [{"id": 33, "is_selectable": True}] if categories is None else categories
        self.brands_raw = brands_raw
        self.categories_raw = categories_raw
        self.sku_response_shape = sku_response_shape
        self.existing = set(existing or [])
        self.created_template = created or {}
        self.fail_on = fail_on
        self.posts = 0
        self.gets = 0
        self.sku_lookups = 0
        self.methods_called: list[str] = []
        self.posted: list[dict] = []
        self.allow_mutations = True

    def get(self, path: str):
        self.gets += 1
        self.methods_called.append("GET")
        if path == "/brands/":
            if self.brands_raw is not None:
                return self.brands_raw
            return {"data": self.brands}
        if path == "/categories/":
            if self.categories_raw is not None:
                return self.categories_raw
            return {"data": self.categories}
        raise AssertionError(path)

    def get_product_by_sku(self, sku: str):
        self.sku_lookups += 1
        self.methods_called.append("GET")
        if self.sku_response_shape is not None:
            return self.sku_response_shape
        if sku in self.existing:
            return {"sku": sku, "id": 1}
        return None

    def post_product(self, payload: dict) -> dict:
        if not self.allow_mutations:
            raise RuntimeError("read-only transport forbids POST before network dispatch")
        self.posts += 1
        self.methods_called.append("POST")
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
        "execution_input": EXECUTION_INPUT_LOGICAL_ID,
        "execution_input_sha256": PINNED_EXECUTION_INPUT_SHA256,
        "writes_performed": False,
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
    assert (
        hashlib.sha256(DEFAULT_EXECUTION_INPUT.read_bytes()).hexdigest()
        == PINNED_EXECUTION_INPUT_SHA256
    )


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


def test_plan_hash_independent_of_filesystem_root(tmp_path: Path) -> None:
    hashes = []
    for name in ("root-a", "root-b"):
        root = tmp_path / name
        docs = root / "docs" / "operations" / "pipeline"
        docs.mkdir(parents=True)
        allow_dir = root / "docs" / "operations"
        allow_dir.mkdir(parents=True, exist_ok=True)
        execution = docs / "zcc-category-b-ticket-344-execution-input.json"
        allowlist = allow_dir / "ZCC-CATEGORY-B-ALLOWLIST-20260919.md"
        shutil.copyfile(DEFAULT_EXECUTION_INPUT, execution)
        shutil.copyfile(DEFAULT_ALLOWLIST, allowlist)
        plan = build_draft_plan(execution, allowlist, PINNED_SOURCE_SHA256, PINNED_ALLOWLIST_SHA256)
        assert plan["execution_input"] == EXECUTION_INPUT_LOGICAL_ID
        assert plan["execution_input_sha256"] == PINNED_EXECUTION_INPUT_SHA256
        assert not Path(plan["execution_input"]).is_absolute()
        hashes.append(digest(plan))
    assert hashes[0] == hashes[1]


def test_precheck_only_and_apply_are_mutually_exclusive(tmp_path: Path) -> None:
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
                str(tmp_path / "plan-mutex"),
                "--ticket",
                "344",
                "--apply",
                "--precheck-only",
            ]
        )


def test_readonly_transport_rejects_non_get_before_network() -> None:
    transport = ReadOnlyUrlTransport("https://api.karzartools.com/api/v1", "secret-token-value")
    with pytest.raises(RuntimeError, match="forbids POST"):
        transport._call("POST", "/products/", {"sku": "ZCC-A"})
    with pytest.raises(RuntimeError, match="forbids PUT"):
        transport._call("PUT", "/products/1", {"sku": "ZCC-A"})
    with pytest.raises(RuntimeError, match="forbids PATCH"):
        transport._call("PATCH", "/products/1", {"sku": "ZCC-A"})
    with pytest.raises(RuntimeError, match="forbids DELETE"):
        transport._call("DELETE", "/products/1")
    with pytest.raises(RuntimeError, match="forbids POST"):
        transport.post_product({"sku": "ZCC-A"})
    assert transport.posts == 0
    assert transport.methods_called == ["POST", "PUT", "PATCH", "DELETE"]
    # Method names are recorded for auditability, but network dispatch never occurs.


def test_writable_transport_still_allows_post_method_listing() -> None:
    transport = UrlTransport("https://api.karzartools.com/api/v1", "token")
    assert transport.allow_mutations is True


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


def test_response_shape_rejection(tmp_path: Path, scope_count) -> None:
    scope_count(1)
    backup, backup_sha = valid_backup(tmp_path)
    plan = mini_plan()
    with pytest.raises(RuntimeError, match="unexpected brands response"):
        precheck_only(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            tmp_path / "audit-shape-brands",
            "a" * 40,
            FakeTransport(brands_raw=["not-a-dict"]),
        )
    with pytest.raises(RuntimeError, match="unexpected categories response"):
        precheck_only(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            tmp_path / "audit-shape-cats",
            "a" * 40,
            FakeTransport(categories_raw={"items": []}),
        )


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
    events = [
        json.loads(line)
        for line in (audit_dir / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
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
    failure = [
        json.loads(line)
        for line in (audit_dir / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ][-1]
    assert failure["event"] == "terminal_failure"
    assert failure["created_count"] == 0
    ok = FakeTransport()
    apply(
        plan,
        "https://api.karzartools.com/api/v1",
        "token",
        backup,
        backup_sha,
        tmp_path / "audit-ok",
        "a" * 40,
        ok,
    )
    assert ok.posts == 1
    assert ok.posted[0]["is_active"] is False
    assert ok.posted[0]["is_available"] is False
    assert ok.posted[0]["base_price"] is None
    assert ok.posted[0]["stock_quantity"] == 0


def test_precheck_only_covers_all_skus_with_zero_mutations(tmp_path: Path, scope_count) -> None:
    scope_count(3)
    backup, backup_sha = valid_backup(tmp_path)
    plan = mini_plan([mini_record("ZCC-A"), mini_record("ZCC-B"), mini_record("ZCC-C")])
    transport = FakeTransport()
    result = precheck_only(
        plan,
        "https://api.karzartools.com/api/v1",
        "super-secret-admin-token",
        backup,
        backup_sha,
        tmp_path / "audit-precheck-ok",
        "a" * 40,
        transport,
    )
    assert result.sku_checked == 3
    assert transport.sku_lookups == 3
    assert transport.posts == 0
    assert "POST" not in transport.methods_called
    assert all(method == "GET" for method in transport.methods_called)
    events = [
        json.loads(line)
        for line in (tmp_path / "audit-precheck-ok" / "precheck-audit.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert events[0]["writes_performed"] is False
    assert events[-1]["event"] == "precheck_complete"
    assert events[-1]["writes_performed"] is False
    assert events[-1]["sku_checked"] == 3
    assert events[-1]["skus_absent"] == 3
    blob = (tmp_path / "audit-precheck-ok" / "precheck-audit.jsonl").read_text(encoding="utf-8")
    assert "super-secret-admin-token" not in blob
    assert "Authorization" not in blob


def test_precheck_only_full_309_sku_lookups(tmp_path: Path) -> None:
    backup, backup_sha = valid_backup(tmp_path)
    plan = build_draft_plan(
        DEFAULT_EXECUTION_INPUT,
        DEFAULT_ALLOWLIST,
        PINNED_SOURCE_SHA256,
        PINNED_ALLOWLIST_SHA256,
    )
    category_ids = sorted({entry["category_id"] for entry in plan["entries"]})
    brand_names = sorted({entry["brand"] for entry in plan["entries"]})
    transport = FakeTransport(
        brands=[{"id": index + 1, "name": name} for index, name in enumerate(brand_names)],
        categories=[{"id": category_id, "is_selectable": True} for category_id in category_ids],
    )
    result = precheck_only(
        plan,
        "https://api.karzartools.com/api/v1",
        "token",
        backup,
        backup_sha,
        tmp_path / "audit-precheck-309",
        "b" * 40,
        transport,
    )
    assert plan["count"] == 309
    assert result.sku_checked == 309
    assert transport.sku_lookups == 309
    assert transport.posts == 0
    assert "POST" not in transport.methods_called
    assert result.brands_resolved == len(brand_names)
    assert result.categories_selectable_matched == len(category_ids)


def test_precheck_only_failure_audit_writes_performed_false(tmp_path: Path, scope_count) -> None:
    scope_count(1)
    backup, backup_sha = valid_backup(tmp_path)
    plan = mini_plan()
    transport = FakeTransport(existing={"ZCC-A"})
    with pytest.raises(RuntimeError, match="already exists"):
        precheck_only(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            tmp_path / "audit-precheck-fail",
            "a" * 40,
            transport,
        )
    events = [
        json.loads(line)
        for line in (tmp_path / "audit-precheck-fail" / "precheck-audit.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert events[-1]["event"] == "precheck_failed"
    assert events[-1]["writes_performed"] is False
    assert transport.posts == 0


def test_precheck_rejects_bad_deployed_sha_and_plan_confirm(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")
    monkeypatch.setenv("KARZAR_ALLOW_PRODUCTION_WRITE", "1")
    monkeypatch.setenv("KARZAR_INGESTION_CATEGORY", "B")
    monkeypatch.setenv("KARZAR_CATEGORY_B_ADMIN_TOKEN", "token")
    backup, backup_sha = valid_backup(tmp_path)
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
                str(tmp_path / "plan-bad-sha"),
                "--ticket",
                "344",
                "--precheck-only",
                "--confirm-plan-sha256",
                "0" * 64,
                "--confirm-count",
                "309",
                "--backup",
                str(backup),
                "--backup-sha256",
                backup_sha,
                "--audit-dir",
                str(tmp_path / "audit-bad-confirm"),
                "--deployed-git-sha",
                "not-a-git-sha",
                "--api-base",
                "https://api.karzartools.com/api/v1",
            ]
        )


def test_secret_redaction_helper() -> None:
    text = "Authorization: Bearer super-secret-admin-token failed"
    assert "super-secret-admin-token" not in redact_secrets(text)
    assert "[REDACTED]" in redact_secrets(text)


def test_apply_consumes_shared_precheck_before_any_post(tmp_path: Path, scope_count) -> None:
    scope_count(2)
    backup, backup_sha = valid_backup(tmp_path)
    plan = mini_plan([mini_record("ZCC-A"), mini_record("ZCC-B")])
    transport = FakeTransport()
    posts_during_precheck = []

    original = writer.run_destination_precheck

    def wrapped(plan_arg, transport_arg):
        result = original(plan_arg, transport_arg)
        posts_during_precheck.append(transport_arg.posts)
        return result

    writer.run_destination_precheck = wrapped  # type: ignore[assignment]
    try:
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            tmp_path / "audit-shared-precheck",
            "a" * 40,
            transport,
        )
    finally:
        writer.run_destination_precheck = original  # type: ignore[assignment]
    assert posts_during_precheck == [0]
    assert transport.posts == 2
    assert transport.sku_lookups == 2


def test_run_destination_precheck_direct_counts(scope_count) -> None:
    scope_count(2)
    plan = mini_plan([mini_record("ZCC-A"), mini_record("ZCC-B")])
    transport = FakeTransport()
    result = run_destination_precheck(plan, transport)
    assert result.sku_checked == 2
    assert transport.posts == 0
    assert transport.sku_lookups == 2


def test_brand_match_keys_exact_and_bilingual_segments() -> None:
    assert brand_match_keys("ZCC.CT") == frozenset({"zcc.ct"})
    assert "zcc.ct" in brand_match_keys("ZCC.CT | زد سی‌سی")
    assert "زد سی‌سی".casefold() in brand_match_keys("ZCC.CT | زد سی‌سی")
    # whitespace around the literal bilingual delimiter is trimmed per segment
    assert "zcc.ct" in brand_match_keys("  ZCC.CT  |  زد سی‌سی  ")
    # Unicode-safe casefold on Latin segment
    assert "zcc.ct" in brand_match_keys("zcc.ct | FA")
    # no punctuation folding / fuzzy / substring keys
    assert "zccct" not in brand_match_keys("ZCC.CT | زد سی‌سی")
    assert "zcc" not in brand_match_keys("ZCC.CT | زد سی‌سی")


def test_unique_brand_ids_monolingual_and_bilingual() -> None:
    assert unique_brand_ids([{"id": 8, "name": "ZCC.CT"}], {"ZCC.CT"}) == {"ZCC.CT": 8}
    assert unique_brand_ids([{"id": 8, "name": "ZCC.CT | زد سی‌سی"}], {"ZCC.CT"}) == {"ZCC.CT": 8}
    assert unique_brand_ids([{"id": 8, "name": "  ZCC.CT  |  زد سی‌سی  "}], {"ZCC.CT"}) == {
        "ZCC.CT": 8
    }
    assert unique_brand_ids([{"id": 8, "name": "zcc.ct | زد سی‌سی"}], {"ZCC.CT"}) == {"ZCC.CT": 8}


def test_unique_brand_ids_rejects_punctuation_or_similar_names() -> None:
    with pytest.raises(RuntimeError, match="brand missing"):
        unique_brand_ids([{"id": 8, "name": "ZCC-CT | زد سی‌سی"}], {"ZCC.CT"})
    with pytest.raises(RuntimeError, match="brand missing"):
        unique_brand_ids([{"id": 8, "name": "ZCC CT | زد سی‌سی"}], {"ZCC.CT"})
    with pytest.raises(RuntimeError, match="brand missing"):
        unique_brand_ids([{"id": 8, "name": "ZCC | زد سی‌سی"}], {"ZCC.CT"})
    with pytest.raises(RuntimeError, match="brand missing"):
        unique_brand_ids([{"id": 8, "name": "Something ZCC.CT Extra"}], {"ZCC.CT"})


def test_unique_brand_ids_duplicate_bilingual_keys_fail_closed() -> None:
    brands = [
        {"id": 8, "name": "ZCC.CT | زد سی‌سی"},
        {"id": 9, "name": "ZCC.CT | alternate"},
    ]
    with pytest.raises(RuntimeError, match="not unique"):
        unique_brand_ids(brands, {"ZCC.CT"})
    with pytest.raises(RuntimeError, match="not unique"):
        unique_brand_ids(
            [{"id": 8, "name": "ZCC.CT"}, {"id": 9, "name": "ZCC.CT | زد سی‌سی"}],
            {"ZCC.CT"},
        )


def test_precheck_resolves_bilingual_zcc_brand_id_8(tmp_path: Path, scope_count) -> None:
    scope_count(1)
    backup, backup_sha = valid_backup(tmp_path)
    plan = mini_plan([mini_record(brand="ZCC.CT")])
    transport = FakeTransport(brands=[{"id": 8, "name": "ZCC.CT | زد سی‌سی"}])
    result = precheck_only(
        plan,
        "https://api.karzartools.com/api/v1",
        "token",
        backup,
        backup_sha,
        tmp_path / "audit-bilingual-brand",
        "a" * 40,
        transport,
    )
    assert result.brand_ids == {"ZCC.CT": 8}
    assert result.brands_resolved == 1
    assert transport.posts == 0
    assert "POST" not in transport.methods_called


def test_apply_uses_bilingual_brand_and_still_posts_only_after_precheck(
    tmp_path: Path, scope_count
) -> None:
    scope_count(1)
    backup, backup_sha = valid_backup(tmp_path)
    plan = mini_plan([mini_record(brand="ZCC.CT")])
    transport = FakeTransport(brands=[{"id": 8, "name": "ZCC.CT | زد سی‌سی"}])
    posts_during_precheck: list[int] = []
    original = writer.run_destination_precheck

    def wrapped(plan_arg, transport_arg):
        result = original(plan_arg, transport_arg)
        posts_during_precheck.append(transport_arg.posts)
        return result

    writer.run_destination_precheck = wrapped  # type: ignore[assignment]
    try:
        apply(
            plan,
            "https://api.karzartools.com/api/v1",
            "token",
            backup,
            backup_sha,
            tmp_path / "audit-bilingual-apply",
            "a" * 40,
            transport,
        )
    finally:
        writer.run_destination_precheck = original  # type: ignore[assignment]
    assert posts_during_precheck == [0]
    assert transport.posts == 1
    assert transport.posted[0]["brand_id"] == 8


def test_deterministic_plan_sha_unchanged_by_brand_match_fix() -> None:
    plan = build_draft_plan(
        DEFAULT_EXECUTION_INPUT,
        DEFAULT_ALLOWLIST,
        PINNED_SOURCE_SHA256,
        PINNED_ALLOWLIST_SHA256,
    )
    assert digest(plan) == "c1993d2439a17af83547a2cd21698d915d953421dd90e1128b3b66695146aec7"
