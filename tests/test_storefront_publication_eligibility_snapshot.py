"""Unit tests for read-only eligibility snapshot SQL helpers."""

from app.utils.public_catalog import (
    PLACEHOLDER_ILIKE_TOKENS,
    legacy_public_image_gate_sql_conditions,
)


def test_legacy_sql_includes_all_placeholder_tokens():
    sql = legacy_public_image_gate_sql_conditions("pi")
    for token in PLACEHOLDER_ILIKE_TOKENS:
        assert token in sql


def test_identity_equation_example():
    legacy = 100
    current = 130
    newly_visible = current - legacy
    assert current == legacy + newly_visible
