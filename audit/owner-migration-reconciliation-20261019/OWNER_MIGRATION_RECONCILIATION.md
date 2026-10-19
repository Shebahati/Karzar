# OWNER MIGRATION RECONCILIATION — `brands.logo_url` / u6 drift (2026-10-19)

## Verified live state (owner attested)

| Field | Value |
|-------|--------|
| Database | `karzar_staging` (CR-011 live plane) |
| `alembic_version` | **one row:** `c1d2e3f4a5b6` |
| `brands.logo_url` | **exists** — `VARCHAR(500)`, nullable, no default |
| Populated logos | 25 / 40 brands non-null |
| `home_bestseller_selection` | **does not exist** |
| Target code head | `bcd3b0b3` → Alembic head **`a3f410b5c6d7`** |

## Root cause

Merge revision `a3f410b5c6d7` requires parents **`c1d2e3f4a5b6`** and **`u6v7w8x9y0z1`**. Live records only the `c1` branch tip, but **`logo_url` was applied outside Alembic’s `u6` revision** (manual/script/legacy deploy). The stock `u6` migration used unconditional `op.add_column`, which would **fail** on deploy when `docker-entrypoint.sh` runs `alembic upgrade head`.

## Remediation strategies compared

| Strategy | Fresh DB | Preserves live logos | Fail-closed on drift | History honesty | Rollback | Verdict |
|----------|----------|----------------------|----------------------|-----------------|----------|---------|
| **A. Guarded `u6` upgrade (same revision id)** | Adds column if missing | Yes — no-op + compatibility check | Yes | Revision id unchanged; body updated before `u6` ever stamped on live | Downgrade skips drop if any non-null `logo_url` | **Recommended** |
| **B. `alembic stamp u6` without upgrade** | N/A | Unchecked — incompatible column would pass | **No** | Falsifies that `u6` ran | Dangerous | **Reject** |
| **C. New forward migration instead of fixing `u6`** | Requires rewiring `v7…` child + merge parents | Possible | Yes | Leaves broken `u6` for anyone upgrading linearly | Complex graph surgery | **Reject** (scope/risk) |
| **D. Manual SQL + stamp** | N/A | Operator error risk | Weak | Off-book | Hard to audit | **Reject** |
| **E. Drop & re-add column** | Works | **Destroys 25 logos** | N/A | N/A | Data loss | **Reject** |

### Historical revision edit (Strategy A)

- **Live:** `u6` is **not** in `alembic_version` → editing `u6v7w8x9y0z1_add_brand_logo_url.py` does **not** rewrite applied history on CR-011.
- **Envs that already stamped `u6`:** Alembic will **not** re-run `upgrade()`; guard is irrelevant unless they downgrade/re-upgrade.
- **Fresh clones / CI:** run guarded `u6` once.

Implementation: `alembic/brand_logo_url_guard.py` + thin `u6` revision wrapper.

## Approved migration path (post-fix code)

From live `c1d2e3f4a5b6`:

1. Alembic applies pending revisions on the **`u6` branch** (through `t5u6v7w8x9y0` … `u6v7w8x9y0z1`).
2. **`u6` upgrade:** if `logo_url` missing → `ADD COLUMN`; if present → **assert** `VARCHAR(500)` nullable, no server default; **no data changes**.
3. **`a3f410b5c6d7`:** creates `home_bestseller_selection` only (no product seed).

Expected final `alembic_version`: **`a3f410b5c6d7`** (single head).

## Rollback

| Action | Effect |
|--------|--------|
| Revert container image | App rollback; **schema stays at `a3f410`** if migration already ran |
| `alembic downgrade a3f410b5c6d7` | Drops `home_bestseller_selection` only (if empty / owner accepts) |
| `alembic downgrade u6v7w8x9y0z1` | Drops `logo_url` **only if no non-null values** — live with 25 logos → **no-op drop** |

## Pre-release tests (automated)

| Test module | What it proves |
|-------------|----------------|
| `tests/test_brand_logo_url_u6_migration.py` | Compatible / incompatible specs; add column when missing; preserve non-null on downgrade |
| `tests/test_knowledge_unit_dimensions_prompt150.py::test_alembic_head_is_single_descendant_of_s2` | Single head `a3f410b5c6d7`, merge parents |

### Required before GO (owner / VPS)

1. **Scratch DB restore** from pre-deploy backup → `alembic upgrade head` at `bcd3b0b3` (or PR head).
2. **Live read-only re-check:** `alembic current` = `c1d2e3f4a5b6`; confirm `logo_url` definition unchanged.
3. **Post-upgrade on scratch:** `alembic current` = `a3f410b5c6d7`; `logo_url` values byte-identical to pre-upgrade export sample.
4. `GET /api/v1/home-merchandising/bestsellers` → 200 empty payload.
5. Deploy smoke per `docs/OPERATIONS.md`.

## PR #538

Superseded by merged **#537** (`a3f410b5c6d7`). **Do not merge #538** or apply competing revision `c2d3e4f5a6b7`.

## Release status

**NO-GO** until guarded `u6` is merged and scratch restore + migration dry-run succeed. This document does not authorize live migration.
