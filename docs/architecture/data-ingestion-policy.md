# Data Ingestion Policy — Importers, Enrichers, and Controlled Pipelines

**Document type:** Architecture / Ops Governance RFC (binding policy)  
**Status:** Binding after Phase 4 of baseline migration; normative for all catalog writes  
**Date:** 2026-07-28  
**Owner:** Backend lead (importers) + Platform Architect (policy)  
**References:**  
- Sync SoT: `docs/audits/production-to-development-synchronization-strategy.md`  
- Execution plan: `docs/operations/database-baseline-migration-plan.md`  
- Quality gate: `docs/audits/production-baseline-quality-report.md` (**ACCEPT BASELINE**)  
- Readiness: `docs/operations/baseline-migration-readiness.md`  
- Runbook: `docs/operations/production-to-local-baseline-runbook.md`  
- Lifecycle: `docs/architecture/development-lifecycle-standard.md`  
- Registry: `docs/architecture/DOCUMENT_GOVERNANCE.md`  
- As-implemented flow: `docs/architecture/specification-data-flow.md`  
- Runbook (scripts): `backend/docs/OPERATIONS.md`  

**Non-goals:** Re-auditing product census · Designing full PKM · **Changing importer/application code in this RFC** · Duplicating the migration plan or runbook · Creating a second competing ingestion policy file.

---

## 1. Purpose

Govern how catalog and specification data may enter KarzarTools environments so that **Production is never the developer sandbox**, and so that after the production→development baseline cutover the platform obeys:

**Git → Local → Alembic → Validation → Production Deploy**

plus a **single versioned data pipeline** for intentional catalog transforms.

This is the **sole** living ingestion policy (DOCUMENT_GOVERNANCE: one topic, one living doc). Conceptual drafts such as `data-governance.md` do not override this file for importers.

---

## 2. System of Truth (SoT)

### 2.1 Binding ADR-001 (referenced)

Full text: migration plan §2 and DOCUMENT_GOVERNANCE §2.4.

| Item | Binding statement |
|------|-------------------|
| Current Production dataset (~5900 / audited **5901**) | **TEMPORARY baseline source only** |
| **System of Truth for product data transformation** | **Versioned Data Pipeline** (+ Git-controlled changes) |
| After sync — Production PostgreSQL | Runtime **operational** store (deployment *result*), **not** origin of knowledge |
| Schema SoT | Git + Alembic |
| Knowledge model SoT | Future PKM (prerequisites only; not implemented here) |
| API layer | Production API exposing validated data |

**Final principle:** Leave **Database as SoT** → **Versioned Knowledge and Data Pipeline as SoT**.

**Enforce:** **ONE CODEBASE · ONE DATABASE LIFECYCLE · ONE MIGRATION PATH · ONE VERSIONED DATA PIPELINE · ONE SOURCE OF TRUTH**

### 2.2 What “Versioned Data Pipeline” means

A catalog mutation is legitimate only when it is:

1. Represented in **Git** (script, mapping, input refs, or approved job definition), and  
2. Declared with the mandatory attributes in §5, and  
3. Executed in the correct **Category** (A / B / C) with environment rules in §6–§7.

Raw production rows, laptop dumps pushed to VPS, and undocumented Admin click-ops are **not** the SoT.

---

## 3. Policy statement (normative)

1. **Every importer / enricher / bulk updater must be:** version controlled, reproducible, auditable, reversible.  
2. **Every pipeline must declare:** Source, Destination, Owner, Validation, Audit Trail, Rollback (§5).  
3. **No write path may bypass** the controlled pipeline (including ad-hoc Admin API spam from laptops as a substitute for a versioned job).  
4. **Ban default live-API imports** against `https://api.karzartools.com` for routine work.  
5. **Align** all routine transforms with: develop/test on **local** API → commit → PR → validate → controlled production execution (if any).  
6. **Prod→Dev DB dump** is Category **C** (historical/baseline migration), not a substitute for Categories A/B.

Evidence that script defaults currently point at production (treat as **non-compliant for routine use** until overridden):

```text
KARZAR_API_BASE default = https://api.karzartools.com/api/v1
```

