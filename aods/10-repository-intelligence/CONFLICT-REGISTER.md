# Conflict Register — Open Issues Requiring Human Resolution

**Document ID:** `AODS-CR-001`
**Document type:** Governance register (append-only)
**Status:** **Accepted** (living register; individual `CR-*` rows remain OPEN until Board decision)
**Version:** 1.0.0
**Opened:** 2026-07-29
**Decision authority:** per-row (see `Owner`)

> **Purpose.** The brief for AODS states: *"Whenever requirements conflict, explicitly report the conflict instead
> of silently choosing one"* and *"whenever you identify uncertainty, clearly mark it as an open issue requiring
> human resolution instead of making assumptions."* This is that report.
>
> **Nothing in this file has been decided by AI.** Each row states the conflict, the evidence on both sides, the
> options, the AI-recommended option *as a recommendation only*, and the human who must decide.

---

## How to use this register

1. **Rows are append-only.** Never delete a row; close it by setting `Status: RESOLVED` with a date, the decision, and a link.
2. **`Owner: UNASSIGNED` is a failure state** (success criterion S-08). Assign a name.
3. An agent that encounters a live conflict **must halt** and cite the `CR-nnn` ID rather than improvising.
4. Conflicts that block a workflow node are listed in that node's `blocked_by` field in
   [`../registry/task-graph.yaml`](../registry/task-graph.yaml).

**Severity scale**

| Severity | Meaning |
|----------|---------|
| **BLOCKER** | Work in the affected area must not proceed until resolved |
| **HIGH** | Work may proceed under a stated assumption, which must be recorded in the TASK-RECORD |
| **MEDIUM** | Causes drift and rework; resolve within the current wave |
| **LOW** | Cosmetic or hygiene |

---

## Summary

| ID | Title | Severity | Owner | Status |
|----|-------|----------|-------|--------|
| CR-001 | Canon Lock promoted to `main` via PR #125 (2026-07-30); citations resolve | ~~BLOCKER~~ CLOSED | Architecture Board | CLOSED |
| CR-002 | Branch naming: `feature/*` (Canon) vs `feat/*` (CONTRIBUTING + 18 branches) | HIGH | Architecture Board | OPEN |
| CR-003 | Coverage gate stated as 62% / 67% / 67% / 68% in four documents | MEDIUM | QA Engineer | OPEN |
| CR-004 | Script defaults no longer point at production API (ADR-012); fail-closed Category B still optional residual | ~~BLOCKER~~ CLOSED | Backend Architect + Board | CLOSED |
| CR-005 | BE-01 transaction ownership: docs say endpoints commit; 26 service commits exist | HIGH | Backend Architect | OPEN |
| CR-006 | Quality bar: v2 audit 5.7 vs self-certified scorecard 9.0 | HIGH | Independent auditor | OPEN |
| CR-007 | PMO progress/sprint files duplicated at two paths; 6 pairs divergent | HIGH | PMO | OPEN |
| CR-008 | Two priority systems: PMO checkpoint vs Board EPIC-1; EPIC-1 PRs have no task ID | HIGH | Owner (PMO + Board) | OPEN |
| CR-009 | `Website/docs/` authoring SoR is outside version control | **BLOCKER** | Owner | OPEN |
| CR-010 | Canon Lock and Git workflow cite ≥12 documents that do not exist in the repo | HIGH | Architecture Board | OPEN |
| CR-011 | Staging and production are the same VPS; merge to `main` auto-deploys live | **BLOCKER** | DevOps / Release Manager | OPEN |
| CR-012 | `openapi/v1.json` snapshot drift fixed 2026-07-30; CI wiring still open | HIGH | Backend Architect | MITIGATED |
| CR-013 | Orphan/untracked work items: `CONTENT-URL-001`, `SEO-001 follow-up` | MEDIUM | PMO | OPEN |
| CR-014 | EPIC-1 deliverable 5 (`/brands/{slug}`) unimplemented and unspecified | HIGH | Frontend Architect + SEO | OPEN |
| CR-015 | `frontend/AI_CONTEXT.md` retains ~1,000 lines of false claims behind a banner | **BLOCKER** for AI work | Documentation Architect | OPEN |
| CR-016 | Pytest markers and options declared twice (`pytest.ini` + `pyproject.toml`) | LOW | QA Engineer | OPEN |
| CR-017 | 62 unmerged remote branches; 45 local worktrees; local `main` held by a worktree | MEDIUM | Owner | OPEN |
| CR-018 | PR checklist is Accepted but no `pull_request_template.md` exists | MEDIUM | Documentation Architect | OPEN |
| CR-019 | Knowledge Platform Phase 3 says pause image import; `CATALOG_IMAGES_PLAN.md` is actively importing | MEDIUM | Owner | OPEN |
| CR-020 | Bilingual doc pairs diverge, including contradictory API paths | MEDIUM | Documentation Architect | OPEN |
| CR-021 | Release/rollback owners unnamed while REL-001 is marked done | HIGH | Owner | OPEN |
| CR-022 | Availability semantics: `low_stock` documented as qty<10, hardcoded `False` in code | MEDIUM | Backend Architect | OPEN |
| CR-023 | Two root-relative links in `docs/BACKEND_CHANGES.md` do not resolve | LOW | Documentation Architect | OPEN |

