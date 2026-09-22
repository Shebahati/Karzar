"""Catalog / runtime data-plane identity (fail-closed isolation).

``APP_ENV`` labels process behavior (debug, HTTPS, payment rules). It does **not**
identify which PostgreSQL database or uploads volume is being mutated.

``KARZAR_DATA_PLANE`` identifies the mutable data plane:

- ``live`` — public VPS catalog (today: DB name ``karzar_staging`` on the
  production compose project; CR-011 / historic misnomer).
- ``catalog_staging`` — isolated catalog rehearsal stack (separate DB + media).
- ``development`` — local developer machine.

Threat class this module detects:

    APP_ENV=staging + POSTGRES_DB=<live DB> + KARZAR_DATA_PLANE=catalog_staging
    → FAIL (claimed staging plane, live database)

See ``docs/CATALOG_STAGING_ISOLATION.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

# Historic live VPS database name (CR-011). Despite the suffix, this IS live.
LIVE_DB_NAME_DENYLIST: frozenset[str] = frozenset(
    {
        "karzar_staging",
    }
)

CATALOG_STAGING_DB_NAME_DEFAULT = "karzar_catalog_staging"
DATA_PLANE_VALUES = frozenset({"live", "catalog_staging", "development"})


@dataclass(frozen=True, slots=True)
class DataPlaneIdentity:
    """Non-secret identity snapshot for operators and guards."""

    app_env: str
    data_plane: str
    postgres_db: str
    postgres_server: str
    media_plane: str
    write_policy: str
    inferred_data_plane: bool


def normalize_data_plane(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return normalized


def infer_data_plane(app_env: str, explicit: str | None) -> tuple[str, bool]:
    """Return ``(data_plane, was_inferred)``.

    Unset ``KARZAR_DATA_PLANE`` defaults preserve CR-011 live VPS behavior:
    ``APP_ENV=staging`` → ``live`` (label-only staging is still the live plane).
    """
    explicit_norm = normalize_data_plane(explicit)
    if explicit_norm is not None:
        return explicit_norm, False

    env = (app_env or "development").strip().lower()
    if env == "development":
        return "development", True
    # staging and production both default to the live data plane until an
    # isolated catalog-staging stack is explicitly opted in.
    return "live", True


def live_db_denylist(*, extra: str | None = None) -> frozenset[str]:
    """Live database names that catalog_staging must never target."""
    names = set(LIVE_DB_NAME_DENYLIST)
    if extra:
        for part in extra.split(","):
            cleaned = part.strip().lower()
            if cleaned:
                names.add(cleaned)
    return frozenset(names)


def expected_catalog_staging_db(*, override: str | None = None) -> str:
    value = (override or "").strip()
    return value or CATALOG_STAGING_DB_NAME_DEFAULT


def validate_data_plane(
    *,
    app_env: str,
    data_plane_explicit: str | None,
    postgres_db: str,
    postgres_server: str = "",
    media_plane: str | None = None,
    catalog_staging_db_name: str | None = None,
    extra_live_db_names: str | None = None,
) -> DataPlaneIdentity:
    """Validate plane vs database; raise ``ValueError`` on contradiction."""
    plane, inferred = infer_data_plane(app_env, data_plane_explicit)
    if plane not in DATA_PLANE_VALUES:
        raise ValueError(
            f"KARZAR_DATA_PLANE must be one of: {', '.join(sorted(DATA_PLANE_VALUES))} "
            f"(got {plane!r})"
        )

    db = (postgres_db or "").strip()
    if not db:
        raise ValueError("POSTGRES_DB is required for data-plane validation")

    db_lower = db.lower()
    deny = live_db_denylist(extra=extra_live_db_names)
    expected_staging_db = expected_catalog_staging_db(override=catalog_staging_db_name)

    if plane == "catalog_staging":
        if db_lower in deny:
            raise ValueError(
                "KARZAR_DATA_PLANE=catalog_staging cannot use a live database name "
                f"({db!r}). Live denylist includes: {', '.join(sorted(deny))}. "
                f"Use POSTGRES_DB={expected_staging_db} on an isolated Postgres volume."
            )
        if db_lower != expected_staging_db.lower():
            raise ValueError(
                "KARZAR_DATA_PLANE=catalog_staging requires "
                f"POSTGRES_DB={expected_staging_db!r} (got {db!r}). "
                "Refusing start to prevent accidental live catalog writes."
            )

    # Claiming live while pointing at the catalog-staging DB name is allowed
    # only if operators intentionally reuse the name (discouraged). Prefer
    # explicit plane=catalog_staging. No fail here — wrong direction is less
    # dangerous (writes isolated DB while thinking live).

    media = normalize_data_plane(media_plane) or plane
    if plane == "catalog_staging" and media != "catalog_staging":
        raise ValueError(
            "KARZAR_MEDIA_PLANE must be 'catalog_staging' when "
            f"KARZAR_DATA_PLANE=catalog_staging (got {media!r})"
        )

    write_policy = _write_policy(plane)
    return DataPlaneIdentity(
        app_env=(app_env or "").strip().lower() or "development",
        data_plane=plane,
        postgres_db=db,
        postgres_server=(postgres_server or "").strip(),
        media_plane=media,
        write_policy=write_policy,
        inferred_data_plane=inferred,
    )


def _write_policy(plane: str) -> str:
    if plane == "catalog_staging":
        return "catalog_staging_writes_ok"
    if plane == "development":
        return "local_category_a_default"
    return "live_requires_adr012_category_b"


def identity_from_mapping(env: Mapping[str, str]) -> DataPlaneIdentity:
    """Build identity from an env mapping (os.environ-compatible)."""
    return validate_data_plane(
        app_env=env.get("APP_ENV", "development"),
        data_plane_explicit=env.get("KARZAR_DATA_PLANE"),
        postgres_db=env.get("POSTGRES_DB", ""),
        postgres_server=env.get("POSTGRES_SERVER", ""),
        media_plane=env.get("KARZAR_MEDIA_PLANE"),
        catalog_staging_db_name=env.get("KARZAR_CATALOG_STAGING_DB_NAME"),
        extra_live_db_names=env.get("KARZAR_LIVE_DB_DENYLIST"),
    )


def format_identity_report(identity: DataPlaneIdentity) -> str:
    """Human-readable non-secret identity block for operators."""
    inferred = "yes (default)" if identity.inferred_data_plane else "no (explicit)"
    return "\n".join(
        [
            f"APP ENV:      {identity.app_env}",
            f"DB ENV:       {identity.data_plane} (inferred={inferred})",
            f"DB NAME:      {identity.postgres_db}",
            f"DB SERVER:    {identity.postgres_server or '(unset)'}",
            f"MEDIA ENV:    {identity.media_plane}",
            f"WRITE POLICY: {identity.write_policy}",
        ]
    )


def assert_catalog_mutate_allowed(
    identity: DataPlaneIdentity,
    *,
    allow_live_catalog_writes: bool = False,
) -> None:
    """Fail closed for catalog APPLY / mutate when plane is live without opt-in.

    Catalog-staging and development planes are eligible. Live plane requires
    ``allow_live_catalog_writes=True`` (operators must also satisfy ADR-012 when
    targeting production API hosts).
    """
    if identity.data_plane in {"catalog_staging", "development"}:
        return
    if allow_live_catalog_writes:
        return
    raise ValueError(
        "Catalog mutation refused: data plane is "
        f"{identity.data_plane!r} (DB={identity.postgres_db!r}). "
        "Point at an isolated catalog-staging stack "
        "(KARZAR_DATA_PLANE=catalog_staging, "
        f"POSTGRES_DB={CATALOG_STAGING_DB_NAME_DEFAULT}) "
        "or pass an explicit live-write confirmation after ADR-012 Category B."
    )


def assert_db_sentinel_matches_plane(
    *,
    declared_plane: str,
    sentinel_plane: str | None,
    require_match: bool = False,
) -> None:
    """Fail closed when ``environment_identity.plane`` disagrees with declaration.

    ``sentinel_plane=None`` means the marker table/row is absent (pre-migration).

    Default behavior (``require_match=False``): catalog-staging writes require an
    explicit matching sentinel; live/development skip (historical path for the
    ordinary dictionary importer).

    ``require_match=True``: declared plane must equal sentinel exactly (used by
    the live-only dictionary importer). Missing sentinel refuses.
    """
    declared = normalize_data_plane(declared_plane)
    if declared is None:
        raise ValueError("declared data plane is required for sentinel validation")
    sentinel = normalize_data_plane(sentinel_plane)
    if require_match:
        if sentinel is None:
            raise ValueError(
                f"environment_identity.plane is missing/absent but "
                f"KARZAR_DATA_PLANE={declared!r} requires an exact sentinel match. "
                "Refusing write (run migration that creates environment_identity)."
            )
        if sentinel != declared:
            raise ValueError(
                f"KARZAR_DATA_PLANE={declared!r} but environment_identity.plane="
                f"{sentinel_plane!r}. Refusing write: declared / DB marker mismatch."
            )
        return
    if declared != "catalog_staging":
        # Live/development do not require the staging sentinel (ordinary importer).
        return
    if sentinel != "catalog_staging":
        raise ValueError(
            "KARZAR_DATA_PLANE=catalog_staging but environment_identity.plane="
            f"{sentinel_plane!r}. Refusing write: declared staging / actual DB "
            "marker mismatch (CR-011 live mislabel class)."
        )


def assert_live_db_sentinel(*, sentinel_plane: str | None) -> None:
    """Live Dictionary import: require environment_identity.plane == live."""
    assert_db_sentinel_matches_plane(
        declared_plane="live",
        sentinel_plane=sentinel_plane,
        require_match=True,
    )


def assert_category_b_production_write(
    *,
    allow_production_write: str | None,
    ingestion_category: str | None,
) -> None:
    """Require ADR-012 Category B pair (exact env spellings)."""
    allow = (allow_production_write or "").strip()
    category = (ingestion_category or "").strip().upper()
    errors: list[str] = []
    if allow != "1":
        errors.append("set KARZAR_ALLOW_PRODUCTION_WRITE=1")
    if category != "B":
        errors.append("set KARZAR_INGESTION_CATEGORY=B")
    if errors:
        raise ValueError(
            "Live Property Dictionary import refused: Category B incomplete — "
            + "; ".join(errors)
            + "."
        )


def assert_dictionary_seed_import_allowed(
    identity: DataPlaneIdentity,
    *,
    sentinel_plane: str | None,
    extra_live_db_names: str | None = None,
) -> None:
    """Non-dry-run Property Dictionary import gate (ordinary importer).

    Order:
      1. Reject any postgres_db in the live DB denylist (plane-independent)
      2. Refuse live plane (no force-production switch)
      3. Require matching environment_identity for catalog_staging

    Allowed planes after denylist: ``development``, ``catalog_staging``.
    """
    deny = live_db_denylist(extra=extra_live_db_names)
    db_lower = (identity.postgres_db or "").strip().lower()
    if db_lower in deny:
        raise ValueError(
            "Property Dictionary import refused: "
            f"database {identity.postgres_db!r} is classified as LIVE and cannot "
            "be mutated by this importer, regardless of KARZAR_DATA_PLANE."
        )
    assert_catalog_mutate_allowed(identity, allow_live_catalog_writes=False)
    assert_db_sentinel_matches_plane(
        declared_plane=identity.data_plane,
        sentinel_plane=sentinel_plane,
    )


def assert_live_dictionary_seed_import_allowed(
    identity: DataPlaneIdentity,
    *,
    sentinel_plane: str | None,
    allow_production_write: str | None,
    ingestion_category: str | None,
    extra_live_db_names: str | None = None,
) -> None:
    """Non-dry-run LIVE-only Property Dictionary import gate.

    Order:
      1. Require explicit KARZAR_DATA_PLANE=live (no inferred plane)
      2. Require postgres_db ∈ live denylist (known live target)
      3. Require ADR-012 Category B + production-write flag
      4. Require environment_identity.plane == live
    """
    if identity.inferred_data_plane:
        raise ValueError(
            "Live Property Dictionary import refused: KARZAR_DATA_PLANE must be "
            "set explicitly to 'live' (inferred plane is not accepted)."
        )
    if identity.data_plane != "live":
        raise ValueError(
            "Live Property Dictionary import refused: KARZAR_DATA_PLANE must be "
            f"'live' (got {identity.data_plane!r}). Use "
            "scripts/seed_property_dictionary.py for development/catalog_staging."
        )
    deny = live_db_denylist(extra=extra_live_db_names)
    db_lower = (identity.postgres_db or "").strip().lower()
    if db_lower not in deny:
        raise ValueError(
            "Live Property Dictionary import refused: POSTGRES_DB="
            f"{identity.postgres_db!r} is not a recognized LIVE database. "
            f"Approved live names: {', '.join(sorted(deny))}."
        )
    assert_category_b_production_write(
        allow_production_write=allow_production_write,
        ingestion_category=ingestion_category,
    )
    assert_live_db_sentinel(sentinel_plane=sentinel_plane)
