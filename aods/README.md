# AODS checks (on demand)

**Status of this file:** Binding invocation guide for retained integrity gates. Process authority is [`AODS-CHARTER.md`](AODS-CHARTER.md) (current operating model).

Architecture Board minute [`90-governance/BOARD-MINUTE-AODS-SIMPLIFICATION.md`](90-governance/BOARD-MINUTE-AODS-SIMPLIFICATION.md) (۱۵ شهریور ۱۴۰۵ / 2026-09-06, PR #271) makes this reduced surface **current procedure**. AODS 1.0.0 acceptance is historical provenance. Archived orchestration under `docs/archive/` is evidence, not executable ceremony.

- run the retained commands when the change can break them
- do not treat archived files as current authorities
- do not invent a third process

1.0.0 acceptance evidence: [`90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md`](90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md).

## What CI currently runs

| Gate | Proves |
|------|--------|
| `registry` | Active markdown is classified or explicitly allowed; registered paths exist |
| `links` | Relative markdown links in **active** docs resolve (archive excluded) |
| `naming` | Tracked filenames avoid reserved `final`/`latest`/`copy` stems |
| `openapi` | `openapi/v1.json` path set matches `app.openapi()` |
| `ingestion-boundary` | `scripts/*.py` do not default to `karzartools.com` (ADR-012) |

Optional gates (`citation`, `pmo`, `prompts`, `graph`, `allowlist`) remain in the tool and skip when their artifacts are absent. `pmo` / `prompts` / `graph` are **not** current required ceremony. Use `citation` when the change cites authority.

```bash
python3 aods/tools/aods_validate.py
python3 aods/tools/aods_validate.py --gate openapi
python3 aods/tools/aods_validate.py --gate ingestion-boundary
python3 aods/tools/aods_validate.py --list-gates
```

Stdlib only. Baseline: `aods/registry/validation-baseline.json`.

## Authority (as-built vs requirement)

- **Implemented state:** code, `openapi/v1.json`, `alembic/`, workflows, `.env*.example`
- **Requirement:** Accepted/Binding rows in `docs/architecture/CANON-LOCK.md` (Charter Φ3: specification outranks code)
- Drift: report it; follow Accepted Canon unless a newer Accepted decision supersedes it
- Schedule: GitHub Issues/PRs
- Evidence: `docs/archive/`, `CONFLICT-REGISTER.md` (append-only)

Do not set a document `Accepted`. Do not rewrite conflict-register rows. Production writes and deploys need a human (`docs/OPERATIONS.md`, ADR-012).
