"""PT-W1 Product Type runtime core — model, FK, integrity (KB-PT-01 / ADR-015)."""

from __future__ import annotations

import asyncio
import inspect

import pytest
from app.db.models import ProductType, ProductTypeStatus
from app.db.models.product import Category, Product
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from tests.conftest import USE_POSTGRES_TESTS, TestingSessionLocal

client = TestClient(app)


def _run(coro):
    return asyncio.run(coro)


async def _enable_fk(session) -> None:
    if not USE_POSTGRES_TESTS:
        await session.execute(text("PRAGMA foreign_keys=ON"))


def test_product_type_create_required_fields():
    async def body():
        async with TestingSessionLocal() as session:
            pt = ProductType(
                code="GEN_CALIPER",
                slug="general-purpose-caliper",
                name_fa="کولیس عمومی",
                name_en="General-purpose Caliper",
                status=ProductTypeStatus.ACTIVE.value,
            )
            session.add(pt)
            await session.commit()
            await session.refresh(pt)
            assert pt.id is not None
            assert pt.code == "GEN_CALIPER"
            assert pt.status == "active"
            assert pt.created_at is not None

    _run(body())


def test_product_type_code_uniqueness():
    async def body():
        async with TestingSessionLocal() as session:
            session.add(
                ProductType(
                    code="DUP_CODE",
                    slug="dup-code-a",
                    name_fa="الف",
                    status=ProductTypeStatus.DRAFT.value,
                )
            )
            await session.commit()
            session.add(
                ProductType(
                    code="DUP_CODE",
                    slug="dup-code-b",
                    name_fa="ب",
                    status=ProductTypeStatus.DRAFT.value,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()

    _run(body())


def test_product_type_slug_uniqueness():
    async def body():
        async with TestingSessionLocal() as session:
            session.add(
                ProductType(
                    code="SLUG_A",
                    slug="same-slug",
                    name_fa="الف",
                    status=ProductTypeStatus.DRAFT.value,
                )
            )
            await session.commit()
            session.add(
                ProductType(
                    code="SLUG_B",
                    slug="same-slug",
                    name_fa="ب",
                    status=ProductTypeStatus.DRAFT.value,
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()

    _run(body())


@pytest.mark.parametrize("status", ["draft", "active", "retired"])
def test_product_type_valid_lifecycle_statuses(status: str):
    async def body():
        async with TestingSessionLocal() as session:
            pt = ProductType(
                code=f"ST_{status}",
                slug=f"status-{status}",
                name_fa=status,
                status=status,
            )
            session.add(pt)
            await session.commit()
            assert pt.status == status

    _run(body())


def test_product_type_invalid_lifecycle_status_rejected():
    async def body():
        async with TestingSessionLocal() as session:
            session.add(
                ProductType(
                    code="BAD_STATUS",
                    slug="bad-status",
                    name_fa="بد",
                    status="deleted",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()

    _run(body())


def test_product_may_exist_with_null_product_type(super_admin_headers, valid_product_data):
    created = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "PT-NULL-1"},
        headers=super_admin_headers,
    )
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]

    async def body():
        async with TestingSessionLocal() as session:
            product = await session.get(Product, product_id)
            assert product is not None
            assert product.product_type_id is None

    _run(body())


def test_product_can_reference_product_type(super_admin_headers, valid_product_data):
    async def setup_and_assign():
        async with TestingSessionLocal() as session:
            pt = ProductType(
                code="REF_TYPE",
                slug="ref-type",
                name_fa="مرجع",
                status=ProductTypeStatus.ACTIVE.value,
            )
            session.add(pt)
            await session.flush()
            pt_id = pt.id
            await session.commit()
            return pt_id

    pt_id = _run(setup_and_assign())
    created = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "PT-REF-1"},
        headers=super_admin_headers,
    )
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]

    async def assign():
        async with TestingSessionLocal() as session:
            product = await session.get(Product, product_id)
            product.product_type_id = pt_id
            await session.commit()
            await session.refresh(product)
            assert product.product_type_id == pt_id

    _run(assign())