Examples (repo): `backend/scripts/shopmill_insize_sync.py`, `mitutoyo_import.py`, `azarsanat_import.py`, `insize_price_update.py`, `catalog_remediation.py`, and related enrich scripts documented in `specification-data-flow.md`.

**This policy does not modify those scripts**; operators must override destination explicitly and remediate defaults in a future code PR under the development lifecycle standard.

---

## 4. Write-path analysis (in scope)

All of the following are **ingestion write paths** and must obey this policy when they create or mutate catalog data.

### 4.1 Supplier importers

| Aspect | As-implemented (evidence) | Policy requirement |
|--------|---------------------------|--------------------|
| Mechanism | Crawl → JSONL → `*_import.py` / sync → Admin `POST /products/` | Category **A** for routine; **B** only when ticketed for prod |
| Examples | `shopmill_insize_sync.py`, `mitutoyo_import.py`, `azarsanat_import.py` | Named Owner; Source = crawl artifact + checksum |
| Risk | Defaults to production API | Explicit local `KARZAR_API_BASE` for A; never “forgot to override” |

### 4.2 Enrichment

| Aspect | As-implemented | Policy requirement |
|--------|----------------|--------------------|
| Mechanism | Leaflet/catalog merges → Admin `PUT /products/{id}` | Same Category A/B rules; prefer scoped SKU/brand allowlists |
| Examples | `dasqua_catalog_2025_enrich.py`, `enrich_mitutoyo_from_leaflets.py`, related `*_enrich*.py` | Validation must include sample before/after; Rollback = pre-backup on B |
| Risk | Silent overwrite of specs | Dry-run when available; fail-closed on unexpected delta |

### 4.3 Admin create / update

| Aspect | As-implemented | Policy requirement |
|--------|----------------|--------------------|
| Mechanism | Admin UI → `buildSpecificationsPayload` → `POST`/`PUT /products/` | **Interactive single-SKU** fixes by authorized admins are allowed on the environment they administer |
| Bulk via UI | Repeated manual creates/edits as a substitute for a script | **Forbidden** as an undocumented bulk transform — promote to a versioned Category A/B pipeline |
| Prod admin | Operational store maintenance | Must not introduce untracked mapping logic; material transform rules belong in Git |

### 4.4 Bulk updates

| Aspect | As-implemented | Policy requirement |
|--------|----------------|--------------------|
| Mechanism | Price/update/remediation scripts (e.g. `insize_price_update.py`, `catalog_remediation.py`) | Always Category A first; Category B only with ticket + backup |
| ORM/CSV seed | Historical `seed_products_from_csv.py` / direct ORM | Treat as pipeline; no silent laptop→prod |
| Remediation | Quality debt from ACCEPT BASELINE (sparse specs, UNKNOWN brands) | Fix via A→B pipelines after local baseline — not via pre-dump live cleans |

---

## 5. Mandatory attributes (every pipeline)

Before a pipeline may write **any** environment, the owning PR or ops ticket must record **all** of:

| Field | Requirement |
|-------|-------------|
| **Source** | File path, supplier feed, catalog PDF/CSV, crawl JSONL, or upstream system; version or **checksum** of inputs |
| **Destination** | Explicit API base + environment (`local` \| `production` \| future named env) — never implied |
| **Owner** | Named human/team accountable for blast radius |
| **Validation** | Count deltas, SKU uniqueness, required fields, sample spot-checks, fail-closed criteria |
| **Audit Trail** | Ticket ID, Git SHA, command line, env overrides, start/end UTC, result summary retained (no secrets in git) |
| **Rollback** | Pre-`backup_db.sh` restore point (required for Category B), or reversible write design, or documented compensating job |

### Minimum bar

| Property | Bar |
|----------|-----|
| Version controlled | Lives under Git (`backend/scripts/` or approved package); no one-off desktop scripts for prod |
| Reproducible | Pinned inputs; documented flags; no silent dependency on laptop-only files |
| Auditable | Audit Trail complete; no anonymous production writes |
| Reversible | Backup-before-write on prod; prefer idempotent upserts; know how to restore |

