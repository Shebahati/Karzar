# AODS checks (on demand)

AODS is the **Accepted** process system (1.0.0, Board minute ۸ مرداد ۱۴۰۵). Charter: [`AODS-CHARTER.md`](AODS-CHARTER.md). Acceptance evidence: [`90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md`](90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md).

It is **not** a mandatory role/prompt ceremony and not a second product spec. Do not preload this tree. Run checks when the change can break them.

## What the retained gates prove

| Gate | Proves |
|------|--------|
| `registry` | Active markdown is classified or explicitly allowed; registered paths exist |
| `links` | Relative markdown links in **active** docs resolve (archive excluded) |
| `naming` | Tracked filenames avoid reserved `final`/`latest`/`copy` stems |
| `openapi` | `openapi/v1.json` path set matches `app.openapi()` |
| `ingestion-boundary` | `scripts/*.py` do not default to `karzartools.com` (ADR-012) |

Optional / contextual: `--gate citation` (PR body paths on merge-base), `--gate pmo` / `prompts` / `graph` / `allowlist` if those artifacts still exist.

## Invoke

```bash
python3 aods/tools/aods_validate.py              # retained gates, baseline-aware (CI)
python3 aods/tools/aods_validate.py --all        # same gates, no baseline
python3 aods/tools/aods_validate.py --gate openapi
python3 aods/tools/aods_validate.py --gate ingestion-boundary
python3 aods/tools/aods_validate.py --list-gates
```

Stdlib only. Baseline: `aods/registry/validation-baseline.json` (visible debt, not a silent skip).

## Authority that still matters

1. Runtime: code, `openapi/v1.json`, `alembic/`
2. Canon: `docs/architecture/CANON-LOCK.md` + Accepted ADR/RFC
3. Ops / ingestion policy
4. Developer standards under `docs/development/standards/`
5. GitHub Issues/PRs for *when*
6. `docs/archive/` and `CONFLICT-REGISTER.md` for evidence — register is append-only

Do not set a document `Accepted`. Do not rewrite conflict-register rows. Production writes and deploys need a human (`docs/OPERATIONS.md`, ADR-012).

Historical orchestration (prompt library, task-graph, role ceremony, PMO mirrors) lives under `docs/archive/` after consolidation and is not current guidance.
