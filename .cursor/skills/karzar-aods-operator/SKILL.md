---
name: karzar-aods-operator
description: >
  Use this skill for any Karzar monorepo work: planning, implementation, review,
  API/schema/URL/SEO changes, catalog ingestion, PMO updates, audits, or
  release-related tasks. Applies Accepted AODS 1.0.0, Canon Lock authority,
  allow-list execution, local-only ingestion, merge-base citations, PMO sync,
  and halt-instead-of-guess. Trigger on app/, frontend/, alembic/, scripts/,
  docs/architecture/, aods/, project-management/, OpenAPI, Brand Hub, PDP slug,
  enrichment, deploy, or conflict-register mentions.
---

# Karzar AODS Operator

Operating skill for **Karzar** (`Shebahati/Karzar`) after AODS **Accepted 1.0.0**
(۸ مرداد ۱۴۰۵ / 2026-07-30, Mohammad Shebahati).

AODS governs *how* work is done. Canon Lock governs *what is correct*.
PMO governs *what is next*. This skill makes those three enforceable in Auto Mode.

## 0. First 60 seconds (every task)

1. `git fetch origin main` and treat `origin/main` as citation merge-base.
2. Read `project-management/EXECUTIVE_SUMMARY.md` — confirm the work serves the
   **31 Shahrivar (2026-09-22)** checkpoint: mid-tail SEO + UX + CWV, **not**
   head-term #1 vanity.
3. Classify change class **C0–C6** (`aods/90-governance/GOVERNANCE.md`).
4. Bind a PMO task ID from `project-management/exports/tasks.json`, or state
   explicitly why none exists (`CR-008` risk).
5. Pick **one** prompt from `aods/70-prompts/` (table below). Do not freestyle.
6. Print `RESTATE` (goal, constraints, allow-list, non-goals) then `PLAN`.
7. If a required ADR/RFC/spec is missing, ambiguous, or conflicts → **HALT**
   with numbered blockers. Guessing is failure.

## 1. Authority order (never silent-pick)

When documents disagree, report the conflict and stop:

1. **Runtime truth** — code, live routes, `openapi/v1.json`, `alembic/`
2. **Canon** — `docs/architecture/CANON-LOCK.md` + Accepted ADR/RFC
3. **Operational policy** — ingestion policy, git workflow, `docs/OPERATIONS.md`
4. **Developer standards** — `docs/development/standards/**`
5. **PMO** — `project-management/**` (schedule/status only; never correctness)
6. **Evidence** — `docs/audits/**` (measures; does not authorize)

Full model: `aods/10-repository-intelligence/AUTHORITY-MODEL.md`.

### Canon you must know

| Doc | Path | Use for |
|-----|------|---------|
| Canon Lock index | `docs/architecture/CANON-LOCK.md` | What is binding today |
| ADR-010 | `docs/architecture/adr/ADR-010-seo-url-contract.md` | PDP `/product/{slug}`, 301 from id, Brand Hub `/brands/{slug}` |
| ADR-012 | `docs/architecture/adr/ADR-012-ingestion-boundary-local-vs-production.md` | Local-only routine ingestion |
| RFC-004 | `docs/architecture/rfc/RFC-004-slug-migration-and-redirects.md` | Slug migration / redirects |
| RFC-005 | `docs/architecture/rfc/RFC-005-brand-hub-launch.md` | Brand Hub launch (spec gaps = `CR-014`) |
| AODS Charter | `aods/AODS-CHARTER.md` | Process system (Accepted 1.0.0) |
| Board minute | `aods/90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md` | AODS acceptance evidence |

Cite as `path:line` against **`origin/main`**, not an unmerged branch tip.

## 2. Hard prohibitions

### Never read (hallucination sources)

- `frontend/AI_CONTEXT.md`
- `docs/archive/AI_CONTEXT-2026-07-11.md`
- `frontend/BACKEND_NON_COMPLIANCE.md`
- `frontend/BACKEND_HANDOFF.md`
- `docs/FRONTEND_IMPLEMENTATION_GUIDE.md`
- `docs/GO_LIVE_EXECUTION_PLAN.md`
- `docs/audits/v1/**`
- `docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md`

### Never do (unless human explicitly overrides with HC)