**Open BLOCKERs: 3.** Until `CR-009`, `CR-011`, and `CR-015` are resolved, AODS operates in
degraded mode for those surfaces. `CR-001` and `CR-004` closed 2026-07-30.
**degraded mode** — see [`../90-governance/GOVERNANCE.md`](../90-governance/GOVERNANCE.md) §7.

---

## CR-001 — Canon Lock is binding but not on `main`

| Field | Value |
|-------|-------|
| **Severity** | BLOCKER |
| **Owner** | Architecture Board (Mohammad Shebahati) |
| **Status** | CLOSED |
| **Affects** | Every PR in Wave-1 / EPIC-1 scope; the entire AODS authority model rank 1 |

**Side A — the documents.** `docs/architecture/CANON-LOCK.md` is marked **Accepted** (۱۴۰۵/۰۵/۰۷, signed) and states:
*"If a document is not listed here as Accepted or Binding, it MUST NOT alone be used as merge criteria for EPIC 1 work."*
`documentation-citation-rules.md` adds: *"Missing Canon citation on URL/SEO/enrich PRs is an explicit PR fail."*

**Side B — the repository (historical).** At register open (2026-07-29), the 29 Wave-1 files existed only on
branch `docs/wave1-canon-lock-promote` (PR #125) and were absent from `main` at `c022a44`.

**Consequence already realised (historical).** PR #127 merged citing Canon Lock paths that 404'd on `main` —
AODS failure criterion **F-01 (auditability void)** — until promotion landed.

**Options**

| # | Option | Consequence |
|---|--------|-------------|
| A | Merge PR #125 immediately, before any further EPIC-1 PR | Citations resolve; rank 1 becomes real. Requires accepting the dangling references in `CR-010`. |
| B | Keep Canon Lock off `main`; cite by branch+commit SHA | Auditable but fragile; contradicts *"canonical promoted copy"* in `PROMOTION-WAVE1.md`. |
| C | Declare Canon Lock non-binding until merged, and retroactively strip citations | Contradicts the signed Board minute. |

**AI recommendation (advisory only): Option A**, then fix `CR-010` in a follow-up docs PR.

**DECISION (2026-07-30, Mohammad Shebahati — Board / operator session): Option A executed.**
PR #125 merged to `main` at `8b63415` (2026-07-30T03:07:32Z). `docs/architecture/CANON-LOCK.md` and the Wave-1
pack resolve on `origin/main`. AODS Accepted 1.0.0 landed via PR #128; skill via #129. Registry `on_main`
flags reconciled to `true` for promoted Canon + AODS documents; CR-001 validation-baseline link findings
removed. **Status → CLOSED.** Residual dangling refs inside the Canon pack remain `CR-010` (separate).

---

## CR-002 — Branch naming standard conflict

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Owner** | Architecture Board |
| **Status** | OPEN |

**Side A (`CANON`, rank 2).** `docs/development/git-development-workflow.md` and
`karzar-developer-standards.md` §4 mandate `feature/*`, `fix/*`, `hotfix/*`, `chore/*`, `docs/*`.
`pr-checklist.md` lists branch prefix as an "Always" gate.

**Side B (`POLICY`, rank 6).** `docs/CONTRIBUTING.md`: *"Branch names: `fix/…`, `feat/…`, `chore/…`, `docs/…`"* —
`feat/` not `feature/`, and no `hotfix/`.

**Side C (observed).** 18 branches use `feat/*`, only 2 use `feature/*`. The dominant practice follows the
*lower-ranked* document.

**Note on this PR.** The branch for the AODS work is `cursor/design-ai-orchestrated-development-system-4263`,
which matches **neither** standard — it is imposed by the Cloud Agent branch-prefix policy. That is a third
input the standard does not contemplate, and it should be addressed in the resolution.

**Options:** (A) amend `CONTRIBUTING.md` to `feature/*` and rename in-flight branches; (B) amend the Canon documents
to `feat/*` via Board minute, matching practice; (C) accept both prefixes explicitly in both documents.

**AI recommendation (advisory): Option C**, plus an explicit carve-out for agent-generated `cursor/*` branches.
Rationale: precedence says `feature/*` wins, but 90% of history uses `feat/*`; renaming history is worthless churn,
and a validator that fails 18 existing branches will be disabled rather than obeyed.

---

## CR-003 — Test coverage gate has four different values

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM |
| **Owner** | QA Engineer role |
| **Status** | OPEN |

| Source | Value |
|--------|-------|
| `docs/API_CHANGELOG.md` (P5 entry) | 62% |
| `docs/TESTING.md` | 67% minimum, 70% target |
| `README.md` | 67% |
| `pyproject.toml` `[tool.coverage.report] fail_under` | **68** |
| `.github/workflows/backend-ci.yml` `--cov-fail-under` | **68** |

**Enforced reality: 68%.** The other three are stale prose.

**Options:** (A) correct all prose to 68% and add a single-source note; (B) raise CI toward the 70% target and update
all four; (C) generate the number into docs from `pyproject.toml`.

**AI recommendation (advisory): Option A now, Option C when a docs-generation step exists.** The Charter's
"single-source numeric facts" principle applies: numbers duplicated in prose always drift.

---

## CR-004 — Enrichment scripts default to the production API, violating ADR-012

| Field | Value |
|-------|-------|
| **Severity** | BLOCKER (for any catalog-write work) |
| **Owner** | Backend Architect + Architecture Board |
| **Status** | CLOSED |

```
scripts/shopmill_insize_sync.py:27           scripts/azarsanat_import.py:29
scripts/dry_run_product_seo_descriptions.py:40  scripts/publish_vernier_article.py:18
scripts/dohre_official_catalog_enrich.py:47  scripts/insize_price_update.py:25
scripts/dasqua_catalog_2025_enrich.py:54     scripts/publish_seo003_articles.py:25
scripts/chumpower_official_catalog_enrich.py:56  scripts/mitutoyo_import.py:27
scripts/sanou_official_catalog_enrich.py:49  scripts/enrich_insize_from_shopmill.py:64
scripts/catalog_remediation.py:24            scripts/enrich_mitutoyo_from_leaflets.py:50
scripts/azarsanat_rebrand.py:26              scripts/remove_omumi_padding_leaves.py:253
scripts/mirror_product_images.py:49 (PUBLIC_ASSET_BASE)   scripts/materialize_product_images.py:40
```

Pattern: `API = os.getenv("KARZAR_API_BASE", "https://api.karzartools.com/api/v1")`.

The policy document **itself acknowledges this**, calling it *"non-compliant for routine use until overridden."*

**Complication.** `publish_seo003_articles.py` is invoked by `deploy-staging.yml` as a post-deploy step and
*must* target the deployed host. It is arguably a Category B/deploy job, not Category A enrichment — but no
document classifies it.

**Options:** (A) flip all defaults to `http://127.0.0.1:8000/api/v1` and require explicit opt-in for production;
(B) add a fail-closed guard requiring `KARZAR_ALLOW_PRODUCTION_WRITE=1` plus a declared Category;
(C) formally classify the deploy-time publishers as Category B with a documented ticket path.

**AI recommendation (advisory): A + B + C together**, as one `IMPL` node per script group, since the policy is
Accepted and the drift is unambiguous. **This must not be done as a side effect of unrelated work.**

**DECISION (2026-07-30, Mohammad Shebahati — Board / operator session): Option A executed.**
All 18 listed defaults flipped to local (`http://127.0.0.1:8000/api/v1` or `http://127.0.0.1:8000` for
`PUBLIC_ASSET_BASE`). `--gate ingestion-boundary` PASS; CR-004 baseline entries removed. **Status → CLOSED.**
**Residual (not this node):** Option B fail-closed guard + Option C formal Category B classification for
deploy-time publishers (`publish_seo003_articles.py` / staging workflow) — track as follow-up tech debt,
not a remaining BLOCKER for defaults.

---

## CR-005 — Transaction ownership (BE-01) drift

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Owner** | Backend Architect |
| **Status** | OPEN |

**Side A (rank 6 `POLICY` + rank 8 `REFERENCE`).** `docs/ARCHITECTURE.md` §"Transaction ownership (BE-01)" and
`docs/CONTRIBUTING.md`: *"Endpoints own `commit`/`rollback`. Services and CRUD flush only."*
`REMEDIATION-TO-9.md` lists BE-01 as an open **P1** item ("tx ownership on money path").

**Side B (code).** 26 `await db.commit()` calls in 8 service modules:
`product_service.py` (7), `otp_service.py` (4), `cart_service.py` (4), `brand_service.py` (4),
`category_service.py` (4), `checkout_service.py` (1), `idempotency_service.py` (1), `hesabfa/item_push.py` (1).
Plus 40 in endpoints and 1 in `main.py`'s order-expiry worker.

**Classification under the AUTHORITY-MODEL decision rule:** branch **E — the code is defective.** No ADR supersedes
BE-01, and the remediation programme still lists it as open.

**Options:** (A) refactor services to `flush()` and hoist commits to endpoints, money paths first;
(B) write an ADR that formally accepts service-level commits and retire BE-01;
(C) narrow BE-01 to money paths only and document the exception set.

**AI recommendation (advisory): Option A, incrementally, money paths first** (`checkout_service`, `payment_*`),
each as a separate `IMPL`+`TEST` node pair with no behaviour change. Option B is legitimate but requires a Board
minute and contradicts an open P1 remediation item.

---

## CR-006 — Quality bar: 5.7 audit vs 9.0 self-certification

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Owner** | Independent auditor (must not be the implementer) |
| **Status** | OPEN |

`docs/audits/v2/master-engineering-report-v2.md` scores the platform **5.7/10** overall.
`docs/audits/v2/SCORECARD-AFTER-REMEDIATION.md`, dated the **same day**, claims **9.0 in every category** —
with no independent re-audit. It also contains its own invalidation rule:
*"If any evidence above regresses on `main`, drop the affected category immediately."*

**Evidence items that have not held:**

| Scorecard claim | Observed |
|---|---|
| Documentation 9.0, citing `AI_CONTEXT.md` honesty | Body still contains ~1,000 lines of false claims (`CR-015`) |
| Binary availability admin UI | `admin-panel/.../products/page.tsx` bulk path still uses `quantity_delta` stock-adjust |
| Architecture 9.0 | BE-01 still violated in 8 modules (`CR-005`) |
| Ops offsite backup | Script exists; effective only if `BACKUP_OFFSITE_URI` is configured (unknown, `U-04`) |
| Second staging host | Still one VPS (`CR-011`) |

**Options:** (A) commission a v3 audit by a role separated from the implementer, and treat 9.0 as void until then;
(B) demote the scorecard to `EVIDENCE`/`HISTORICAL` and use v2 + remediation as the live bar; (C) keep 9.0 and
document the compensating controls explicitly per category.

**AI recommendation (advisory): B now, A when the wave closes.** Under the authority model, a self-certification is
`EVIDENCE` (rank 9) and cannot outrank the audit it claims to supersede. AODS therefore separates the
**AI Reviewer** and **Auditor** roles from the **Implementer** role by construction (see `ROLE-ARCHITECTURE.md` §6).

---

## CR-007 — PMO files duplicated at two paths, six pairs divergent

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Owner** | PMO |
| **Status** | OPEN |

14 progress ledgers and 5 sprint files exist at both `project-management/X.md` and
`project-management/{progress,sprints}/X.md`. All 5 sprint pairs are identical. **6 of 14 progress pairs diverge:**

| File | Nature of divergence |
|------|---------------------|
| `BACKEND_PROGRESS.md` | Root says `Owner: unassigned`; `progress/` says `Owner: PMO` + checkpoint-close note + `revisit 2026-09-23` |
| `KNOWLEDGE_BASE_PROGRESS.md` | Same owner/notes divergence for KB-001 |
| `DATABASE_PROGRESS.md` | `progress/` copy is a **stub pointing back** to the root copy |
| `STRUCTURED_DATA_PROGRESS.md` | `progress/` has extra LocalBusiness/geo follow-up work and an extra open checkbox |
| `UI_PROGRESS.md` | Different evidence for #93 (root cites merge SHA + staging; `progress/` cites "this PR") |
| `UX_PROGRESS.md` | `progress/` has an extra open item (Google Maps place) |

**Root cause.** `.cursor/rules/pmo-living-system.mdc` step 2 says to update *"the relevant `*_PROGRESS.md`"* without
naming a directory, so each agent picks one. Missing specification `G-08`.

**Options:** (A) `progress/` + `sprints/` canonical, delete root duplicates, update the rule and all inbound links;
(B) root canonical, delete subdirectories; (C) keep both with a generated-mirror step.

**AI recommendation (advisory): Option A** — `project-management/README.md` already documents `progress/` and
`sprints/` as the layout, and the `progress/` copies are the *newer* ones in 5 of 6 divergences. Merge the unique
content forward before deleting. **This requires a human decision because it deletes files.**

---

## CR-008 — Two priority systems with no cross-reference

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Owner** | Owner (as both PMO and Board) |
| **Status** | OPEN |

**System 1 (PMO, rank 7).** `EXECUTIVE_SUMMARY.md`: checkpoint 2026-09-22, KPI *"quality + indexable mid-tail + CWV,
not #1 head-term rank"*; PMO declared *"operationally complete for 31 Shahrivar checkpoint"*; only CAT-002 and KB-001
remain, both deliberately deferred. The always-applied Cursor rule mandates: *"Before large new work: read
`EXECUTIVE_SUMMARY.md` and confirm priority against the 31 Shahrivar checkpoint."*

**System 2 (Board, rank 1).** Wave-1 Canon Lock opened **EPIC-1** on 2026-07-29: slug PDP, 301s, brand hubs, JSON-LD
`@id`. `epic1-ia-readiness.md` lists 8 deliverables.

**The collision.** PRs #126 and #127 delivered EPIC-1 deliverables 1–2 and carry **no PMO task ID**, no `tasks.json`
entry, and no progress-ledger update — violating the very rule that is `alwaysApply: true`. Meanwhile PMO reports
85.3% complete and "operationally complete," which is true for the checkpoint and false for the live workload.

**Options:** (A) register EPIC-1 as PMO tasks (`EPIC1-001…008` or `SEO-005+`) and re-open PMO for a new sprint;
(B) declare the checkpoint closed, archive PMO, and let the Board's EPIC/Wave structure own planning;
(C) keep both, with an explicit mapping table `EPIC-1 deliverable ↔ PMO task ID`.

**AI recommendation (advisory): Option C, implemented as Option A's registration step.** The authority model already
separates *what* (Board) from *when/status* (PMO); what is missing is the join. Without it, the `alwaysApply` rule
will keep being violated, which trains agents to ignore rules — the worst possible outcome.

---

## CR-009 — The authoring source-of-record is outside version control

| Field | Value |
|-------|-------|
| **Severity** | BLOCKER |
| **Owner** | Owner |
| **Status** | OPEN |

`git-development-workflow.md` §"Repo boundary" states:

| Path | Role |
|------|------|
| `Website/backend` | Canonical GitHub repo |
| `Website/docs` | **Authoring SoR**; promote KEEP docs into `backend/docs/` |

`PROMOTION-WAVE1.md` confirms Wave-1 documents were authored in `Website/docs/` and copied into `backend/docs/`,
and that `Website/docs/` still holds *"Proposed packs + audits"*.

**Consequence.** Canon Lock's `PROPOSED` inventory (ADR-001…009/011, RFC-001/002/003/006/007, Domain, KG, PIM,
Property Governance, Data Governance, DQ, `docs/architecture/ai/`, `docs/architecture/search/`,
`docs/governance/repository/`, `docs/roadmap/enterprise/`, and the prompt collection referenced as
`docs/prompts/karzar-enterprise-architecture-prompts.md`) is **not in this repository**. It cannot be reviewed,
diffed, linted, backed up, or read by any agent working from the GitHub checkout. `U-01`.

