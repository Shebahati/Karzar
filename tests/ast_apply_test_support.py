"""Test-only helpers (not imported by production CLI)."""

from __future__ import annotations

from catalog_target.ast_price_catalog_apply import load_create_plan


def load_create_plan_for_tests(path, **kwargs):  # noqa: ANN001
    kwargs.setdefault("require_owner_approval", False)
    return load_create_plan(path, **kwargs)
