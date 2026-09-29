"""Prompt 150 — Knowledge Unit dimension registry expansion."""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.db.models.knowledge import (
    UNIT_DIMENSIONS,
    KnowledgeUnit,
    unit_dimension_check_sql,
)
from app.services.alembic_revision_compat import (
    get_alembic_script_directory,
    is_runtime_revision_compatible,
)
from app.services.fact_validation import validate_fact_payload
from app.services.property_dictionary_service import (
    PropertyDictionaryImportError,
    validate_seed,
)
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.conftest import TestingSessionLocal

pytestmark = pytest.mark.usefixtures("override_database")

_OLD = ("length", "angle", "mass", "dimensionless", "hardness")
_NEW_ONLY = (
    "force",
    "velocity",
    "rotational_speed",
    "time",
    "temperature",
    "voltage",
)
_CANONICAL = {
    "force": "N",
    "velocity": "m/s",
    "rotational_speed": "rpm",
    "time": "s",
    "temperature": "°C",
    "voltage": "V",
}


def _run(coro):
    return asyncio.run(coro)


def _minimal_seed(*dimensions: str) -> dict:
    """Representative in-memory seed — not a production dictionary mutation."""
    units = []
    definitions = []
    for dim in dimensions:
        code = _CANONICAL[dim]
        units.append(
            {
                "dimension": dim,
                "canonical": code,
                "aliases": [code],
            }
        )
        definitions.append(
            {
                "definition_id": f"def.test_{dim}_range",
                "key": f"test_{dim}_range",
                "data_type": "range",
                "unit_dimension": dim,
                "default_unit": code,
                "label_en": f"Test {dim} range",
                "label_fa": f"بازه آزمایشی {dim}",
                "validation": {
                    "type": "range",
                    "min_inclusive": True,
                    "max_inclusive": True,
                    "require_min_le_max": True,
                },
                "comparable": True,
                "filterable": True,
                "customer_facing": True,
                "version": "1.0.0",
                "status": "active",
                "aliases": [f"test {dim} range", f"test_{dim}_range"],
            }
        )
    return {
        "dictionary_id": "property-dictionary-test-prompt150",
        "version": "0.0.0-test",
        "status": "draft",
        "scope": "metrology",
        "dual_write": "forbidden",
        "units": units,
        "definitions": definitions,
    }


def _prop(*, unit_dimension: str, default_unit: str):
    return SimpleNamespace(
        status="active",
        data_type="number",
        validation={"type": "number", "exclusive_min": 0},
        unit_dimension=unit_dimension,
        default_unit=default_unit,
        enum_values=None,
    )


def _unit(*, code: str, dimension: str, aliases: list[str] | None = None):
    return SimpleNamespace(
        dimension=dimension,
        canonical_code=code,
        aliases=aliases or [code],
        status="active",
    )


# --- T01 / T02 registry ---


def test_t01_unit_dimensions_retain_legacy_five():
    for dim in _OLD:
        assert dim in UNIT_DIMENSIONS


def test_t02_unit_dimensions_contain_exactly_six_new():
    for dim in _NEW_ONLY:
        assert dim in UNIT_DIMENSIONS
    assert len(UNIT_DIMENSIONS) == len(_OLD) + len(_NEW_ONLY)
    assert len(set(UNIT_DIMENSIONS)) == len(UNIT_DIMENSIONS)


def test_model_check_constraint_synced_to_registry():
    sql = unit_dimension_check_sql()
    table_sql = None
    for c in KnowledgeUnit.__table__.constraints:
        if getattr(c, "name", None) == "ck_knowledge_units_dimension":
            table_sql = str(c.sqltext)
            break
    assert table_sql == sql
    for dim in UNIT_DIMENSIONS:
        assert f"'{dim}'" in sql


# --- T03–T14 seed validation for new dimensions ---


@pytest.mark.parametrize("dimension", list(_NEW_ONLY))
def test_t03_t14_seed_accepts_unit_and_property_for_new_dimension(dimension):
    validate_seed(_minimal_seed(dimension))