def test_product_type_delete_restricted_while_referenced(
    super_admin_headers, valid_product_data
):
    async def setup():
        async with TestingSessionLocal() as session:
            await _enable_fk(session)
            pt = ProductType(
                code="RESTRICT_T",
                slug="restrict-t",
                name_fa="محدود",
                status=ProductTypeStatus.ACTIVE.value,
            )
            session.add(pt)
            await session.flush()
            pt_id = pt.id
            await session.commit()
            return pt_id

    pt_id = _run(setup())
    created = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "PT-REST-1"},
        headers=super_admin_headers,
    )
    assert created.status_code == 201
    product_id = created.json()["id"]

    async def assign_and_delete():
        async with TestingSessionLocal() as session:
            await _enable_fk(session)
            product = await session.get(Product, product_id)
            product.product_type_id = pt_id
            await session.commit()

        async with TestingSessionLocal() as session:
            await _enable_fk(session)
            pt = await session.get(ProductType, pt_id)
            await session.delete(pt)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

        async with TestingSessionLocal() as session:
            product = await session.get(Product, product_id)
            assert product is not None
            assert product.product_type_id == pt_id
            assert await session.get(ProductType, pt_id) is not None

    _run(assign_and_delete())


def test_product_type_delete_restricted_when_products_collection_loaded(
    super_admin_headers, valid_product_data
):
    """Loaded ProductType.products must not cause silent FK-nulling on delete (AC-01)."""

    async def setup():
        async with TestingSessionLocal() as session:
            await _enable_fk(session)
            pt = ProductType(
                code="LOADED_T",
                slug="loaded-t",
                name_fa="بارگذاری‌شده",
                status=ProductTypeStatus.ACTIVE.value,
            )
            session.add(pt)
            await session.flush()
            pt_id = pt.id
            await session.commit()
            return pt_id

    pt_id = _run(setup())
    created = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "PT-LOADED-1"},
        headers=super_admin_headers,
    )
    assert created.status_code == 201
    product_id = created.json()["id"]

    async def assign_load_delete_verify():
        async with TestingSessionLocal() as session:
            await _enable_fk(session)
            product = await session.get(Product, product_id)
            product.product_type_id = pt_id
            await session.commit()

        async with TestingSessionLocal() as session:
            await _enable_fk(session)
            result = await session.execute(
                select(ProductType)
                .where(ProductType.id == pt_id)
                .options(selectinload(ProductType.products))
            )
            pt = result.scalar_one()
            assert len(pt.products) == 1
            assert pt.products[0].id == product_id
            await session.delete(pt)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

        async with TestingSessionLocal() as session:
            product = await session.get(Product, product_id)
            assert product is not None
            assert product.product_type_id == pt_id
            assert await session.get(ProductType, pt_id) is not None

    _run(assign_load_delete_verify())


def test_deleting_product_does_not_delete_product_type(
    super_admin_headers, valid_product_data
):
    async def setup():
        async with TestingSessionLocal() as session:
            pt = ProductType(
                code="KEEP_TYPE",
                slug="keep-type",
                name_fa="بماند",
                status=ProductTypeStatus.ACTIVE.value,
            )
            session.add(pt)
            await session.flush()
            pt_id = pt.id
            await session.commit()
            return pt_id

    pt_id = _run(setup())
    created = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "PT-DEL-P"},
        headers=super_admin_headers,
    )
    assert created.status_code == 201
    product_id = created.json()["id"]

    async def assign_delete_product_check_type():
        async with TestingSessionLocal() as session:
            product = await session.get(Product, product_id)
            product.product_type_id = pt_id
            await session.commit()

        async with TestingSessionLocal() as session:
            product = await session.get(Product, product_id)
            await session.delete(product)
            await session.commit()

        async with TestingSessionLocal() as session:
            assert await session.get(ProductType, pt_id) is not None

    _run(assign_delete_product_check_type())