**Options:** (A) move `Website/docs/` into the repo (e.g. `docs/_authoring/` or a second repo with a submodule);
(B) keep it out but forbid Canon Lock from referencing anything not promoted; (C) promote the whole tree now.

**AI recommendation (advisory): Option B immediately** (make Canon Lock self-contained — this also closes `CR-010`),
**then Option A** for durability. Rationale: a binding index that points outside version control cannot satisfy the
"auditable" or "reproducible" principles, and single-machine authority is a bus-factor-1 data-loss risk.

---

## CR-010 — Canon Lock and Git workflow cite documents that do not exist

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Owner** | Architecture Board |
| **Status** | OPEN |

Verified missing on branch `docs/wave1-canon-lock-promote` (and on `main`):

| Cited path | Cited by | Claimed status |
|------------|----------|----------------|
| `docs/audits/repository-governance-final-lock.md` | `CANON-LOCK.md` §2 | **"PASS (evidence)" — Binding row** |
| `docs/development/development-lifecycle-standard.md` | `CANON-LOCK.md` §2, developer standards §3 | **Binding** |
| `docs/architecture/adr/ADR-001…009, 011` | `adr/README.md` index (links) | Proposed |
| `docs/architecture/rfc/RFC-001/002/003/006/007` | `rfc/README.md` index (links) | Draft |
| `docs/architecture/ai/`, `search/` | `CANON-LOCK.md` §3 | Proposed |
| `docs/governance/repository/`, `docs/roadmap/enterprise/` | `CANON-LOCK.md` §3 | Proposed |
| `docs/architecture/data-quality/baselines-epic0.md` | `rfc/README.md` "Citing EPIC 0" | Referenced as the frozen-baseline source |
| `docs/prompts/karzar-enterprise-architecture-prompts.md` | `adr/README.md` (Canon C0–C10 definition) | Referenced as the Canon definition |
| `docs/audits/worktree-cleanup-execution-plan.md`, `baseline-tag-readiness.md`, `final-repository-state-audit.md` | `git-development-workflow.md` | Referenced |
| `docs/development/local-baseline-environment.md`, `documentation-index.md`, `docs/roadmap/post-migration-development-plan.md` | `git-development-workflow.md` "Related" | Referenced |

