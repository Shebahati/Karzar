"""BE-01: money-path services must flush-only (no db.commit)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Hard contract: services flush-only (ARCHITECTURE.md BE-01).
MONEY_PATH_MODULES = [
    "app/services/payment_flow_service.py",
    "app/services/order_service.py",
    "app/services/payment_ledger_service.py",
    "app/services/order_expiry_service.py",
    "app/services/checkout_service.py",
    "app/services/hesabfa/invoice_retry.py",
    "app/services/product_service.py",
    "app/services/cart_service.py",
    "app/services/brand_service.py",
    "app/services/category_service.py",
    "app/services/otp_service.py",
    "app/services/idempotency_service.py",
    "app/services/hesabfa/item_push.py",
    "app/services/hesabfa/invoices.py",
]


def _commit_calls(tree: ast.AST) -> list[str]:
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            # db.commit() / session.commit() / await db.commit()
            if isinstance(func, ast.Attribute) and func.attr == "commit":
                hits.append(f"line {node.lineno}: .commit()")
    return hits


@pytest.mark.parametrize("rel_path", MONEY_PATH_MODULES)
def test_money_path_services_do_not_commit(rel_path: str) -> None:
    path = REPO_ROOT / rel_path
    assert path.is_file(), f"missing module {rel_path}"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits = _commit_calls(tree)
    assert not hits, f"{rel_path} must be flush-only; found commits: {hits}"