### Pipeline declaration template

```text
PIPELINE DECLARATION
--------------------
Name: ____________________
Category: A | B | C
Git path: backend/scripts/__________
Owner: ____________________
Ticket: ____________________
Source (path/URI + checksum/version): __________
Destination env: local | production
KARZAR_API_BASE (explicit): __________
Scope (brands/SKUs/limit): __________
Validation rules: __________
Audit Trail location (ticket/ops note): __________
Rollback strategy: pre-backup path / compensating job: __________
Dry-run available (Y/N): __________
Prod run approved by (Category B): __________
Pre-backup artifact (Category B): backups/karzar________.sql.gz
Start UTC / End UTC / Result: __________
```

---

## 6. Import categories

Exactly one category applies per execution.

### Category A — Development Import

| Field | Rule |
|-------|------|
| **Purpose** | Develop, map, dry-run, iterate enrich/import against **local** prod-baseline DB |
| **Destination** | `KARZAR_API_BASE=http://127.0.0.1:8000/api/v1` (or local compose URL) only |
| **Approval** | PR for script/mapping changes; local run may proceed under Owner |
| **Backup** | Optional local snapshot before large experiments |
| **Forbidden** | Any write to `api.karzartools.com` |

```bash
export KARZAR_API_BASE=http://127.0.0.1:8000/api/v1
```

### Category B — Controlled Production Import

| Field | Rule |
|-------|------|
| **Purpose** | Intentional catalog mutation on the live operational store |
| **Destination** | Explicit `KARZAR_API_BASE=https://api.karzartools.com/api/v1` |
| **Approval** | Change ticket + Prod DB owner (or delegate) + pipeline declaration §5 |
| **Backup** | **Mandatory** VPS `./scripts/backup_db.sh` before write; retain artifact |
| **Scope** | Prefer brand/SKU allowlist; limited blast radius |
| **Post** | Validation + Audit Trail; Rollback path identified |
| **Forbidden** | “Quick” runs without ticket/backup; relying on script default URL |

### Category C — Historical Migration Import

| Field | Rule |
|-------|------|
| **Purpose** | One-time or periodic **dataset baseline/refresh** (Prod→Dev dump/restore), or emergency DR |
| **Mechanism** | `backup_db.sh` / `restore_db.sh` (+ uploads) per sync audit and `production-to-local-baseline-runbook.md` |
| **SoR note** | Artifacts are **temporary baseline**, not permanent knowledge SoR (ADR-001) |
| **Prod→Dev** | Allowed as baseline/refresh under readiness = READY |
| **Dev→Prod dump** | **Emergency/DR only** — never routine catalog promotion |
| **Not a substitute** | Does not replace Category A/B for mapping/enrichment work |

---

## 7. Environment rules (summary)

### 7.1 Local (default for Category A)

- Schema: Alembic only.  
- Hesabfa: disabled per migration plan / `HESABFA.md`.  
- Develop against prod-baseline local DB after runbook Phase 6.

### 7.2 Production (Category B only)

Allowed only when **all** hold:

1. Ticket + §5 declaration (Category B).  
2. Pre-run VPS `backup_db.sh`.  
3. Explicit production `KARZAR_API_BASE`.  
4. Limited blast radius.  
5. Post-run validation.  
6. Rollback path identified.

### 7.3 Explicit forbidden patterns

| Forbidden | Rationale |
|-----------|-----------|
| **Uncontrolled production writes** (no ticket, no declaration, no backup) | Catalog drift; dual-write; violates SoT |
| **Laptop → production import** as routine (API defaults or ad-hoc Admin bulk) | Sync audit §3.4 / §7.2; caused Local≠Prod divergence |
| **Laptop → production DB dump restore** as routine (`export-local-db.sh` → `restore-db-staging.sh`) | Overwrites larger live catalog (`STAGING_DEPLOY.md` §3) |
| **Undocumented transforms** (spreadsheet → live PUT loops; one-off desktop scripts; untracked mapping) | Not reproducible / not auditable |
| Hand SQL on production for “quick import” | Bypasses Alembic + pipeline Audit Trail |
| Using production API as developer sandbox | Violates ADR-001 |
| Enabling prod Hesabfa credentials on laptop “to test import” | Commerce side effects |
| Pre-baseline “cleanups” on live data that contradict **ACCEPT BASELINE** | Quality report + readiness |

