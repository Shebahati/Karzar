# Task record — KB-REMEDIATION-00 — Architecture Contract

| Field | Value |
|-------|-------|
| **NODE_ID** | KB-REMEDIATION-00-ARCHITECTURE-CONTRACT |
| **Follow-on nodes** | 00A-OWNER-REVIEW-AMEND · **00B-FINAL-CORRECTIONS-REGISTER** |
| **Prompt** | Prompt 00 / 00A / **00B** |
| **Date** | 2026-08-02 |
| **Change class** | Documentation / registry / PMO metadata (C1) |
| **Status** | COMPLETE — **READY FOR OWNER REVIEW** (not Board-Accepted) · SPEC **v0.3.0 Proposed** |
| **Authority** | Proposed SPEC only; does not claim Board acceptance |

## Allowlist honored

| Path | Action |
|------|--------|
| `docs/architecture/specs/SPEC-master-knowledge-base-remediation.md` | Created (00) · Amended (00A → v0.2.0) · **Amended (00B → v0.3.0)** |
| `aods/reports/tasks/KB-REMEDIATION-00-ARCHITECTURE-CONTRACT.md` | Created (00) · Updated (00A/00B) |
| `aods/registry/document-registry.yaml` | **Added** `SPEC-MASTER-KB-REMEDIATION` (00B) |
| `project-management/exports/tasks.json` | **Added** KB-REMEDIATION-00 / 00A / 00B (00B; authored SoT) |

No production code, tests, migrations, frontend, Accepted ADRs, Canon decisions, or seed files modified.

## Inputs read

| Path | Role |
|------|------|
| `docs/architecture/karzar-knowledge-platform-master-architecture.md` | Bible invariants (Postgres SoR, P5–P6 dual-write gate, modular contexts) |
| `docs/architecture/adr/ADR-013-knowledge-edge-fact-storage.md` | Postgres overlay; no graph DB; no dual-write auth |
| `docs/architecture/adr/ADR-014-product-knowledge-entity-identity.md` | PKE = `products.id` |
| `docs/architecture/specs/SPEC-knowledge-graph-model.md` | Edge statuses, provenance, soft-link migration |
| `docs/architecture/specs/SPEC-knowledge-graph-registry.md` | Relation vocabulary + KB-001 freeze |
| `docs/architecture/specs/SPEC-product-knowledge-entity-model.md` | PKE vs commerce; Facts/content model |
| `docs/architecture/specs/SPEC-property-dictionary-system.md` | Property/Fact/units; dual-write gated |
| `docs/architecture/specs/SPEC-industrial-taxonomy-model.md` | Knowledge dimensions ≠ second Category DAG |
| `docs/API_CONTRACT.md` | Error envelope |
| `docs/ARCHITECTURE.md` | Layering endpoints → services → crud → models |
| `docs/architecture/CANON-LOCK.md` | ADR-013/014 Accepted rows |
| `app/api/deps.py` | 401 / 403 semantics |
| `app/api/endpoints/product_common.py` | `_guard_inactive_product` public PDP gate |
| `app/db/models/content.py` | Article columns for public DTO |
| `app/db/models/product.py` | Brand / Category / Product columns |
| `app/db/models/knowledge.py` | Edge indexes / identity |
| `app/api/endpoints/knowledge.py` | As-built public edges + admin sync |
| `app/crud/knowledge.py` | As-built `asserted\|published` visibility |
| `app/schemas/knowledge.py` | Response/counter schemas |
| `app/services/knowledge_edge_projector.py` | Projection/publish defaults |
| `tests/test_knowledge_edges.py` | As-built expectations |
| `frontend/Storefront/.../product-knowledge-rail.tsx` | Local blog rail (not API) |
| `frontend/admin-panel/.../knowledge-edges-browser.tsx` | Admin read-only browser |
| `project-management/progress/KNOWLEDGE_BASE_PROGRESS.md` | KB-001 progress context |

## Files changed

1. `docs/architecture/specs/SPEC-master-knowledge-base-remediation.md` (v0.1.0 → 0.2.0 → **0.3.0**)
2. `aods/reports/tasks/KB-REMEDIATION-00-ARCHITECTURE-CONTRACT.md`
3. `aods/registry/document-registry.yaml` (00B)
4. `project-management/exports/tasks.json` (00B)

## Decisions recorded in the SPEC (Proposed) — original 00

