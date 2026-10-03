from __future__ import annotations

import ast
import re
from pathlib import Path

from services.gsc_mcp.config import GOOGLE_OAUTH_SCOPE

ROOT = Path(__file__).resolve().parents[1] / "services" / "gsc_mcp"

READONLY_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
WRITE_SCOPE = "https://www.googleapis.com/auth/webmasters"

FORBIDDEN_ATTR_CHAINS: tuple[tuple[str, ...], ...] = (
    ("sitemaps", "submit"),
    ("sitemaps", "delete"),
    ("sites", "add"),
    ("sites", "delete"),
)

FORBIDDEN_EXACT_STRINGS = frozenset(
    {
        "sitemaps.submit",
        "sitemaps.delete",
        "sites.add",
        "sites.delete",
    }
)

SCAN_PATHS = (
    ROOT,
)


def _attr_name_chain(node: ast.AST) -> tuple[str, ...]:
    parts: list[str] = []
    current: ast.AST = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return tuple(reversed(parts))


def _collect_py_files() -> list[Path]:
    files: list[Path] = []
    for base in SCAN_PATHS:
        for py_file in base.rglob("*.py"):
            if py_file.name.startswith("test_"):
                continue
            files.append(py_file)
    return files


def _static_violations(path: Path, tree: ast.AST) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            chain = _attr_name_chain(node)
            for forbidden in FORBIDDEN_ATTR_CHAINS:
                if chain == forbidden or chain[-len(forbidden) :] == forbidden:
                    violations.append(f"{path}: forbidden attribute chain {'.'.join(chain)}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if value in FORBIDDEN_EXACT_STRINGS:
                violations.append(f"{path}: forbidden API reference string {value!r}")
            if value == WRITE_SCOPE:
                violations.append(f"{path}: writable OAuth scope string")
            if "indexing.googleapis.com" in value:
                violations.append(f"{path}: Indexing API host in string constant")
    return violations


def test_oauth_scope_constant_is_readonly_only() -> None:
    assert GOOGLE_OAUTH_SCOPE == READONLY_SCOPE
    assert GOOGLE_OAUTH_SCOPE != WRITE_SCOPE


def test_read_only_contract_guard_static() -> None:
    violations: list[str] = []
    for py_file in _collect_py_files():
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        violations.extend(_static_violations(py_file, tree))
    assert not violations, "\n".join(violations)