**Most serious:** the **Consistency Canon C0–C10** — invoked throughout the governance pack and by the
citation rules — is defined in a file that is not in the repository. Agents are told to respect "Canon C0–C10"
with no way to read it.

**Options:** (A) promote the missing documents; (B) remove or downgrade the dangling rows and inline C0–C10 into
`CANON-LOCK.md`; (C) mark each as `EXTERNAL` with an explicit "not in repo" annotation.

**AI recommendation (advisory): Option B for the Binding rows** (a Binding row pointing at a missing file is
unenforceable), **Option C for Proposed rows.** Enforced going forward by `--gate links`.

---


**NOTE (2026-07-30, after CR-001 Option A):** Canon Lock is on `main`. `--gate links` now reports the
dangling citations in this row as concrete findings (previously invisible because the citing files were
off-main). Those findings are baselined under `conflict_id: CR-010` until Board chooses Option B
(self-contain Canon) or promotes the missing packs. This does **not** close `CR-010`.


## CR-011 — Staging and production are the same host; `main` auto-deploys live

| Field | Value |
|-------|-------|
| **Severity** | BLOCKER |
| **Owner** | DevOps / Release Manager |
| **Status** | OPEN |

`deploy-production.yml` header: *"Production host is NOT split yet — same VPS as staging (karzartools.com).
Dangerous to auto-deploy: ONLY workflow_dispatch + GitHub Environment `production`."*