1. **Public vs admin boundary:** Raw `GET /knowledge/edges` becomes super-admin-only; public uses resolved PKE read-model only.
2. **Publication:** `asserted` internal-only; `published` public; `rejected`/`deprecated` never public; article public edges require published article + non-future `published_at` + public target product.
3. **Compat:** Neighborhood remains temporarily but published-only, provenance-stripped, deprecated toward `GET .../knowledge`.
4. **Projection:** Scoped HTTP inline limits; full sync via durable Postgres job rows + CLI worker (batches, retry, locking, checkpoints, idempotency).
5. **Counters:** `scanned` + `created`/`updated`/`unchanged`/`deprecated`/`invalid_references`/`failed` replace opaque `edges_upserted`.
6. **Provenance minimum:** projection run, first-seen, last-verified, source artifact/version, review/publish metadata, change reason.
7. **No dual-write** of `products.specifications` until a separate approved migration/import task.
8. **Identity / storage:** Keep `products.id` PKE key; Postgres only; no graph DB.
9. **Implementation sequence:** Prompts **01–14** enumerated in SPEC §12.
10. **Document status:** Proposed — owner review required; **not** Board-Accepted.

---

## Owner-review amendments

**Node:** KB-REMEDIATION-00A-OWNER-REVIEW-AMEND
**SPEC version:** 0.2.0
**Document status after amend:** **Proposed — owner review required** (Board acceptance **not** claimed)

### Decision log (amendments 1–19)

| # | Topic | Decision recorded in SPEC |
|---|-------|---------------------------|
| 1 | Prompt 01 vs 03 | Prompt 01 closes raw `/edges` alone; Prompt 03 adds public PKE DTO; **not** same commit; closing anonymous raw access MUST NOT wait for 03 (§1.2, §3.1, §12). |
| 2 | AuthN/AuthZ | Missing/invalid/expired/revoked → **401**; authenticated non-super-admin (or inactive) → **403**; super-admin allowed (§1.3). |
| 3 | Sync scope | Full catalog **only** `mode=enqueue` + both scopes `null`. Inline both-null → `413 SYNC_SCOPE_TOO_LARGE`. Empty arrays → **`422 EMPTY_SYNC_SCOPE`** (never full catalog; no silent no-op). Mixed: `product_ids=[1], article_ids=null` = product commerce scope only (§3.3). |
| 4 | Status transitions | Normative matrix §2.6: steward publish/reject; P/R demotion; rejected freeze; deprecated revival; steward reopen; reconcile deprecate. |
| 5 | Article demotion | **MUST** demote `published` → `asserted` when article unpublished / future-dated / deleted / target non-public (§2.4.1). |
| 6 | Invalid references | Missing row = invalid; inactive present product = non-public (not invalid); non-int related ids = invalid; duplicates deduped once (§4.2). |
| 7 | Job completion | Terminal set includes **`succeeded_with_errors`** when scope completes with `failed > 0`; `failed` = incomplete / retry exhausted; checkpoint resume documented (§5.3–5.4). |
| 8 | Full-sync concurrency | **Partial unique index** on active full-catalog jobs; scoped overlaps allowed; second full enqueue → `409 PROJECTION_JOB_IN_PROGRESS` (§5.5). |
| 9 | Migration vs Prompt order | M1 code (01–02) → M2 jobs (05) → M4 provenance (08) → M5 events (10) → M6–M8 dictionary/Facts/evidence; explicit reason: jobs before `projection_run_id` (§11.1). |
| 10 | Provenance backfill | Nullable add → deterministic `first_seen_at`/`last_verified_at` from `recorded_at` → legacy `projection_run_id` stays null → NOT NULL only after backfill on those two timestamps; downgrade drops new columns (§11.2). |
| 11 | Event logging | **Mandatory** `knowledge_edge_events` on every status transition by steward / projector / reconcile / status-changing migration; system vs human actors (§7.2). |
| 12 | Provenance naming | Prefer `reviewed_by` / `last_actor` / `last_review_action`; ban ambiguous `actor` / `review_status` that duplicates `edge.status` (§3.4, §7.1). |
| 13 | Public product eligibility | One shared predicate with PDP (`deleted_at IS NULL` + `is_active`); no weaker duplicate filter (§2.5). |
| 14 | Public DTO vs models | All §8 fields map to existing Article/Brand/Category/Product columns; `cover_image` nullable; no invented columns (§8.2). |
| 15 | Index plan | Edge filter, public PKE lookup, job claim, full-sync exclusivity, events `(edge_id, at)` (§11.8). |
| 16 | Performance | Reclassified as **targets/observations**; not merge-blocking until Prompt 14 records hardware/dataset/cache/benchmark (§11.7). |
| 17 | Enums / markdown | Status lists complete: `asserted \| published \| rejected \| deprecated` throughout. |
| 18 | Review API timing | Backend review endpoint = **Prompt 02**; Admin UI = **Prompt 10**; interim API-only stewardship documented (§3.2, §9, §12). |
| 19 | Non-negotiables | Preserved: Postgres only; `products.id` PKE; no JSONB↔Facts dual-write; layering; no auth/publication/audit/integrity weakening (§0.3). |

