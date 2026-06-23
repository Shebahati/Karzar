from sqlalchemy.dialects import postgresql

from app.db.models.product import Product
from app.utils.jsonb_filters import build_specification_filters


class TestJsonbFiltersPostgres:
    def test_postgres_exact_match_uses_astext_not_cast(self):
        conditions = build_specification_filters(
            {"technical_specs.range": "0-150mm"},
            dialect_name="postgresql",
        )
        sql = str(
            conditions[0].compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        assert "astext" in sql.lower() or "->>" in sql
        assert "0-150mm" in sql
        assert "CAST" not in sql.upper()

    def test_postgres_icontains_uses_astext(self):
        conditions = build_specification_filters(
            {"technical_specs.range__icontains": "150"},
            dialect_name="postgresql",
        )
        sql = str(
            conditions[0].compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        assert "astext" in sql.lower() or "->>" in sql
        assert "ILIKE" in sql.upper()

    def test_postgres_boolean_uses_astext(self):
        conditions = build_specification_filters(
            {"features.waterproof": True},
            dialect_name="postgresql",
        )
        sql = str(
            conditions[0].compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        assert "astext" in sql.lower() or "->>" in sql
        assert "true" in sql.lower()