But `deploy-staging.yml` triggers on **push to `main`** (path-filtered) and deploys to that same VPS and the same
public domains, with **no human approval**, then runs `publish_seo003_articles.py` against it.

**Net effect:** the guarded "production" workflow is ceremonial. Any merge to `main` touching `app/**`,
`frontend/**`, `deploy/**`, `scripts/**`, or requirements/Docker files ships to the live public site immediately.
Both observed Deploy Staging failures happened *after* the smoke gate, i.e. against live.

This also contradicts `git-development-workflow.md` §5: *"Promote: Git merge → local/staging verify → Alembic on
target → production"*, which presumes distinct stages.

**Options:** (A) provision a real staging host and re-point `deploy-staging.yml`;
(B) keep one host but require `workflow_dispatch` + environment approval for *all* deploys, removing the push trigger;
(C) rename the workflows to `deploy-live.yml` and delete `deploy-production.yml` so the documentation is honest.

**AI recommendation (advisory): Option B immediately** (a one-line trigger change buys a real human gate),
**Option A as the durable fix, Option C's honesty applied either way.** Until then, AODS treats every merge to `main`
as a **production release** and routes it through human checkpoint **HC-12**.

---

## CR-012 — `openapi/v1.json` has no CI verification

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Owner** | Backend Architect |
| **Status** | MITIGATED |

`docs/API_CONTRACT.md` designates `openapi/v1.json` as the machine contract and documents a regeneration command.
The snapshot holds 81 paths and 115 schemas. **No workflow regenerates or diffs it** — `backend-ci.yml` runs only
ruff, mypy, and pytest. `tests/test_p5_contract.py` exercises `app.openapi()` behaviour but performs no snapshot diff.