### Migrations

None applied in this task. SPEC §11 defines future Alembic **A1–A5** (not M*) for later prompts (order corrected in 00A; labels cleaned in 00B).

---

## Final owner-review corrections

**Node:** KB-REMEDIATION-00B-FINAL-CORRECTIONS-REGISTER
**SPEC version:** 0.3.0
**Document status after amend:** **Proposed — owner review required** (Board acceptance **not** claimed)

### Decision log (corrections 1–12)

| # | Topic | Decision |
|---|-------|----------|
| 1 | Review / provenance / events sequencing | Prompt **02** = visibility/gates/demotion/rejected freeze only (**no** steward mutations). Prompt **08** = provenance columns + `knowledge_edge_events` + backend Review API + transition service + tests. Prompt **10** = Admin UI only. |
| 2 | Type-specific transitions | Category/brand: P/R may `asserted→published` iff §2.5; `published→asserted` when product becomes non-public; deprecated may revive to `published` when source+commerce rule pass. Articles: P/R never auto-publish; `asserted→published` steward-only via Review API. |
| 3 | Missing vs non-public | Present unpublished/future/inactive → demote to `asserted`. Missing/deleted source or target → `deprecated` + `invalid_references`. Removed from `related_product_ids` → `deprecated`. Missing MUST NOT remain `asserted`. |
| 4 | Status enums / Markdown | `knowledge_facts.status` = `asserted \| published \| rejected \| deprecated`. Forbidden truncated patterns verified absent. |
| 5 | Job cancellation | Keep `cancelled`. `POST .../jobs/{id}/cancel` super-admin; queued→immediate cancel; running→`cancel_requested_at` then stop at batch boundary; terminals→`409 INVALID_JOB_TRANSITION`. |
| 6 | Job ID type | `knowledge_projection_jobs.id` = UUID PK; `projection_run_id` = nullable UUID FK ON DELETE SET NULL; public DTOs omit; admin may stringify. |
| 7 | `is_full_catalog` | Ordinary Boolean + CHECK (true iff both scope lists null); partial unique index relies on this column. |
| 8 | Migration numbering | Separate **W** waves vs Alembic **A1–A5**; removed code-only “M3” migration row. |
| 9 | Registry | Formal PROPOSED row `SPEC-MASTER-KB-REMEDIATION` (`on_main: false`); not unclassified_allow. |
| 10 | PMO | `tasks.json` is authored Machine SoT — added KB-REMEDIATION-00 / 00A / 00B. CSVs left GENERATED (out of allowlist). |
| 11 | Task report | This section + decision log + validation evidence. |
| 12 | Non-negotiables | Preserved: Postgres only; `products.id` PKE; no JSONB↔Facts dual-write; layering; published public DTOs only; rejected freeze; no auth/publication/audit/integrity weakening. |

### Exact files changed (00B)

1. `docs/architecture/specs/SPEC-master-knowledge-base-remediation.md`
2. `aods/reports/tasks/KB-REMEDIATION-00-ARCHITECTURE-CONTRACT.md`
3. `aods/registry/document-registry.yaml`
4. `project-management/exports/tasks.json`

---

## Test commands / results

### Original Prompt 00 (historical)

### Command 1 — citation gate

```bash
python3 aods/tools/aods_validate.py --gate citation
```

**Actual output (00):**

```text
AODS validation — 1 gate(s), base=origin/main
  SKIP  citation             no --pr-body supplied

RESULT: PASS — 0 new findings, 0 baselined
```

**Exit code:** `0`
**Note:** Gate skips without `--pr-body`; not substantive citation validation.

### Command 2 — docs gate → substituted `links`

```bash
python3 aods/tools/aods_validate.py --gate docs
```

**Exit code:** `2` (unknown gate). Substitution: `--gate links` → PASS, **0 checked**.

---

### KB-REMEDIATION-00A verification (this amend)