def test_changing_category_does_not_change_product_type(
    super_admin_headers, valid_product_data
):
    """Category mutation must not touch product_type_id (ORM-level independence)."""

    async def setup():
        async with TestingSessionLocal() as session:
            pt = ProductType(
                code="CAT_IND",
                slug="cat-ind",
                name_fa="مستقل",
                status=ProductTypeStatus.ACTIVE.value,
            )
            session.add(pt)
            await session.flush()
            pt_id = pt.id
            await session.commit()
            return pt_id

    pt_id = _run(setup())
    created = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "PT-CAT-1"},
        headers=super_admin_headers,
    )
    assert created.status_code == 201
    product_id = created.json()["id"]

    async def assign_and_change_category():
        async with TestingSessionLocal() as session:
            product = await session.get(Product, product_id)
            product.product_type_id = pt_id
            original_category = product.category_id
            sibling = Category(
                name="Alternate Leaf",
                parent_id=2,
                slug="alternate-leaf-ptw1",
            )
            session.add(sibling)
            await session.flush()
            product.category_id = sibling.id
            await session.commit()
            await session.refresh(product)
            assert product.category_id != original_category
            assert product.product_type_id == pt_id

    _run(assign_and_change_category())


def test_no_product_type_seed_and_no_backfill(super_admin_headers, valid_product_data):
    client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "PT-SEED-1"},
        headers=super_admin_headers,
    )

    async def body():
        async with TestingSessionLocal() as session:
            pt_count = await session.scalar(select(func.count()).select_from(ProductType))
            non_null = await session.scalar(
                select(func.count())
                .select_from(Product)
                .where(Product.product_type_id.is_not(None))
            )
            assert pt_count == 0
            assert non_null == 0

    _run(body())


def test_no_readout_column_or_profile_on_product_types():
    mapper = sa_inspect(ProductType)
    column_names = {c.key for c in mapper.columns}
    forbidden = {
        "readout",
        "readout_profile",
        "profile_json",
        "attributes",
        "definition",
        "taxonomy_node_id",
        "category_id",
        "spec_template_key",
        "parent_product_type_id",
    }
    assert column_names.isdisjoint(forbidden)
    expected = {
        "id",
        "code",
        "slug",
        "name_fa",
        "name_en",
        "description",
        "status",
        "created_at",
        "updated_at",
    }
    assert expected.issubset(column_names)


def test_specifications_unchanged_when_assigning_type(
    super_admin_headers, valid_product_data
):
    payload = {
        **valid_product_data,
        "sku": "PT-JSONB-1",
        "specifications": {
            "technical_specs": {"range": "0-200mm", "accuracy": "keep-me"},
            "features": {"waterproof": True},
            "dimensions": {"L_mm": 1.0},
            "optional_accessories": ["box"],
        },
    }
    created = client.post(
        "/api/v1/products/",
        json=payload,
        headers=super_admin_headers,
    )
    assert created.status_code == 201
    product_id = created.json()["id"]

    async def assign():
        async with TestingSessionLocal() as session:
            product = await session.get(Product, product_id)
            before = dict(product.specifications)
            pt = ProductType(
                code="JSONB_T",
                slug="jsonb-t",
                name_fa="جیسون",
                status=ProductTypeStatus.ACTIVE.value,
            )
            session.add(pt)
            await session.flush()
            product.product_type_id = pt.id
            await session.commit()
            await session.refresh(product)
            assert product.specifications == before

    _run(assign())


def test_no_public_product_type_endpoint_introduced():
    routes = {getattr(route, "path", None) for route in app.routes}
    offending = {
        path
        for path in routes
        if path
        and (
            "/product-types" in path
            or "/product_types" in path
            or path.rstrip("/").endswith("/product-type")
        )
    }
    assert offending == set()
    import app.api.v1 as v1_module

    src = inspect.getsource(v1_module)
    assert "product_type" not in src.lower()
    assert "product-types" not in src.lower()


def test_migration_fk_has_no_cascade_or_set_null():
    from pathlib import Path

    migration = Path("alembic/versions/e6f7a8b9c0d1_product_types_pt_w1.py").read_text()
    assert "fk_products_product_type_id_product_types" in migration
    assert "ondelete=" not in migration.lower()
    assert "SET NULL" not in migration
    assert "ON DELETE CASCADE" not in migration.upper()
    assert "op.execute(" not in migration
    assert "INSERT INTO" not in migration.upper()
