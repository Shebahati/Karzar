"""Property Dictionary runtime (Prompt 11A) — models, import, admin read API."""

from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path

import pytest
from app.api.deps import get_current_super_admin
from app.core.security import create_access_token
from app.db.models import Product
from app.db.models.knowledge import (
    KnowledgePropertyAlias,
    KnowledgePropertyDefinition,
    KnowledgeUnit,
)
from app.db.models.product import Brand, Category
from app.main import app
from app.services.property_dictionary_service import (
    DEFAULT_SEED_PATH,
    PropertyDictionaryImportError,
    import_property_dictionary,
    normalize_alias,
    validate_seed,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from tests.conftest import TestingSessionLocal, customer_auth_headers, override_super_admin

client = TestClient(app)
SEED = Path("docs/architecture/specs/seeds/property-dictionary-v0-metrology.json")


def _run(coro):
    return asyncio.run(coro)


def test_normalize_alias_nfc_strip_casefold():
    assert normalize_alias("  Accuracy ") == "accuracy"
    assert normalize_alias("دقت") == normalize_alias("  دقت  ")


def test_seed_validate_rejects_bad_datatype():
    data = json.loads(SEED.read_text(encoding="utf-8"))
    data["definitions"][0]["data_type"] = "not_a_type"
    with pytest.raises(PropertyDictionaryImportError, match="invalid data_type"):
        validate_seed(data)


def test_seed_validate_rejects_cross_definition_alias_collision():
    data = json.loads(SEED.read_text(encoding="utf-8"))
    data["definitions"][0]["aliases"].append("UNIQUE_COLLISION_TOKEN")
    data["definitions"][1]["aliases"].append("unique_collision_token")
    with pytest.raises(PropertyDictionaryImportError, match="alias collision"):
        validate_seed(data)


def test_import_idempotent_and_counts():
    async def body():
        async with TestingSessionLocal() as session:
            first = await import_property_dictionary(session, seed_path=SEED)
            await session.commit()
            assert first["counters"]["units_created"] == 2
            assert first["counters"]["properties_created"] == 9
            assert first["counters"]["aliases_created"] == 36
            assert first["counters"]["units_updated"] == 0
            assert first["counters"]["properties_updated"] == 0
            assert first["counters"]["aliases_updated"] == 0
            assert first["counters"]["failed"] == 0

            unit_ids = (
                await session.execute(
                    select(KnowledgeUnit.id).order_by(KnowledgeUnit.id)
                )
            ).scalars().all()
            def_rows = (
                await session.execute(
                    select(
                        KnowledgePropertyDefinition.id,
                        KnowledgePropertyDefinition.definition_id,
                    ).order_by(KnowledgePropertyDefinition.id)
                )
            ).all()
            alias_ids = (
                await session.execute(
                    select(KnowledgePropertyAlias.id).order_by(KnowledgePropertyAlias.id)
                )
            ).scalars().all()

            second = await import_property_dictionary(session, seed_path=SEED)
            await session.commit()
            c2 = second["counters"]
            assert c2["units_created"] == 0
            assert c2["properties_created"] == 0
            assert c2["aliases_created"] == 0
            assert c2["units_updated"] == 0
            assert c2["properties_updated"] == 0
            assert c2["aliases_updated"] == 0
            assert c2["units_unchanged"] == 2
            assert c2["properties_unchanged"] == 9
            assert c2["aliases_unchanged"] == 36
            assert c2["failed"] == 0

            unit_ids_2 = (
                await session.execute(
                    select(KnowledgeUnit.id).order_by(KnowledgeUnit.id)
                )
            ).scalars().all()
            def_rows_2 = (
                await session.execute(
                    select(
                        KnowledgePropertyDefinition.id,
                        KnowledgePropertyDefinition.definition_id,
                    ).order_by(KnowledgePropertyDefinition.id)
                )
            ).all()
            alias_ids_2 = (
                await session.execute(
                    select(KnowledgePropertyAlias.id).order_by(KnowledgePropertyAlias.id)
                )
            ).scalars().all()
            assert unit_ids == unit_ids_2
            assert def_rows == def_rows_2
            assert alias_ids == alias_ids_2

            units = int(
                (
                    await session.execute(select(func.count()).select_from(KnowledgeUnit))
                ).scalar_one()
            )
            defs = int(
                (
                    await session.execute(
                        select(func.count()).select_from(KnowledgePropertyDefinition)
                    )
                ).scalar_one()
            )
            aliases = int(
                (
                    await session.execute(
                        select(func.count()).select_from(KnowledgePropertyAlias)
                    )
                ).scalar_one()
            )
            assert (units, defs, aliases) == (2, 9, 36)

    _run(body())


def test_dry_run_does_not_mutate():
    async def body():
        async with TestingSessionLocal() as session:
            before = int(
                (
                    await session.execute(select(func.count()).select_from(KnowledgeUnit))
                ).scalar_one()
            )
            result = await import_property_dictionary(
                session, seed_path=SEED, dry_run=True
            )
            assert result["dry_run"] is True
            assert result["counters"]["units_scanned"] == 2
            after = int(
                (
                    await session.execute(select(func.count()).select_from(KnowledgeUnit))
                ).scalar_one()
            )
            assert after == before == 0

    _run(body())


def test_import_does_not_create_template_tables_or_touch_products():
    async def body():
        async with TestingSessionLocal() as session:
            cat = (
                await session.execute(select(Category).where(Category.slug == "0-150mm-range"))
            ).scalar_one()
            brand = (
                await session.execute(select(Brand).where(Brand.slug == "testbrand"))
            ).scalar_one()
            specs = {
                "technical_specs": {"range": "0-150", "marker": "preserve-me"},
                "features": {},
                "dimensions": {},
                "optional_accessories": [],
            }
            product = Product(
                name="11A Guard Product",
                slug="11a-guard-product",
                sku="11A-GUARD-001",
                category_id=cat.id,
                brand_id=brand.id,
                base_price=1000,
                specifications=specs,
            )
            session.add(product)
            await session.commit()
            product_id = product.id
            specs_before = copy.deepcopy(product.specifications)

            await import_property_dictionary(session, seed_path=SEED)
            await session.commit()

            await session.refresh(product)
            assert product.specifications == specs_before
            assert product.id == product_id

            from app.db.models import Base

            mapped = {t.name for t in Base.metadata.tables.values()}
            assert "knowledge_spec_templates" not in mapped
            assert "knowledge_template_properties" not in mapped
            assert "knowledge_units" in mapped
            assert "knowledge_property_definitions" in mapped
            assert "knowledge_property_aliases" in mapped

    _run(body())


def test_import_rollback_on_invalid_seed_mutates_nothing():
    async def body():
        async with TestingSessionLocal() as session:
            await import_property_dictionary(session, seed_path=SEED)
            await session.commit()
            before_defs = int(
                (
                    await session.execute(
                        select(func.count()).select_from(KnowledgePropertyDefinition)
                    )
                ).scalar_one()
            )

            bad = Path("/tmp/bad-property-dictionary-11a.json")
            data = json.loads(SEED.read_text(encoding="utf-8"))
            data["definitions"][0]["data_type"] = "bogus"
            bad.write_text(json.dumps(data), encoding="utf-8")
            with pytest.raises(PropertyDictionaryImportError):
                await import_property_dictionary(session, seed_path=bad)
            after_defs = int(
                (
                    await session.execute(
                        select(func.count()).select_from(KnowledgePropertyDefinition)
                    )
                ).scalar_one()
            )
            assert after_defs == before_defs

    _run(body())


def test_definition_key_and_alias_uniqueness():
    async def body():
        async with TestingSessionLocal() as session:
            session.add(
                KnowledgePropertyDefinition(
                    definition_id="def.a",
                    key="shared_key",
                    data_type="string",
                    label_en="A",
                    label_fa="الف",
                    validation={},
                    version="1.0.0",
                    status="draft",
                )
            )
            await session.commit()
            session.add(
                KnowledgePropertyDefinition(
                    definition_id="def.b",
                    key="shared_key",
                    data_type="string",
                    label_en="B",
                    label_fa="ب",
                    validation={},
                    version="1.0.0",
                    status="draft",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            session.add(
                KnowledgePropertyDefinition(
                    definition_id="def.c",
                    key="other_key",
                    data_type="string",
                    label_en="C",
                    label_fa="ج",
                    validation={},
                    version="1.0.0",
                    status="active",
                )
            )
            await session.flush()
            session.add(
                KnowledgePropertyAlias(
                    definition_id="def.c",
                    alias="X",
                    alias_normalized="x",
                    source_kind="seed_inline",
                    status="active",
                )
            )
            await session.commit()
            session.add(
                KnowledgePropertyAlias(
                    definition_id="def.c",
                    alias="x",
                    alias_normalized="x",
                    source_kind="seed_inline",
                    status="active",
                )
            )
            with pytest.raises(IntegrityError):
                await session.commit()

    _run(body())


def test_admin_dictionary_api_auth_and_read():
    async def seed():
        async with TestingSessionLocal() as session:
            await import_property_dictionary(session, seed_path=SEED)
            await session.commit()

    _run(seed())

    unauth = client.get("/api/v1/knowledge/dictionary/properties")
    assert unauth.status_code in (401, 403)

    # Customer token must not pass super-admin gate.
    customer = customer_auth_headers("09124444444")
    forbidden = client.get(
        "/api/v1/knowledge/dictionary/properties",
        headers=customer,
    )
    assert forbidden.status_code == 403

    app.dependency_overrides[get_current_super_admin] = override_super_admin
    try:
        headers = {"Authorization": f"Bearer {create_access_token(subject='09120000001')}"}
        props = client.get("/api/v1/knowledge/dictionary/properties", headers=headers)
        assert props.status_code == 200
        body = props.json()
        assert body["total"] == 9
        assert len(body["items"]) == 9
        assert any(i["key"] == "accuracy" for i in body["items"])
        assert any(i.get("aliases") for i in body["items"])

        detail = client.get(
            "/api/v1/knowledge/dictionary/properties/def.accuracy",
            headers=headers,
        )
        assert detail.status_code == 200
        assert detail.json()["key"] == "accuracy"
        assert "دقت" in [a["alias"] for a in detail.json()["aliases"]]

        units = client.get("/api/v1/knowledge/dictionary/units", headers=headers)
        assert units.status_code == 200
        assert units.json()["total"] == 2

        aliases = client.get(
            "/api/v1/knowledge/dictionary/aliases",
            headers=headers,
            params={"q": "accuracy"},
        )
        assert aliases.status_code == 200
        assert aliases.json()["total"] >= 1
    finally:
        app.dependency_overrides.pop(get_current_super_admin, None)


def test_default_seed_path_matches_repo_seed():
    assert DEFAULT_SEED_PATH.as_posix() == SEED.as_posix()


def test_no_http_dictionary_import_route():
    routes = {getattr(r, "path", "") for r in app.routes}
    assert not any("dictionary" in p and "import" in p for p in routes)
    # POST on dictionary list must not exist as write API
    postish = [
        r
        for r in app.routes
        if getattr(r, "path", "").startswith("/api/v1/knowledge/dictionary")
        and getattr(r, "methods", None)
        and "POST" in r.methods
    ]
    assert postish == []