The v2 documentation audit already caught this drifting once (audit cited 71 paths; the file now has 81), proving
the failure mode is live rather than theoretical.

**The snapshot is drifted right now, and `--gate openapi` proves it.** Running the gate against `main` reports:

```
FAIL  openapi   1 checked
  - openapi/v1.json: path present in the app but missing from the snapshot:
    /api/v1/products/slug/{slug} (CR-012)
```

`GET /api/v1/products/slug/{slug}` was added by PR #126 (`feat(api): EPIC1 product-by-slug and brand meta for
hubs`). The snapshot was last regenerated in PR #111. Two EPIC-1 pull requests therefore merged while the
declared machine contract was stale, and nothing anywhere reported it — this is the same auditability void as
`CR-001`, arriving through a different door. The gate is a regression test for exactly this event.

**Options:** (A) add a CI step that regenerates and `git diff --exit-code`s the snapshot; (B) add a pytest that
compares `app.openapi()` to the file; (C) stop committing the snapshot and publish it as a build artifact.

**AI recommendation (advisory): A and B** (CI for the gate, pytest for local feedback). Implemented as
`--gate openapi` in `aods/tools/`. Option C loses the reviewable diff, which is the snapshot's main value.


**DECISION (2026-07-30, Mohammad Shebahati — Board order in operator session):** Regenerate and commit
`openapi/v1.json` from `app.openapi()` now (ADR/API_CONTRACT regeneration rule). Verified:
`GET /api/v1/products/slug/{slug}` present; path count 81→82; `--gate openapi` PASS; related pytest 47 passed.
Baseline entry for this drift removed. **Follow-up remains:** wire `--gate openapi` (or equivalent pytest
snapshot diff) as a required CI check — Option A/B — tracked under Phase 4 / `OI-GOV-05`. Until then status is
**MITIGATED**, not CLOSED.


---

## CR-013 — Orphan and untracked work items

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM · **Owner** PMO · **Status** OPEN |

| Item | Problem |
|------|---------|
| `CONTENT-URL-001` | Marked `done` 100% in `CONTENT_PROGRESS.md` (both copies) but absent from `tasks.json`, all CSV exports, `KANBAN_BOARD.md`, sprints, `DONE.md`, `CHANGELOG.md`. Its own evidence line says "PR pending" while claiming done. |
| `SEO-001 follow-up` (LocalBusiness geo / Maps place) | In `CHANGELOG.md` and two `progress/` ledgers, no task ID anywhere |
| `SEC-001` | `DONE.md` records "merge SHA pending" while status is `done` |
| `KANBAN_BOARD.md` | `SEC-001` sits under `## todo` while marked `` `done` 100% `` |
| `MASTER_ROADMAP.md` | Outcomes O3–O6 unchecked although all constituent tasks are `done` |
| `exports/milestones.json` | `M0 "PMO live"` still `in_progress` although PMO-001 is `done` |
| `SPRINT_00/01.md` | `## Goals` checkboxes unchecked while every task under them is checked |
| `project-management/README.md` | Says *"~25% of tracked backlog hours claimed"*; actual is 85.3% |
| `printable/PMO_31_Shahrivar_wallboard.{html,pdf}` | Shows `SEO-003 5%`, `REL-001 0%`; both are now 100% |

**AI recommendation (advisory):** register the orphans as real task IDs, then run one `PMO-SYNC` node with
`--gate pmo` enforcing parity thereafter. The wallboard and CSVs should be marked `GENERATED` and regenerated
rather than hand-patched.

---

## CR-014 — EPIC-1 deliverable 5 (Brand Hub) unimplemented and unspecified

| Field | Value |
|-------|-------|
| **Severity** | HIGH · **Owner** Frontend Architect + SEO Engineer · **Status** OPEN |

`epic1-ia-readiness.md` requires: *"Ship Brand Hub `/brands/{slug}` for priority brands"* and
*"Expose Brand meta needed for hubs."* ADR-010 §4 mandates `/brands/{slug}` and names the priority brands
(ASTPOWER, INSIZE, Dasqua, Chumpower, Mitutoyo, SAN OU) via RFC-005.

**Observed:** `frontend/Storefront/src/app/` contains no `brands/` route. Backend brand meta landed in PR #126.
Deliverables 1–2 (slug PDP + 301) shipped in #127.

**Missing specification `G-01`:** no document defines the Brand Hub *page contract* — required regions, content
model, PLP behaviour, pagination, meta/JSON-LD shape, or the empty-state rule when a brand has few products.
`epic1-ia-readiness.md` warns of *"Brand hub thin content"* and mandates *"No new indexable thin facet 'hubs'"*
but sets no threshold.

**Resolution requires a human decision on:** minimum product count to publish a hub, indexability rule below that
threshold, and whether hub intro copy is authored (like `content/hubs/intros.json`) or generated.
**AODS forbids an agent from inventing these**; the correct output is a `SPEC` node producing a page contract for
Board review.

---

## CR-015 — `frontend/AI_CONTEXT.md` is an active hallucination source

| Field | Value |
|-------|-------|
| **Severity** | BLOCKER for AI-executed work · **Owner** Documentation Architect · **Status** OPEN |

The file is 37 KB / ~1,053 lines across 21 sections. Its banner (added 2026-07-25) states:

