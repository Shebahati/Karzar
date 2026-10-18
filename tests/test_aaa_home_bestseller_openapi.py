"""Focused snapshot regression with an actionable field-level OpenAPI diff."""

import difflib
import json
from pathlib import Path

from app.main import app


def test_home_bestseller_openapi_contract_matches_snapshot():
    snapshot = json.loads((Path(__file__).resolve().parents[1] / "openapi" / "v1.json").read_text(encoding="utf-8"))
    actual = app.openapi()
    path = "/api/v1/home/bestsellers"
    keys = [
        ("paths", path),
        ("components", "schemas", "BestsellerSelectionResponse"),
        ("components", "schemas", "BestsellerSelectionWrite"),
    ]
    for key in keys:
        expected = snapshot
        generated = actual
        for part in key:
            expected = expected[part]
            generated = generated[part]
        before = json.dumps(expected, ensure_ascii=False, sort_keys=True, indent=2).splitlines()
        after = json.dumps(generated, ensure_ascii=False, sort_keys=True, indent=2).splitlines()
        assert before == after, "\n" + "\n".join(difflib.unified_diff(before, after, fromfile="committed", tofile="generated", lineterm=""))