- `git push` / `git merge` / `git rebase` / `git reset --hard` / deploy
- Write production DB or call `https://api.karzartools.com`
- Point enrichment/import scripts at production (many still **default** to it — `CR-004`)
- Set any document status to `Accepted`
- Close/rewrite conflict-register rows (`CONFLICT-REGISTER.md` is **append-only**)
- Delete governance docs (supersede + record)
- Edit outside the declared allow-list; opportunistic cleanup
- Add/remove/upgrade dependencies without escalation
- Invent specs, prices, stock, or undocumented fields
- Claim a command passed without pasting real output
- Third strategy after two failed attempts → HALT

Always-on floor: `.cursor/rules/aods-auto-mode.mdc`.

## 3. Repo map

| Path | Role |
|------|------|
| `app/` | FastAPI backend (endpoints, crud, services, schemas) |
| `frontend/Storefront/` | Next.js public shop (RTL/Persian), port 3000 |
| `frontend/admin-panel/` | Next.js admin, port 3001 — read `AGENTS.md` first |
| `alembic/` | DB migrations (HC-08) |
| `openapi/v1.json` | Machine API contract — **must** match code |
| `scripts/` | Import/enrich/SEO/taxonomy — treat as hazardous |
| `aods/` | Process OS (prompts, gates, registries) |
| `project-management/` | Living PMO SoT |
| `docs/architecture/` | Canon Lock, ADR, RFC, IA |
| `.github/workflows/` | CI + deploy (staging≈prod — `CR-011`) |

Stack anchors: FastAPI + SQLAlchemy async + Postgres + Redis; Next.js 16 / React 19 /
Tailwind 3 / TanStack Query. Backend coverage CI gate: **68%**.

## 4. Node / prompt selection

One node = one role = one concern = one allow-list.

| Intent | Prompt |
|--------|--------|
| Spec a feature | `aods/70-prompts/spec/SPEC-feature-contract.prompt.md` |
| Backend endpoint | `aods/70-prompts/impl/IMPL-backend-endpoint.prompt.md` |
| Frontend route/UI | `aods/70-prompts/impl/IMPL-frontend-route.prompt.md` |
| Alembic migration | `aods/70-prompts/impl/IMPL-schema-migration.prompt.md` |
| Tests from spec | `aods/70-prompts/test/TEST-from-spec.prompt.md` |
| OpenAPI/docs sync | `aods/70-prompts/doc/DOC-api-contract-sync.prompt.md` |
| Catalog ingest | `aods/70-prompts/know/KNOW-catalog-ingest.prompt.md` |
| PMO mirror sync | `aods/70-prompts/gov/GOV-pmo-sync.prompt.md` |
| Address review | `aods/70-prompts/gov/GOV-address-review.prompt.md` |
| Repo scan | `aods/70-prompts/audit/AUD-repository-scan.prompt.md` |
| Doc conflict scan | `aods/70-prompts/audit/AUD-doc-conflict-scan.prompt.md` |

Loop: `READ → RESTATE → PLAN → ACT → VERIFY → RECORD`.

Ceilings (default): **≤400 changed lines**, **≤15 files**, one concern per PR.
Separate IMPL / TEST / DOC / GOV nodes — do not mix.

## 5. Domain invariants

### URL / SEO (ADR-010)

- Canonical PDP: `/product/{slug}`
- `/product/{id}` → **301** to slug
- Brand hubs: `/brands/{slug}` (RFC-005; do not invent page contract — `CR-014`)
- Categories: `/categories/{slug}`
- Canonical, sitemap, breadcrumbs, JSON-LD `@id` must agree

### Ingestion (ADR-012 + D4)

- Routine work targets `http://127.0.0.1:8000/api/v1` only
- **Content enrichment never writes** price / stock / availability
- Numeric warehouse stock = Hesabfa; site uses binary `is_available`
- Do not resurrect `stock_quantity` / `low_stock` from stale docs
- Production writes require Category B + HC-09 (backup, declaration, rollback)

### OpenAPI (`CR-012`)

After any API shape change:

1. Regenerate `openapi/v1.json`
2. Diff it in the same PR
3. Update `docs/API_CHANGELOG.md` when contract-affecting
4. Run `python3 aods/tools/aods_validate.py --gate openapi`

Known debt: `/api/v1/products/slug/{slug}` is live; snapshot may lag until regenerated.

### Deploy hazard (`CR-011`)

Push/merge to `main` touching `app/**`, `alembic/**`, frontends, etc. can trigger
`deploy-staging.yml` onto the **same VPS as production** (`karzartools.com`).
There is no isolated staging. Treat qualifying merges as live releases.

## 6. Open BLOCKERs (do not pretend fixed)