> *"OBSOLETE AS SoT… Confirmed false claims include: SQLAdmin `/admin`, 'no refresh token', missing
> checkout/OTP/blog/hero, ComingSoon admin pages, 5-digit migration head… Rewrite of this file is Wave 1 of remediation."*

The rewrite never happened. The false body remains. Verified false against code: no SQLAdmin dependency exists;
refresh-token rotation exists; checkout/OTP/blog/hero endpoints exist (`app/api/endpoints/storefront*.py`, `auth.py`);
admin orders/customers pages exist; the Alembic head is `z1a2b3c4d5e6`, not `f1a2b3c4d5e6`.

**Why a banner is insufficient for AI.** Retrieval is chunk-based. An agent asking "how does admin auth work?" can
receive §10 ("بدون refresh token") without ever seeing §0's banner. A human reading top-down is protected; an
Auto Mode agent is not. `SCORECARD-AFTER-REMEDIATION.md` nonetheless cites this file's "honesty" as evidence for
Documentation 9.0 (`CR-006`).

**Options:** (A) truncate to the banner plus §21 (the still-useful remediation log) and move the rest to
`docs/archive/AI_CONTEXT-2026-07-11.md`; (B) delete it; (C) rewrite it as a correct context document;
(D) leave it and rely on the AODS forbidden-context list.

**AI recommendation (advisory): Option A now, and do not choose C.** A correct AI context document is exactly what
AODS provides in a maintained, validated form; recreating it as one large hand-maintained file reproduces the
failure. Option D alone is insufficient because it protects only AODS-governed agents.

Interim mitigation, already in force: `forbidden_context: true` in `registry/document-registry.yaml`, inlined into
every prompt's `## FORBIDDEN CONTEXT` block.

---

## CR-016 — Duplicate pytest configuration

| Field | Value |
|-------|-------|
| **Severity** | LOW · **Owner** QA Engineer · **Status** OPEN |

`pytest.ini` and `pyproject.toml` `[tool.pytest.ini_options]` both define `testpaths`, `python_files`, `addopts`,
and the same three markers. `pytest.ini` wins by precedence, so the `pyproject.toml` block is dead configuration
that will silently diverge. Also, only 3 of 276 tests actually use a marker.

**AI recommendation (advisory):** keep one file (`pyproject.toml`, alongside ruff/mypy/coverage), delete the other,
and either use the markers or drop them.

---

## CR-017 — Repository hygiene: 62 unmerged branches, 45 worktrees

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM · **Owner** Owner · **Status** OPEN |

`git branch -r --no-merged origin/main` → **62** on 2026-07-29: undeleted post-squash branches (ahead 1–2 = merge
artifact only), 20 dependabot, and genuinely stale ones (e.g. `chore/insize-catalog-108A-enrich`,
`feat/v2-complete-backlog` 57 behind, `fix/hero-composition-images`). The count drifts daily, so the **command**
is the citable fact and the number is a dated measurement.

`git-development-workflow.md` reports **45 local worktrees**, that local `main` is held by worktree
`backend-stat-fix` (22 behind), and that the primary checkout is parked on `chore/phase9-align-origin-main`.
It points to `docs/audits/worktree-cleanup-execution-plan.md`, which is **not in the repo** (`CR-010`).

`docs/CONTRIBUTING.md` requires *"delete the branch after merge"* — not happening.
Per `git-development-workflow.md` §7, destructive git actions need *"a written plan + confirmation"*, so no agent
may clean this up unilaterally. Decided by the owner at **`HC-03`**, since this is a register entry rather than an
AODS amendment.

---

## CR-018 — PR checklist is Accepted but there is no PR template

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM · **Owner** Documentation Architect · **Status** OPEN |

`pr-checklist.md` is **Accepted** and says *"Paste into PR description or use as review gate."*
`documentation-citation-rules.md` defines a minimum citation block. `karzar-developer-standards.md` §11 asks the
open question: *"CI template to auto-comment PR checklist?"*

No `.github/pull_request_template.md` exists. Compliance is therefore memory-based — which is why only ~11% of
commits carry a task ID, and why the emergent template (`## Summary` / `## Canon Lock` / `## Test plan` /
`Made with Cursor`) varies between PRs.

**AI recommendation (advisory):** add `.github/pull_request_template.md` generated from `pr-checklist.md` plus the
citation block, and enforce with `--gate citation`. Cheap, high leverage, no behaviour change.

---

## CR-019 — Image import: paused by one plan, active in another

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM · **Owner** Owner · **Status** OPEN |

`docs/KNOWLEDGE_PLATFORM_PHASE3_IMPLEMENTATION_ROADMAP.md` states product image import is **paused** pending the
knowledge track. `docs/CATALOG_IMAGES_PLAN.md` + `CATALOG_IMAGES_PROGRESS_2026-07-25.md` are **actively executing**
image import with live DB counts. Both are correctly labelled; the **priorities** conflict.

Contextually, KB-001 is deliberately deferred past 2026-09-22, which suggests the image plan should win — but no
document says so.

**AI recommendation (advisory):** annotate the Phase-3 pause as superseded-for-now by the deferral of KB-001,
recorded in `DECISIONS.md`. A one-line decision closes it.

---

## CR-020 — Bilingual pairs diverge, including contradictory API paths

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM · **Owner** Documentation Architect · **Status** OPEN |