#### Command A — links

```bash
python3 aods/tools/aods_validate.py --gate links
```

```text
AODS validation — 1 gate(s), base=origin/main
  PASS  links                249 checked

RESULT: PASS — 0 new findings, 0 baselined
```

**Exit code:** `0` · **Checked:** 249

#### Command B — registry

```bash
python3 aods/tools/aods_validate.py --gate registry
```

```text
AODS validation — 1 gate(s), base=origin/main
  FAIL  registry             249 checked
          - docs/architecture/specs/SPEC-master-knowledge-base-remediation.md: markdown file is neither registered nor covered by unclassified_allow

RESULT: FAIL — 1 new finding(s), 0 baselined
```

**Exit code:** `1` · **Checked:** 249 · **Remaining blocker:** registry row / `unclassified_allow` update is **outside** 00A allowlist (`aods/registry/**` forbidden). Do not treat as fixed.

#### Command C — status + Non-goals + acceptance form

```bash
grep -n "^status:" docs/architecture/specs/SPEC-master-knowledge-base-remediation.md
grep -n "Non-goals" docs/architecture/specs/SPEC-master-knowledge-base-remediation.md
grep -c "Given .*when .*then" docs/architecture/specs/SPEC-master-knowledge-base-remediation.md
git diff --name-only
```

**Actual:** `status: Proposed` (line 4); Non-goals at line 26; Given/when/then count **17** (§13.1 after 00B); allowlisted paths only in 00B diff.

#### Command E — 00B gates

```bash
python3 aods/tools/aods_validate.py --gate links
python3 aods/tools/aods_validate.py --gate registry
python3 aods/tools/aods_validate.py --gate pmo
python3 aods/tools/aods_validate.py --gate naming
```

| Gate | Exit | Checked | Result |
|------|------|---------|--------|
| links | `0` | 249 | PASS |
| registry | `0` | 249 | PASS |
| pmo | `0` | 31 | PASS |
| naming | `0` | 1042 | PASS |

Malformed-status greps: **CLEAN** (no matches).
`git diff --name-only`: four allowlisted paths only.
Citation without `--pr-body` / openapi without fastapi: **SKIP** — not claimed as substantive passes.

## Risks

| Risk | Note |
|------|------|
| Breaking anonymous `/edges` consumers | Intentional security fix; no anonymous grace period; Prompt 01 independent of public DTO |
| Neighborhood asserted-article behavior change | Storefront currently uses blog JSON, not neighborhood API — lower immediate FE risk; tests must be rewritten |
| Owner may reject Proposed publication gates | Article auto-asserted remains; only public exposure tightens |
| Job/worker design not yet coded | Counters/limits are contract-level; Prompt 05–07 may need minor numeric tuning |
| Prompt pack 01–14 bodies not yet in-repo | Sequence defined here; later prompts must align or amend this SPEC via owner review |
| Partial unique index DDL shape | Integrity-protected `is_full_catalog` + CHECK (§5.5.1) |
| PMO GENERATED lag | No official CSV/printable generator in-repo; authored mirrors updated; GENERATED left untouched |

## Discovered-but-not-fixed

1. Unauthenticated `GET /api/v1/knowledge/edges` exposes full provenance — deferred to Prompt 01.
2. Public neighborhood/CRUD treats `asserted` as visible — deferred to Prompt 02.
3. Sync upsert always counts updates as changed; no `unchanged`/`invalid_references`/`failed` — deferred to Prompt 07.
4. Full-catalog sync runs inline in HTTP request — deferred to Prompt 05–06.
5. Storefront knowledge rail ignores knowledge API — deferred to Prompt 09.
6. Admin browser lacks status filters, resolved labels, review actions, history — deferred to Prompt 10.
7. No runtime Facts / property dictionary / evidence / taxonomy assignment tables — deferred to Prompts 11–13.
8. `edges_upserted` alias compatibility vs hard cut — owner may shorten 30-day window.
9. SPEC + task report still branch-local (`feat/master-kb-remediation`); not on `origin/main` until human push/PR (`on_main: false` in registry).
10. GENERATED PMO twins (`printable/`, CSV exports) not regenerated — out of allowlist; regenerate in a separate GOV node if desired.
11. Full PMO markdown mirrors (`KANBAN_BOARD.md`, `CHANGELOG.md`, progress ledgers) not updated — only `exports/tasks.json` was allowlisted.

## Conclusion

