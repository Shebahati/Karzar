"""Safety tests for the ZCC Category B preflight command."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("zcc_b_preflight", ROOT / "scripts" / "zcc_ir_category_b_preflight.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_preflight_binds_unique_allowlist_to_source(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    allowlist = tmp_path / "allowlist.md"
    source.write_text(json.dumps([{"brand_normalized": "ZCC.CT", "part_number": "DCMT 11", "source_url": "https://zcc.ir/product/a/"}]), encoding="utf-8")
    allowlist.write_text("| SKU | Brand |\n| --- | --- |\n| ZCC-DCMT-11 | ZCC.CT |\n", encoding="utf-8")
    plan = MODULE.build_preflight(source, allowlist, digest(source), digest(allowlist))
    assert plan["count"] == 1
    assert plan["entries"][0]["commerce"] == "OMITTED"
    assert plan["writes_performed"] is False


def test_preflight_rejects_duplicate_allowlist_rows(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    allowlist = tmp_path / "allowlist.md"
    source.write_text("[]", encoding="utf-8")
    allowlist.write_text("| ZCC-A | x |\n| ZCC-A | x |\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        MODULE.build_preflight(source, allowlist, digest(source), digest(allowlist))
