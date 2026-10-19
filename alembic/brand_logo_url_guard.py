"""Schema-equivalence guard for brands.logo_url (revision u6v7w8x9y0z1).

Live CR-011 drift: column may exist before Alembic records u6 on the parallel branch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

COLUMN_NAME = "logo_url"
TABLE_NAME = "brands"
EXPECTED_LENGTH = 500


class BrandLogoUrlSchemaError(RuntimeError):
    """Existing brands.logo_url is present but not equivalent to the migration contract."""


@dataclass(frozen=True)
class LogoUrlColumnSpec:
    nullable: bool
    varchar_length: int | None
    has_server_default: bool

    @classmethod
    def expected(cls) -> LogoUrlColumnSpec:
        return cls(nullable=True, varchar_length=EXPECTED_LENGTH, has_server_default=False)


def _varchar_length(col_type: Any) -> int | None:
    length = getattr(col_type, "length", None)
    if length is not None:
        return int(length)
    # PostgreSQL unbounded VARCHAR reports as VARCHAR() with length None — treat as incompatible.
    return None


def column_spec_from_inspector(col: dict[str, Any]) -> LogoUrlColumnSpec:
    col_type = col["type"]
    type_name = type(col_type).__name__.lower()
    if "string" not in type_name and "varchar" not in type_name:
        raise BrandLogoUrlSchemaError(
            f"{TABLE_NAME}.{COLUMN_NAME} must be VARCHAR({EXPECTED_LENGTH}), found {col_type!r}",
        )
    length = _varchar_length(col_type)
    default = col.get("default")
    has_server_default = default is not None
    return LogoUrlColumnSpec(
        nullable=bool(col.get("nullable", True)),
        varchar_length=length,
        has_server_default=has_server_default,
    )


def assert_logo_url_compatible(existing: LogoUrlColumnSpec, expected: LogoUrlColumnSpec | None = None) -> None:
    expected = expected or LogoUrlColumnSpec.expected()
    if not existing.nullable:
        raise BrandLogoUrlSchemaError(f"{TABLE_NAME}.{COLUMN_NAME} must be nullable")
    if existing.has_server_default:
        raise BrandLogoUrlSchemaError(f"{TABLE_NAME}.{COLUMN_NAME} must not have a server default")
    if existing.varchar_length != expected.varchar_length:
        raise BrandLogoUrlSchemaError(
            f"{TABLE_NAME}.{COLUMN_NAME} must be VARCHAR({expected.varchar_length}), "
            f"found length {existing.varchar_length!r}",
        )


def get_logo_url_column(bind) -> dict[str, Any] | None:
    inspector = inspect(bind)
    if TABLE_NAME not in inspector.get_table_names():
        raise BrandLogoUrlSchemaError(f"table {TABLE_NAME} does not exist")
    for col in inspector.get_columns(TABLE_NAME):
        if col["name"] == COLUMN_NAME:
            return col
    return None


def brands_have_non_null_logo_url(bind) -> bool:
    result = bind.execute(
        text(f"SELECT 1 FROM {TABLE_NAME} WHERE {COLUMN_NAME} IS NOT NULL LIMIT 1"),
    )
    return result.first() is not None


def upgrade_brands_logo_url() -> None:
    bind = op.get_bind()
    existing = get_logo_url_column(bind)
    if existing is None:
        op.add_column(
            TABLE_NAME,
            sa.Column(COLUMN_NAME, sa.String(length=EXPECTED_LENGTH), nullable=True),
        )
        return
    assert_logo_url_compatible(column_spec_from_inspector(existing))


def downgrade_brands_logo_url() -> None:
    bind = op.get_bind()
    existing = get_logo_url_column(bind)
    if existing is None:
        return
    if brands_have_non_null_logo_url(bind):
        return
    op.drop_column(TABLE_NAME, COLUMN_NAME)