**READY FOR OWNER REVIEW** — SPEC **v0.3.0 Proposed**; **not** ACCEPTED. Registry + PMO task rows present. Operator should re-inspect before Prompt 01.

---

## Pre-Prompt-01 readiness — KB-REMEDIATION-00C

**Node:** KB-REMEDIATION-00C-PRE-PROMPT01-READINESS
**Date:** 2026-08-02
**SPEC version:** 0.3.0

### Owner implementation approval decision

| Item | Value |
|------|-------|
| Decision | **Approved for Prompts 01–14** |
| Date | 2026-08-02 |
| Approver | Mohammad Shebahati (repository owner identity from Accepted Board minutes) |
| Architecture Board acceptance | **Not claimed / not granted** |
| Document lifecycle | Remains **Proposed** |
| Canonical authority | **Not Accepted Canon** |
| AODS registry | **PROPOSED** / `proposed` |
| `on_main` | **false** (branch-local until merge) |

### PMO authored-source determination

| Evidence | Finding |
|----------|---------|
| `project-management/README.md` | “Machine SoT: `exports/tasks.json` (update this first, then regenerate markdown if needed)” |
| CR-013 / D15 | CSV + printable are **GENERATED**; must not be hand-patched |
| Conclusion | **`tasks.json` is authored** — edited directly in 00B/00C |

### PMO generator

| Search locations | Result |
|------------------|--------|
| `scripts/**`, `aods/tools/**`, `Makefile`, `package.json`, `pyproject.toml`, `project-management/**` docs | **No official generator script/command** that regenerates `exports/*.csv` or `printable/**` from `tasks.json` |
| Action | GENERATED files **left unchanged** (no invented generator; no manual CSV/printable edits) |
| Blocker class | Non-runtime follow-up — does **not** by itself block Prompt 01 readiness after contract merge |

### Exact files changed (00C)

1. `docs/architecture/specs/SPEC-master-knowledge-base-remediation.md` — owner implementation approval in §14 + frontmatter
2. `aods/reports/tasks/KB-REMEDIATION-00-ARCHITECTURE-CONTRACT.md` — this section
3. `aods/registry/document-registry.yaml` — notes only (still PROPOSED / `on_main=false`)
4. `project-management/exports/tasks.json` — 00B done/100; 00C done/100
5. `project-management/CHANGELOG.md`
6. `project-management/DONE.md`
7. `project-management/progress/KNOWLEDGE_BASE_PROGRESS.md`
8. `project-management/KANBAN_BOARD.md`

### Task status changes

| Task | Status | Progress |
|------|--------|----------|
| KB-REMEDIATION-00B | `done` | 100 |
| KB-REMEDIATION-00C | `done` | 100 |

### Registry truth check

`SPEC-MASTER-KB-REMEDIATION`: `class: PROPOSED`, `status: proposed`, `on_main: false` — unchanged classification; notes updated with owner implementation approval.

### Validation (00C)

| Command | Exit | Checked | Result |
|---------|------|---------|--------|
| `python3 aods/tools/aods_validate.py --gate links` | `0` | 249 | PASS |
| `python3 aods/tools/aods_validate.py --gate registry` | `0` | 249 | PASS |
| `python3 aods/tools/aods_validate.py --gate pmo` | `0` | 32 | PASS |
| `python3 aods/tools/aods_validate.py --gate naming` | `0` | 1042 | PASS |

Skipped (not substantive): citation without `--pr-body`; openapi without fastapi — **not** claimed as passes.

Safety: toplevel `/home/moahmmad/Projects/Karzar`; origin present; branch `feat/master-kb-remediation` (not main); diff paths within allowlist; no `app/`/`tests/`/`frontend/`/`alembic/` changes.

Semantic: SPEC `version: 0.3.0`, `status: Proposed`; owner approval recorded; Board Accept not granted; registry PROPOSED/`on_main=false`; 00B+00C done/100; malformed status greps CLEAN.

### Remaining blockers

1. Contract still branch-local — human commit/PR/merge required before Prompt 01.
2. No in-repo official generator for GENERATED CSV/printable — regenerate when a generator is authored.
3. Prompt 01 implementation not started (intentional).

### Human next steps

1. Review git diff.
2. Commit the governance changes.
3. Push the branch.
4. Open and review the documentation/governance PR.
5. Merge the contract PR into main.
6. Update `on_main` only through the repository’s normal post-merge process.
7. Create a fresh Prompt 01 branch from updated main.
8. Run Prompt 01 in a new Cursor chat.