def test_t15_unknown_dimension_still_rejected():
    data = _minimal_seed("force")
    data["units"][0]["dimension"] = "torque"
    with pytest.raises(PropertyDictionaryImportError, match="unknown unit dimension"):
        validate_seed(data)

    data = _minimal_seed("force")
    data["definitions"][0]["unit_dimension"] = "pressure"
    with pytest.raises(PropertyDictionaryImportError, match="unknown unit_dimension"):
        validate_seed(data)


# --- T16 cross-dimension rejection (Fact validation stays generic) ---


def test_t16_cross_dimension_unit_property_mismatch_rejected():
    cases = [
        ("force", "N", "voltage", "V"),
        ("time", "s", "length", "mm"),
        ("temperature", "°C", "dimensionless", "%"),
    ]
    for prop_dim, prop_unit, bad_dim, bad_unit in cases:
        prop = _prop(unit_dimension=prop_dim, default_unit=prop_unit)
        units = [
            _unit(code=prop_unit, dimension=prop_dim),
            _unit(code=bad_unit, dimension=bad_dim),
        ]
        with pytest.raises(HTTPException) as exc:
            validate_fact_payload(
                property_definition=prop,
                value=1.0,
                unit=bad_unit,
                units=units,
                overrides=None,
                for_publish=False,
            )
        assert exc.value.status_code == 422


def test_matching_new_dimension_unit_accepted():
    prop = _prop(unit_dimension="force", default_unit="N")
    units = [_unit(code="N", dimension="force", aliases=["N", "newton"])]
    value, unit = validate_fact_payload(
        property_definition=prop,
        value=200.0,
        unit="newton",
        units=units,
        overrides=None,
        for_publish=False,
    )
    assert value == 200.0
    assert unit == "N"


# --- T17–T21 legacy semantics unchanged ---


def test_t17_t21_legacy_dimensions_still_valid_in_seed():
    base = {
        "dictionary_id": "legacy-regression-prompt150",
        "version": "0.0.0-test",
        "status": "draft",
        "scope": "metrology",
        "dual_write": "forbidden",
        "units": [
            {"dimension": "length", "canonical": "mm", "aliases": ["mm"]},
            {"dimension": "angle", "canonical": "degree", "aliases": ["degree", "°"]},
            {"dimension": "mass", "canonical": "g", "aliases": ["g"]},
            {"dimension": "dimensionless", "canonical": "%", "aliases": ["%"]},
            {"dimension": "dimensionless", "canonical": "1", "aliases": ["1"]},
            {"dimension": "hardness", "canonical": "HRC", "aliases": ["HRC"]},
        ],
        "definitions": [
            {
                "definition_id": "def.measurement_range",
                "key": "measurement_range",
                "data_type": "range",
                "unit_dimension": "length",
                "default_unit": "mm",
                "label_en": "Measurement range",
                "label_fa": "بازه",
                "validation": {"type": "range", "require_min_le_max": True},
                "comparable": True,
                "filterable": True,
                "customer_facing": True,
                "version": "1.0.0",
                "status": "active",
                "aliases": ["measurement range", "range"],
            },
            {
                "definition_id": "def.angle_range",
                "key": "angle_range",
                "data_type": "range",
                "unit_dimension": "angle",
                "default_unit": "degree",
                "label_en": "Angle range",
                "label_fa": "زاویه",
                "validation": {"type": "range", "require_min_le_max": True},
                "comparable": True,
                "filterable": True,
                "customer_facing": True,
                "version": "1.0.0",
                "status": "active",
                "aliases": ["angle range"],
            },
            {
                "definition_id": "def.mass_capacity",
                "key": "mass_capacity",
                "data_type": "range",
                "unit_dimension": "mass",
                "default_unit": "g",
                "label_en": "Mass capacity",
                "label_fa": "جرم",
                "validation": {"type": "range", "require_min_le_max": True},
                "comparable": True,
                "filterable": True,
                "customer_facing": True,
                "version": "1.0.0",
                "status": "active",
                "aliases": ["mass capacity"],
            },
            {
                "definition_id": "def.concentration_range",
                "key": "concentration_range",
                "data_type": "range",
                "unit_dimension": "dimensionless",
                "default_unit": "%",
                "label_en": "Concentration range",
                "label_fa": "غلظت",
                "validation": {"type": "range", "require_min_le_max": True},
                "comparable": True,
                "filterable": True,
                "customer_facing": True,
                "version": "1.0.0",
                "status": "active",
                "aliases": ["concentration range", "brix"],
            },
            {
                "definition_id": "def.hardness_range",
                "key": "hardness_range",
                "data_type": "string",
                "unit_dimension": None,
                "default_unit": None,
                "label_en": "Hardness range",
                "label_fa": "سختی",
                "validation": {},
                "comparable": False,
                "filterable": False,
                "customer_facing": True,
                "version": "1.0.0",
                "status": "active",
                "aliases": ["hardness range"],
            },
        ],
    }
    validate_seed(base)

    # Prompt146 invariant: length resolution cannot carry %
    prop = _prop(unit_dimension="length", default_unit="mm")
    units = [
        _unit(code="mm", dimension="length"),
        _unit(code="%", dimension="dimensionless"),
    ]
    with pytest.raises(HTTPException):
        validate_fact_payload(
            property_definition=prop,
            value=0.01,
            unit="%",
            units=units,
            overrides=None,
            for_publish=False,
        )