| Pair | Divergence |
|------|-----------|
| `frontend/docs/gaps/01-fe-ahead-be-needed-{en,fa}.md` | EN proposes `/api/v1/settings/site`; FA proposes `/cms/site-settings` or `/settings`. **Two different contracts for an unbuilt endpoint.** |
| `frontend/docs/gaps/02-be-exists-fe-should-use-{en,fa}.md` | EN 2026-07-18; FA 2026-07-24 with additional completed items — FA ahead |
| `frontend/docs/deploy/DEPLOYMENT_{en,fa}.md` | EN describes split-host topology; reality is one VPS (`CR-011`) |

**AI recommendation (advisory):** designate one language as normative per document (FA for operator-facing, EN for
contracts), mark the other a translation with a `translated_from` header, and require both to change in the same PR.
Do not let an unbuilt endpoint have two proposed paths — that is a specification defect, resolvable only by the
Backend Architect.

---

## CR-021 — Release/rollback owners unnamed while REL-001 is done

| Field | Value |
|-------|-------|
| **Severity** | HIGH · **Owner** Owner · **Status** OPEN |

`EXECUTIVE_SUMMARY.md`: *"REL-001 Release freeze documentation pack complete (GO still needs named release/rollback
owners…)"*, yet `tasks.json` has `REL-001` `done` 100%. `BLOCKERS.md` lists the unassigned release/rollback owner as
open. `DECISIONS.md` **D6** (*"Owner matrix for P0 tasks (fill names)"*) is unchecked, while **D8** assigns PMO as
owner only for the two deferred tasks.

With a single operator and `CODEOWNERS` `* @Shebahati`, "named owners" resolves to one person for authoring,
review, approval, deployment, and rollback — meaning **no separation of duties on the release path**, and a
bus factor of 1 (`RISK-REGISTER` R-09).

**AI recommendation (advisory):** either name a second human for rollback authority, or explicitly record
"single-operator release model accepted, with automated rollback (`git revert` + documented restore) as the
compensating control." Marking REL-001 done while a GO blocker is open is exactly the pattern `CR-006` describes.

---

## CR-022 — Availability semantics: documented vs implemented

| Field | Value |
|-------|-------|
| **Severity** | MEDIUM · **Owner** Backend Architect · **Status** OPEN |

`docs/FRONTEND_INTEGRATION.md` documents `low_stock` as true when quantity < 10, and `availability` derived from
stock quantity. Code (`app/crud/product.py`) always returns `low_stock: False` and derives availability from the
binary `is_available` flag. `README.md` and `docs/HESABFA.md` correctly state the binary model — warehouse counts
live only in Hesabfa — so the integration guide is the stale document.

Legacy routes make it worse: `GET /products/{id}/stock` still returns a `stock_quantity` field that is *"not a real
count"*, and `POST /products/{id}/stock/adjust` is deprecated but still used by the admin bulk path (`CR-006`).

**AI recommendation (advisory):** correct `FRONTEND_INTEGRATION.md` to the binary model, add a deprecation note to
the legacy stock fields in `API_CHANGELOG.md`, and migrate the admin bulk path to the availability endpoint.
Three separate nodes — not one PR.

---

## CR-023 — Broken relative links inside merged documentation

| Field | Value |
|-------|-------|
| **Severity** | LOW · **Owner** Documentation Architect · **Status** OPEN |

`--gate links` reports two link targets that do not resolve on `main`, both inside a document that *is* on
`main`. These are distinct from `CR-010` (Canon Lock citing documents that do not exist anywhere) and from
`CR-001` (citations resolving only on an unmerged branch): here the target document exists, and the link is
simply written relative to the repository root rather than relative to the linking file.

| Location | Link as written | Actual path | Correct relative form |
|---|---|---|---|
| `docs/BACKEND_CHANGES.md:67` | `docs/LOCAL_DEV_FRONTEND.md` | `docs/LOCAL_DEV_FRONTEND.md` | `LOCAL_DEV_FRONTEND.md` |
| `docs/BACKEND_CHANGES.md:99` | `docs/TESTING.md` | `docs/TESTING.md` | `TESTING.md` |

Registered rather than fixed for two reasons. First, `docs/BACKEND_CHANGES.md` is classified `HISTORICAL` in
[`../registry/document-registry.yaml`](../registry/document-registry.yaml), and editing a historical record
to make a validator green is the wrong instinct — historical documents are evidence of what was written at
the time. Second, this AODS pack is process-only and does not touch product documentation; doing so would
violate the node-type path separation it defines.

**AI recommendation (advisory):** fix both links in a `DOC` node, since a two-character path correction does
not alter the historical content. Alternatively, declare `HISTORICAL` documents exempt from link checking —
but that weakens the gate, so the cheap fix is preferable.

**Why this row exists at all.** `--write-baseline` emits a warning for any entry it cannot attribute to a
`CR-nnn`. These two were the only unattributed entries, and leaving them unattributed would have turned the
baseline into exactly the silent suppression list the validation framework forbids.

---

## Change log for this register

| Date | Change | By |
|------|--------|-----|
| 2026-07-29 | Register opened with CR-001…CR-022 from the AODS Phase-0 audit | AODS design task |
| 2026-07-29 | Added CR-023 — broken relative links surfaced by `--gate links` and flagged as unattributed by the baseline writer | AODS design task |
| 2026-07-30 | CR-012 snapshot regenerated (MITIGATED); CI wiring deferred to Phase 4 | Operator session under Board order |