---

## 8. Lifecycle alignment

```text
Requirement
  → Architecture / Design Decision (mapping / scope / Category)
  → Git Branch + Commit (script + input refs + declaration)
  → Code Review (PR: validation + rollback + Audit Trail plan)
  → Local Dev DB execution (Category A)
  → Testing / Validation gates
  → Alembic if schema impact
  → Production Deployment (code) and/or Category B Controlled Production Import (data)
```

Cross-ref: `docs/architecture/development-lifecycle-standard.md` (mandatory platform lifecycle).

**Direction table** (sync audit §7.3, adopted):

| Direction | Role |
|-----------|------|
| Import-from-prod (DB dump → local) | Category **C** — baseline / periodic refresh |
| Import-from-local (dump → VPS) | Category **C** emergency/DR only — never routine |
| API import/enrich scripts | Category **A** local-first; Category **B** controlled release |

---

## 9. Ownership

| Asset | Owner |
|-------|-------|
| This policy | Platform Architect |
| Script inventory / future default remediation (code PR) | Backend lead |
| Category B production runs | Prod DB owner + DevOps (backup) |
| Category C baseline execution | DevOps Migration Engineer + Prod DB owner |
| Policy exceptions | Platform Architect + Prod DB owner (**written**) |
| Conflicts with conceptual `data-governance.md` | **This policy wins for importers** until Canonical Architecture merges them |

Known script families (non-exhaustive; see `specification-data-flow.md`):  
`*_import.py`, `shopmill_insize_sync.py`, `*_enrich*.py`, `insize_price_update.py`, `catalog_remediation.py`, SEO description dry-runs — all subject to this policy when writing catalog data.

---

## 10. Acceptance criteria

- [ ] No routine catalog mutation targets `api.karzartools.com` without Category **B** ticket + declaration  
- [ ] Every active importer/enricher/bulk updater has Owner + Source / Destination / Validation / Audit Trail / Rollback  
- [ ] Supplier import, enrichment, admin bulk, and bulk-update paths are classified A/B/C per execution  
- [ ] Local development uses local API base after baseline restore  
- [ ] Production data writes are preceded by `backup_db.sh` and have Rollback  
- [ ] Team acknowledges SoT = **Versioned Data Pipeline**; production DB is runtime store  
- [ ] Forbidden list (§7.3) acknowledged  
- [ ] No second competing ingestion policy file exists  

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| Muscle memory of production defaults | Freeze; require explicit env in tickets; future code default change (out of scope here) |
| “Quick fix” Admin bulk on prod | Ban undocumented transforms; require pipeline declaration |
| Irreversible enrich | Mandatory pre-backup on B; scoped runs |
| Shadow pipelines in worktrees | Only Git-tracked scripts under primary backend tree |
| Confusing baseline dump with ingestion SoR | ADR-001; Category C ≠ permanent SoT |
| Cleaning prod before baseline | Blocked by quality **ACCEPT BASELINE** |

---

## 12. Checkpoints

| CP | Meaning |
|----|---------|
| IP-0 | Policy read + owners named (aligns migration CP-4) |
| IP-1 | Inventory of write-capable scripts listed under Owner |
| IP-2 | First post-baseline enrich/import completed **Category A** with declaration |
| IP-3 | First Category **B** run (if any) follows §7.2 end-to-end |
| IP-4 | Category **C** baseline completed per runbook (when readiness = READY) |

---

## 13. Related documents (no duplication of SoT)

| Topic | Authoritative file |
|-------|-------------------|
| Why Local ≠ Prod / sync mechanics | Sync audit |
| Phased migration ADRs/checkpoints | Migration plan |
| Execute dump/restore | Baseline runbook |
| READY / NOT READY | Readiness doc |
| Day-to-day change ownership | Development lifecycle standard |

---

*End of data-ingestion-policy.md — single binding ingestion policy; no importer code modified by this document.*
