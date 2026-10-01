from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "services" / "gsc_mcp"

FORBIDDEN_SNIPPETS = (
    "sitemaps.submit",
    "sitemaps.delete",
    "sites.add",
    "sites.delete",
    "indexing.googleapis.com",
)

ALLOWED_READONLY_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


def _iter_call_and_constant_strings(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found.append(node.value)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            found.append(node.func.attr)
    return found


def test_read_only_contract_guard() -> None:
    violations: list[str] = []
    for py_file in ROOT.rglob("*.py"):
        if py_file.name.startswith("test_"):
            continue
        text = py_file.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in text:
                violations.append(f"{py_file}: contains {snippet}")
        if "auth/webmasters" in text and ALLOWED_READONLY_SCOPE not in text:
            violations.append(f"{py_file}: missing readonly OAuth scope")
        if "https://www.googleapis.com/auth/webmasters\"" in text.replace(ALLOWED_READONLY_SCOPE, ""):
            violations.append(f"{py_file}: write OAuth scope detected")
        joined = " ".join(_iter_call_and_constant_strings(py_file))
        if "submit" in joined and "sitemaps" in joined:
            violations.append(f"{py_file}: possible sitemap submit reference")
    assert not violations, "\n".join(violations)
