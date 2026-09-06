# AODS checks (on demand)

**Status of this file:** operational invocation guide — **not** Accepted. It does not replace [`AODS-CHARTER.md`](AODS-CHARTER.md).

The Charter (1.0.0) and Canon Lock §1b remain the Accepted process authority (Board minute ۸ مرداد ۱۴۰۵). PR #271 archived most orchestration artifacts and CI now runs the integrity gates below. **That reduction is not a Board-accepted supersession** — see `CR-024`. Until Architecture Board accepts or rejects the transition (`HC-14`):

- do not claim roles / versioned prompts / task-graph / PMO-mirror gates are repealed
- do not treat archived files as executable current ceremony
- do not invent a third process
- run the retained commands when the change can break them

Acceptance evidence: [`90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md`](90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md).

## What CI currently runs

| Gate | Proves |
|------|--------|
| `registry` | Active markdown is classified or explicitly allowed; registered paths exist |
| `links` | Relative markdown links in **active** docs resolve (archive excluded) |
| `naming` | Tracked filenames avoid reserved `final`/`latest`/`copy` stems |
| `openapi` | `openapi/v1.json` path set matches `app.openapi()` |
| `ingestion-boundary` | `scripts/*.py` do not default to `karzartools.com` (ADR-012) |

Optional gates (`citation`, `pmo`, `prompts`, `graph`, `allowlist`) remain in the tool and skip when their artifacts are absent. Absence is tree drift vs Charter S-05/S-07, not a silent repeal.

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
- Schedule: GitHub Issues/PRs (operational). Charter still names PMO consistency until Board amends it (`CR-024`)
- Evidence: `docs/archive/`, `CONFLICT-REGISTER.md` (append-only)

Do not set a document `Accepted`. Do not rewrite conflict-register rows. Production writes and deploys need a human (`docs/OPERATIONS.md`, ADR-012).