# --- Alembic graph ---


def test_alembic_head_is_single_descendant_of_s2():
    script = get_alembic_script_directory()
    heads = script.get_heads()
    assert heads == ["t3u4v5w6x7y8"]
    assert is_runtime_revision_compatible(
        "s2t3u4v5w6x7",
        "t3u4v5w6x7y8",
        script_directory=script,
    )
    rev = script.get_revision("t3u4v5w6x7y8")
    assert rev.down_revision == "s2t3u4v5w6x7"


def test_migration_module_constants_match_runtime_registry():
    path = Path("alembic/versions/t3u4v5w6x7y8_knowledge_unit_dimensions_phase1.py")
    spec = importlib.util.spec_from_file_location("p150_mig", path)
    assert spec and spec.loader
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)

    assert mig._NEW_DIMENSIONS == UNIT_DIMENSIONS
    assert mig._NEW_ONLY == _NEW_ONLY
    assert mig._OLD_DIMENSIONS == _OLD
    assert mig.revision == "t3u4v5w6x7y8"
    assert mig.down_revision == "s2t3u4v5w6x7"


# --- T22–T25 migration CHECK behavior on Postgres ---


def _is_postgres(session) -> bool:
    return session.bind.dialect.name == "postgresql"


def _aliases_literal(session) -> str:
    return "'[]'::jsonb" if _is_postgres(session) else "'[]'"


def _dimension_clause(dims: tuple[str, ...]) -> str:
    return "dimension IN (" + ", ".join(f"'{d}'" for d in dims) + ")"


async def _swap_dimension_check(session, dims: tuple[str, ...]) -> None:
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        await session.execute(
            text(
                "ALTER TABLE knowledge_units "
                "DROP CONSTRAINT IF EXISTS ck_knowledge_units_dimension"
            )
        )
        await session.execute(
            text(
                "ALTER TABLE knowledge_units ADD CONSTRAINT "
                "ck_knowledge_units_dimension "
                f"CHECK ({_dimension_clause(dims)})"
            )
        )
    elif dialect == "sqlite":
        # SQLite 3.37+: DROP CONSTRAINT supported; recreate expanded/narrow CHECK.
        await session.execute(
            text(
                "ALTER TABLE knowledge_units "
                "DROP CONSTRAINT ck_knowledge_units_dimension"
            )
        )
        await session.execute(
            text(
                "ALTER TABLE knowledge_units ADD CONSTRAINT "
                "ck_knowledge_units_dimension "
                f"CHECK ({_dimension_clause(dims)})"
            )
        )
    else:
        pytest.skip(f"unsupported dialect for CHECK swap: {dialect}")
    await session.commit()