Source: `aods/10-repository-intelligence/CONFLICT-REGISTER.md` (append-only).

| ID | Reality |
|----|---------|
| CR-001 | Canon Lock **is on main** (PR #125). Row may still show OPEN until a dated Board close — append a decision; do not rewrite history. |
| CR-004 | **CLOSED** — local defaults + fail-closed Category B (`ingestion_boundary.py`) |
| CR-009 | Authoring SoR partly outside Git (`Website/docs/`) |
| CR-011 | Staging ≈ production (same VPS) |
| CR-015 | **CLOSED** — FE AI_CONTEXT stubbed; archive forbidden |

Also watch: CR-002 branch naming, CR-003 coverage %, CR-007 duplicate PMO paths,
CR-012 OpenAPI, CR-014 Brand Hub underspec, CR-018 missing PR template.

## 7. PMO living system (same PR)

Rule: `.cursor/rules/pmo-living-system.mdc`.

When starting / completing / cancelling / re-scoping meaningful work:

1. Update `project-management/exports/tasks.json` (`status`, `progress`, `notes`)
2. Mirror checkboxes in `PROJECT_STATUS.md`, active `SPRINT_XX.md`, relevant `*_PROGRESS.md`
3. Append `CHANGELOG.md`; on done, `DONE.md` with task ID + PR link
4. New debt/risk/blocker → `TECH_DEBT.md` / `RISKS.md` / `BLOCKERS.md`
5. Progress ledgers: `project-management/progress/` only; sprints: `project-management/sprints/` only (CR-007 Option A)

Deferred past checkpoint (owner PMO, revisit **2026-09-23**): **CAT-002**, **KB-001**.

## 8. Branch / PR shape

- Never develop on `main`
- Prefer `feature/*` | `fix/*` | `hotfix/*` | `chore/*` | `docs/*`
  (`feat/*` also appears — `CR-002`; report, do not silent-normalize)
- Cursor agent branches may use `cursor/<name>-NNNN` when required by the agent env
- PR body should include: `Node`, `Task` (or why none), `Authority` paths,
  Summary, Test plan, real gate output, Rollback
- Cite relevant Canon rows; validate citations on `origin/main`
- Human owns HC-06 push/open and HC-07 merge (unless the human explicitly
  orders the agent to perform them in this session)

## 9. Validation before claiming done

```bash
python3 aods/tools/aods_validate.py          # baseline-aware
python3 aods/tools/aods_validate.py --all    # full debt picture
python3 aods/tools/aods_validate.py --gate openapi
python3 aods/tools/aods_validate.py --gate ingestion-boundary
```

Also run the domain tests you touched (pytest / vitest / lint). Paste real output.

Expect residual findings today (registry `on_main` flags, CR-004/007/012, etc.).
**Do not baseline-grow** without HC-14. Report discovered debt; fix only what is in scope.

## 10. Human checkpoints (stop and ask)

| HC | When |
|----|------|
| HC-01 | Spec acceptance / freeze |
| HC-02 | ADR/RFC/Canon accept |
| HC-03 | Conflict-register decision |
| HC-04 | Convention conflict (branch name, PMO path, coverage) |
| HC-05 | Diff review |
| HC-06 | Push + open PR |
| HC-07 | Merge (live-deploy risk) |
| HC-08 | Migration |
| HC-09 | Ingestion authorization |
| HC-10 | Secrets |
| HC-11 / HC-12 | Deploy / verify release |
| HC-13 | External source document |
| HC-14 | AODS amendment / CI gate enforcement |

Literal steps: `aods/60-human/HUMAN-INTERVENTION-MODEL.md`.

## 11. Completion report (mandatory shape)

```text
RESTATE: ...
CHANGED: <paths>
PMO: <task-id status/progress>
GATES: <command + paste>
TESTS: <command + paste>
HALTS/OPEN QUESTIONS: <numbered or none>
DEBT NOTICED (not fixed): <ids/paths>
NEXT HUMAN STEP: <HC-nn or none>
```

## 12. Quick references

- Entry: `aods/README.md`
- Conflicts: `aods/10-repository-intelligence/CONFLICT-REGISTER.md`
- Adoption / next ops: `aods/90-governance/DELIVERABLES-AND-ADOPTION.md`
- Checkpoint: `project-management/EXECUTIVE_SUMMARY.md`
- Status: `project-management/PROJECT_STATUS.md`
- Admin FE note: `frontend/admin-panel/AGENTS.md`
