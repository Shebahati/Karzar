"""Phase 2E failure-injection tests against disposable PostgreSQL (CI)."""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from decimal import Decimal

import asyncpg
import pytest
from app.db.models.product import Product
from app.domain.product_naming_phase2e import (
    REHEARSAL_REASON,
    audit_rehearsal_logs,
    build_rehearsal_sql,
    parse_rehearsal_stdout,
)
from sqlalchemy import select

from tests.conftest import USE_POSTGRES_TESTS, TestingSessionLocal

pytestmark = pytest.mark.skipif(not USE_POSTGRES_TESTS, reason="requires PostgreSQL")


def _dsn() -> str:
    return (
        f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_SERVER']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )


async def _seed_products() -> tuple[list[dict[str, str]], list[tuple[int, str]]]:
    async with TestingSessionLocal() as session:
        from app.db.models.category import Category

        cat = (await session.execute(select(Category).limit(1))).scalars().first()
        assert cat is not None
        outsider = Product(
            sku="P2E-OUT-1",
            slug="p2e-out-1",
            name="outsider product",
            category_id=cat.id,
            base_price=Decimal("10"),
            is_active=True,
            is_available=True,
        )
        targets: list[Product] = []
        for i, (sku, old, _new, mc) in enumerate(
            [
                ("P2E-T1", "old one", "new one", "MC-1"),
                ("P2E-T2", "old two", "new two", "MC-2"),
                ("P2E-T3", "old three", "new three", "MC-3"),
            ],
            start=1,
        ):
            targets.append(
                Product(
                    sku=sku,
                    slug=f"p2e-t{i}",
                    name=old,
                    manufacturer_code=mc,
                    category_id=cat.id,
                    base_price=Decimal("10"),
                    is_active=True,
                    is_available=True,
                )
            )
        session.add(outsider)
        session.add_all(targets)
        await session.flush()
        prestate = [
            {
                "product_id": str(p.id),
                "sku": p.sku,
                "manufacturer_code": p.manufacturer_code or "",
                "brand_id": "",
                "product_type_id": "",
                "expected_old_name": p.name,
                "proposed_name": {"P2E-T1": "new one", "P2E-T2": "new two", "P2E-T3": "new three"}[p.sku],
                "proposed_name_norm": {"P2E-T1": "new one", "P2E-T2": "new two", "P2E-T3": "new three"}[p.sku],
            }
            for p in targets
        ]
        catalog = [(outsider.id, outsider.name)] + [(p.id, p.name) for p in targets]
        await session.commit()
        return prestate, catalog


def _run_psql_script(sql: str) -> tuple[str, int]:
    env = os.environ.copy()
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False) as tmp:
        tmp.write(sql)
        tmp_path = tmp.name
    proc = subprocess.run(
        [
            "psql",
            "-h",
            env["POSTGRES_SERVER"],
            "-p",
            str(env["POSTGRES_PORT"]),
            "-U",
            env["POSTGRES_USER"],
            "-d",
            env["POSTGRES_DB"],
            "-v",
            "ON_ERROR_STOP=1",
            "-t",
            "-A",
            "-f",
            tmp_path,
        ],
        capture_output=True,
        text=True,
        env={**env, "PGPASSWORD": env["POSTGRES_PASSWORD"]},
    )
    return proc.stdout + proc.stderr, proc.returncode


async def _count_rehearsal_logs() -> int:
    conn = await asyncpg.connect(_dsn())
    try:
        return await conn.fetchval(
            "SELECT COUNT(*) FROM product_change_logs WHERE reason = $1",
            REHEARSAL_REASON,
        )
    finally:
        await conn.close()


async def _product_names() -> dict[int, str]:
    conn = await asyncpg.connect(_dsn())
    try:
        rows = await conn.fetch("SELECT id, name FROM products ORDER BY id")
        return {r["id"]: r["name"] for r in rows}
    finally:
        await conn.close()


INJECTIONS = [
    "after_first_update",
    "mid_cohort",
    "after_all_updates",
    "during_logs",
    "after_all_logs",
    "validation_failure",
]


@pytest.fixture
def p2e_seed(override_database):
    prestate, catalog = asyncio.run(_seed_products())
    catalog_norm = [(pid, name) for pid, name in catalog]
    return prestate, catalog_norm


@pytest.mark.parametrize("failure", INJECTIONS)
def test_failure_injection_leaves_no_persistent_writes(p2e_seed, failure: str):
    prestate, catalog_norm = p2e_seed
    before_names = asyncio.run(_product_names())
    before_logs = asyncio.run(_count_rehearsal_logs())
    sql = build_rehearsal_sql(
        prestate,
        catalog_norm_rows=catalog_norm,
        failure_injection=failure,
    )
    _run_psql_script(sql)
    after_names = asyncio.run(_product_names())
    after_logs = asyncio.run(_count_rehearsal_logs())
    assert after_names == before_names
    assert after_logs == before_logs


def test_identity_drift_simulation_blocks_successful_rehearsal(p2e_seed):
    prestate, catalog_norm = p2e_seed
    sql = build_rehearsal_sql(
        prestate,
        catalog_norm_rows=catalog_norm,
        failure_injection="identity_drift_simulation",
    )
    stdout, rc = _run_psql_script(sql)
    assert rc == 0, stdout[-2000:]
    metrics, log_rows = parse_rehearsal_stdout(stdout)
    assert metrics["in_tx_identity_drift"] > 0
    assert metrics["updates_exact"] == 0
    assert metrics["rehearsal_logs_exact"] == 0
    summary, _ = audit_rehearsal_logs(prestate, log_rows)
    assert summary["actual_rows"] == 0


def test_successful_mini_rehearsal_couples_logs(p2e_seed):
    prestate, catalog_norm = p2e_seed
    sql = build_rehearsal_sql(prestate, catalog_norm_rows=catalog_norm)
    stdout, rc = _run_psql_script(sql)
    assert rc == 0, stdout[-2000:]
    metrics, log_rows = parse_rehearsal_stdout(stdout)
    assert metrics["updates_exact"] == len(prestate)
    assert metrics["rehearsal_logs_exact"] == len(prestate)
    summary, _ = audit_rehearsal_logs(prestate, log_rows)
    assert summary["actual_log_row_mismatches"] == 0
    assert asyncio.run(_count_rehearsal_logs()) == 0