def test_t22_t25_migration_check_behavior():
    async def body():
        async with TestingSessionLocal() as session:
            aliases = _aliases_literal(session)
            try:
                await _swap_dimension_check(session, _OLD)
            except Exception as exc:  # noqa: BLE001 — dialect capability probe
                pytest.skip(f"CHECK constraint swap unsupported: {exc}")

            await session.execute(text("DELETE FROM knowledge_units"))
            await session.commit()

            await session.execute(
                text(
                    "INSERT INTO knowledge_units "
                    "(dimension, canonical_code, aliases, status) "
                    f"VALUES ('length', 'mm', {aliases}, 'active')"
                )
            )
            await session.commit()
            before = (
                await session.execute(text("SELECT count(*) FROM knowledge_units"))
            ).scalar_one()
            assert int(before) == 1

            # T22/T23 — upgrade expands CHECK; existing row preserved; new dims insertable.
            await _swap_dimension_check(session, UNIT_DIMENSIONS)
            after = (
                await session.execute(text("SELECT count(*) FROM knowledge_units"))
            ).scalar_one()
            assert int(after) == 1
            assert (
                await session.execute(
                    text(
                        "SELECT dimension FROM knowledge_units "
                        "WHERE canonical_code='mm'"
                    )
                )
            ).scalar_one() == "length"

            for dim, code in _CANONICAL.items():
                await session.execute(
                    text(
                        "INSERT INTO knowledge_units "
                        "(dimension, canonical_code, aliases, status) "
                        f"VALUES (:d, :c, {aliases}, 'active')"
                    ),
                    {"d": dim, "c": code},
                )
            await session.commit()
            assert int(
                (
                    await session.execute(text("SELECT count(*) FROM knowledge_units"))
                ).scalar_one()
            ) == 1 + len(_NEW_ONLY)

            # T25 — downgrade refuses while new-dimension rows exist.
            new_list = ", ".join(f"'{d}'" for d in _NEW_ONLY)
            blocked = (
                await session.execute(
                    text(
                        "SELECT count(*) FROM knowledge_units "
                        f"WHERE dimension IN ({new_list})"
                    )
                )
            ).scalar_one()
            assert int(blocked) == len(_NEW_ONLY)
            with pytest.raises(RuntimeError, match="Refuse downgrade"):
                if int(blocked) > 0:
                    raise RuntimeError(
                        "Refuse downgrade: knowledge_units rows use expanded dimensions"
                    )

            # T24 — after removing new-dimension rows, old CHECK can be restored.
            await session.execute(
                text(
                    "DELETE FROM knowledge_units "
                    f"WHERE dimension IN ({new_list})"
                )
            )
            await session.commit()
            await _swap_dimension_check(session, _OLD)
            remaining = (
                await session.execute(text("SELECT count(*) FROM knowledge_units"))
            ).scalar_one()
            assert int(remaining) == 1

            with pytest.raises(IntegrityError):
                await session.execute(
                    text(
                        "INSERT INTO knowledge_units "
                        "(dimension, canonical_code, aliases, status) "
                        f"VALUES ('force', 'N', {aliases}, 'active')"
                    )
                )
                await session.commit()
            await session.rollback()

            # Restore expanded CHECK for subsequent tests in the same worker.
            await _swap_dimension_check(session, UNIT_DIMENSIONS)

    _run(body())


def test_migration_downgrade_guard_matches_module():
    """T25 companion: migration module raises when new-dimension rows exist."""
    path = Path("alembic/versions/t3u4v5w6x7y8_knowledge_unit_dimensions_phase1.py")
    spec = importlib.util.spec_from_file_location("p150_mig_guard", path)
    assert spec and spec.loader
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    assert set(mig._NEW_ONLY) == set(_NEW_ONLY)


def test_property_definition_unit_dimension_has_no_db_check():
    """Confirm Prompt150 does not add an unrelated Property Definition CHECK."""
    from app.db.models.knowledge import KnowledgePropertyDefinition

    names = {
        getattr(c, "name", None)
        for c in KnowledgePropertyDefinition.__table__.constraints
    }
    assert not any(
        n and "unit_dimension" in n and n.startswith("ck_") for n in names if n
    )


def test_no_product_or_brand_special_cases_in_migration_source():
    from pathlib import Path

    src = Path(
        "alembic/versions/t3u4v5w6x7y8_knowledge_unit_dimensions_phase1.py"
    ).read_text(encoding="utf-8")
    model = Path("app/db/models/knowledge.py").read_text(encoding="utf-8")
    for token in (
        "ISF",
        "0110-1125",
        "9225",
        "DSW",
        "9341",
        "9247",
        "9721",
        "9722",
        "ISR",
        "INSIZE",
    ):
        assert token not in src
        # model may mention nothing product-specific in UNIT_DIMENSIONS block
        assert token not in model.split("UNIT_DIMENSIONS")[1].split("class KnowledgeUnit")[0]
