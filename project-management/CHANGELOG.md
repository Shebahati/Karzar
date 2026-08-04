# PMO / Product Changelog (living)

## 2026-08-04
- [x] **IMG-02B** — Existing Source Paths started (`in_progress` 20%). Deterministic read-only source worklists for Dasqua / INSIZE / SAN OU from IMG-02A-01 inventory + three completed human-review bundles. Work items 1204 (missing 1122 / replace_required 63 / watermark_cleaner 18 / manual_hold 1). Semantic second-run stable. No crawl/download/DB/ProductImage/storage/network mutation. Generated worklists remain external. Live discovery not started.
- [x] **IMG-02A-02-REMAINDER-ALL** — Post-merge PMO sync **merged** in PR #208 @ `681e9ff7231ab6e2ebb2a4ad29ce410cb4c2eee3`. Task closed done/100 after PR #207 implementation merge.
- [x] **IMG-02A-02-REMAINDER-ALL** — All-remaining package + human review **merged** in PR #207 @ `5ea3f54edb2dcf83f374ea34bec9073973ce8f2f`. Explicit all-remaining selection mode merged; 414 remainder Assets packaged and reviewed; 516 remainder Assignments reviewed; zero overlap with prior review packages; zero remaining validated local Assets; 614 / 614 cumulative unique Assets reviewed; 1193 / 1193 cumulative Assignments reviewed; 75 Remainder-All ShopMill-watermarked Assets; 30 Remainder-All replacement-required Assignments; 88 cumulative replacement-required Assignments queued; 2 cumulative manual-review Assignments queued; rights cleared = 0; raw package and human-review evidence external; zero database/ProductImage/storage/network mutations; replacement execution not started.
- [x] **IMG-02A-02-REMAINDER-ALL** — (historical pre-merge) Human review integrated into PR #207 (`in_progress` 90%; Ready for Review after CI). External human-review ZIP `9e40733a…` validated against package `48d3466d…`: 414/414 Assets, 516/516 Assignments; ShopMill-watermarked Assets 75; REPLACE_REQUIRED Assignments 30; MANUAL_REVIEW 0; rights all `review_required`. Cumulative coverage 614/614 Assets and 1193/1193 Assignments; cumulative REPLACE_REQUIRED 88; cumulative MANUAL_REVIEW 2; remaining Assets 0. No decisions/replacements applied; zero DB/ProductImage/storage/network mutations; raw review evidence remains outside Git.
- [x] **IMG-02A-02-REMAINDER-ALL** — (historical packaging / pre-merge) All-remaining package generated externally (`in_progress` 70%). Added explicit `--all-remaining` selection mode (mutually exclusive with quotas), deterministic full selection ordering, offline review UI pagination/search/navigation for 414 assets, and prior-batch evidence path sanitization. Authoritative outputs: source assets 614; excluded prior assets 200; selected assets 414; assignment rows 516; remaining assets 0; prior overlap 0; shared/singleton 88/326; previews/thumbs 414/414; semantic second-run stability true; ZIP `48d3466d…` (62309721 bytes). Human review was pending at packaging time.


## 2026-08-03
- [x] **IMG-02A-02-BATCH-002** — Sequential Batch 002 **merged** in PR #205 @ `1f391c0a3591c09888d12fbd5ec6d4ef8085de82`. Sequential exclusion tooling merged; 100 new unique Assets / 212 assignments; zero Pilot overlap; Batch 002 human review completed externally; 36 visible ShopMill-watermarked Assets; 17 replacement-required assignments; 1 manual-review assignment; schema batch identity corrected; corrected package verified; no raw evidence committed; zero DB/ProductImage/storage/network mutations; replacement execution not started; 414 unique Assets remain.
- [x] **IMG-02A-02-BATCH-002** — (historical pre-merge) Sequential Batch 002 packaging + human review (`in_progress` 90%, PR #205 open). Human review validated: 100 assets / 212 assignments; watermark 36 distributor; REPLACE_REQUIRED 17; MANUAL_REVIEW 1; rights all `review_required`. Schema `batch_id_default` corrected for sequential batches. Corrected ZIP `6d15fc26…` (old `1112f104…`); selection/preview/thumb stable; decisions not applied; zero DB/ProductImage/storage/network mutations; raw evidence external.
- [x] **IMG-02A-02-BATCH-002** — (historical pre-review) Sequential Batch 002 packaging (`in_progress` 70%). Generalizes Pilot tooling with prior-batch exclusions; Batch 002: 100 new unique assets / 212 assignments; excluded 100 Pilot assets; eligible 514 → remaining 414; overlap 0; ZIP `1112f104…`; human review pending; no replacement execution; zero DB/ProductImage/storage/network mutations; raw outputs external.
- [x] **IMG-02A-02** — Existing image human-review batches + Pilot 001 **merged** in PR #203 @ `023047b8cd0c82b48428f0c5037121e9f0471b24`. Deterministic offline review tooling merged. Pilot 001: 100 unique assets / 465 assignments; human review completed externally; 52 ShopMill watermark assets; 41 replacement-required assignments; 1 manual-review assignment; corrected offline Pilot ZIP verified; no raw review evidence committed; zero DB/ProductImage/storage/network mutations; replacement execution not started.
- [x] **IMG-02A-02** — (historical pre-merge) Human review complete externally while PR #203 open (`in_progress` 90%): 100 assets / 465 assignments; 52 ShopMill watermarks; 41 REPLACE_REQUIRED; rights all `review_required`. Offline `review.html` URL/path contract closed. No DB/ProductImage/storage mutation; replacement not started; raw review evidence not committed.
- [x] **IMG-02A-01 / IMG-02A-01-R1** — Canonical existing image inventory **merged** in PR #201 @ `58401eb28fe346d2f00a0679d90c6763a5000250`. Authoritative PostgreSQL read-only run completed (`karzar_staging`, `transaction_read_only=on`): 5918 products; 1194 ProductImage rows; 1193 valid local images; 1 remote-unverified; 0 missing/decode failures; 188 exact cross-product duplicate groups; 0 cross-brand duplicate groups; 0 unreferenced files; **zero mutations**. Raw outputs external (not in Git). Read-only audit only; no watermark/suitability classification.
- [x] **IMG-02A-01** — (historical pre-merge) Authoritative read-only inventory complete on VPS; aggregates in task report; raw outputs external. PR #201 Ready for Review → later merged.
- [x] **IMG-02A-01-R1** — (historical) Pre-authoritative boundary hardening (43 tests). Branch `feat/existing-image-audit`.
- [x] **IMG-01 → IMG-01E-R1** — Governed multi-brand image discovery pipeline **merged** in PR #198 @ `f10cfff3ace2a00ef3a7403d5408e79e0b9b395b` (implementation head `fe227b4`). Final local suite **110 passed**; offline 100-SKU asset/state regression passed. **No** database/ProductImage apply; **not** production-approved; live TOSAG parser validation **pending**.
- [x] **IMG-01E-R1** — Resume identity contract (`validate_source_manifest_row`); merged via PR #198.
- [x] **IMG-01E** — Four hardening items; merged via PR #198.
- [x] **IMG-01 → IMG-01D** — Pipeline chain merged via PR #198 @ `f10cfff`.

## 2026-08-02
- [x] **IMG-01D** — Close five final image-pipeline blockers (structural parser / allow-replace / manifest contract / no-follow / duplicate physical). Branch `feat/image-discovery-pipeline` (historical). Later merged in PR #198 @ `f10cfff`.
- [x] **IMG-01C** — Final targeted image-pipeline corrections (path/integrity/dedupe/URL safety). Branch `feat/image-discovery-pipeline` (historical). Later merged in PR #198 @ `f10cfff`.
- [x] **IMG-01B** — Close image-pipeline human-review blockers (identity/FS/provenance/consolidation/run-state/transport). Branch `feat/image-discovery-pipeline` (historical). Later merged in PR #198 @ `f10cfff`.
- [x] **IMG-01A** — Generic multi-brand image-discovery engine + `insize_tosag` adapter (refactor before first commit). Branch `feat/image-discovery-pipeline`. External pilot preserved. Later merged in PR #198 @ `f10cfff`.
- [x] **IMG-01** — INSIZE image discovery + 100-SKU external pilot (candidate validation). Registered CR-008 C; implementation reshaped by IMG-01A.
- [x] **KB-REMEDIATION-11A** — Property Dictionary runtime (A3): `knowledge_units` + `knowledge_property_definitions` + `knowledge_property_aliases`; migration `f7a8b9c0d1e2`; CLI import; super-admin GET. No templates/Facts/dual-write. Branch `feat/kb-remediation-11a-property-dictionary` (awaiting human commit/PR; HC-08 before apply).
- [x] **KB-PT-01A** — Close PT-W1 integrity gaps: `passive_deletes="all"`; loaded-collection deletion regression; populated pre-migration Product+JSONB evidence (up/down/up). Same branch `feat/kb-pt-01-runtime-core`.
- [x] **KB-PT-01** — PT-W1 Product Type runtime core: `product_types` + nullable `products.product_type_id` (RESTRICT/NO ACTION). Migration `e6f7a8b9c0d1`. No seed/backfill/API/Definition. Branch `feat/kb-pt-01-runtime-core` (awaiting human commit/PR).
- [x] **KB-PT-00B** — Architecture Board **Option A** Accept Hybrid Product Type clarification (`AB-ADR-015-2026-08-02`). Minute Accepted; ADR-015 → Accepted Canon; taxonomy §7.1; Canon Lock §1d; Master KB KB-PT-01 unblocked after merge. Signed Mohammad Shebahati.
- [x] **KB-PT-00A** — Final owner-review corrections to Canonical Product Type contract (SPEC v0.1.1, ADR-015 Proposed amendment, Master KB v0.4.1): 11A→PT-W2 sequencing; Board clarification mandatory before KB-PT-01; PT-W1 no readout/seed/backfill. Lifecycle **Proposed**; Board Accept **not** granted; runtime still blocked. GENERATED CSV/printable untouched.
- [x] **KB-PT-00** — Canonical Product Type architecture contract: `SPEC-canonical-product-type-model` v0.1.0→v0.1.1 + Proposed **ADR-015** (Hybrid FK) + Master KB remediation **v0.4.0→v0.4.1**. Lifecycle **Proposed**; Board Accept **not** granted; no runtime changes. Branch `docs/kb-pt-00-canonical-product-type-contract`. GENERATED CSV/printable untouched (no in-repo generator).
- [x] **KB-REMEDIATION-00C** — Owner implementation approval for `SPEC-master-knowledge-base-remediation` **v0.3.0** (Prompts 01–14). Lifecycle remains **Proposed**; Architecture Board acceptance **not** granted; registry **PROPOSED** / `on_main=false`. Closed 00B (done/100). Authored `tasks.json` updated. GENERATED CSV/printable left untouched — no official in-repo generator (documented follow-up). Prompt 01 must wait for human commit/PR/merge then a fresh branch from `main`.
- [x] **KB-REMEDIATION-00B** — Final SPEC contradictions resolved; registry row `SPEC-MASTER-KB-REMEDIATION`; PMO task rows 00/00A/00B.
- [x] **KB-REMEDIATION-00A / 00** — Remediation architecture contract authored and owner-review-amended on `feat/master-kb-remediation` (branch-local until PR).

## 2026-08-01
- [x] **Wave A short_desc 0/01 fix (43 INSIZE cat57)** — live Category B rewrite of stale `short_description`/`meta_description`; enricher detects corrupt slash-decimals in marketing text. Verify 0 remaining. PR #190.
- [x] **FE storefront redesign merged (#187)** — L1 category icons + hero dock + OTP length 6; aods unblock via #188 (`on_main` for FE collaborator docs). **Deploy Staging** still needs Owner/FE Actions click (agent 403). No Production.
- [x] **Frontend collaborator gates (self-merge)** — charter + handoff paste for `@mhrbzandi-Designer`; Collaborator Scope Gate (allowlist + lockfile freeze); Owner checklist = Write + **0 approvals** + Code Owners review **Off** + required CI checks; no Owner PR review. Agent cannot invite/protect via API.
- [x] **KB-001 operator residual CLOSED (agent Category A, full catalog)** — seed 1064 products from `all_products.csv` + `projections/sync` → **2132** knowledge edges (1065 category + 1065 brand + 2 article). Report: `aods/reports/tasks/GOV-2026-08-01-operator-kb001-local-sync.md`.
- [x] **Day-5 Admin read-only Knowledge views** — admin `/knowledge` edges browser + product-edit neighborhood card (KB-001 three freeze edges). Mock support. No Facts/publish/dual-write.
- [x] **Day-5 Classification map INSIZE v0** — Git `MAPPING-TABLE` `docs/architecture/specs/seeds/classification-map-insize-v0-metrology.json` (brand_id=3 → taxonomy v0 closed labels). Offline sample coverage. No Facts / no `PRODUCT_CLASSIFIED_AS` projector. Readiness §5 complete for one-brand maps.

## 2026-07-30
- [x] **Day-4 Taxonomy v0 (metrology)** — Git seed `docs/architecture/specs/seeds/taxonomy-v0-metrology.json` (Measurement domain/families/types + apps + L1 bridge 56/81/87). No second Category DAG; hubs not indexable (UD-04).
- [x] **Day-4 Property Dictionary v0 (metrology)** — Git-first seed `docs/architecture/specs/seeds/property-dictionary-v0-metrology.json` (definitions + caliper template + legacy aliases). UD-03 A. No Facts/dual-write.
- [x] **KB-001 Day-3 CLOSED** — wave-1 AC done (#176); offline sync proof PASS; operator local Alembic residual documented in seeds README / day3-close.
- [x] **KB-001 wave-1 IMPL (Day-3)** — `knowledge_edges` overlay (ADR-013) + projector from SoR soft-links + `GET /api/v1/knowledge/edges` + product neighborhood + admin `POST .../projections/sync`. Freeze: three edge types only. Tests + OpenAPI snapshot. Progress 45%→70% (`in_progress`).
- [x] **Day-2 Board Accept — Knowledge Foundation** (2026-08-01 / ۱۴۰۵/۰۵/۱۰) — UD-06 A core SPEC pack + ADR-013 (Postgres edges/Facts) + ADR-014 (`products.id` PKE) Accepted into Canon Lock §1c; UD-03 metrology-first; UD-08 no AI FA auto-publish; OI-KF-04 Phase1–3 HISTORICAL; KB-001 freeze three projection edges. Minute: `aods/90-governance/BOARD-MINUTE-KNOWLEDGE-FOUNDATION-ACCEPT-2026-08-01.md`. KB-001 progress 35%→45%. No code/migrations.
- [x] **Day-1 practical week CLOSED** — Topic 1 merge (#168) · Topic 2 agenda+ballot vote A (#172/#173) · Owner order Day-2 now.
- [x] **KB-001 architecture completion pack (Proposed)** — audit, foundation review, domain model, property dictionary, taxonomy master seed, KG registry, data transformation, target architecture, implementation readiness under `docs/architecture/specs/`. No code/migrations. Extends foundation SPECs; Board Accept still open (UD-06).
- [x] **KB-001 foundation SPECs (Proposed)** — landed `docs/architecture/specs/` pack: Product Knowledge Entity, Industrial Taxonomy, Knowledge Graph, Import & Enrichment Playbook + pack README (analysis, decisions, UD list, sequence). No code/migrations. Not Canon Lock until Board Accept (UD-06). KB-001 progress 10%→20%.
- [x] **CAT-002 local Category A apply** — repaired `lathe_api` (wrong Website/backend bind-mount + SCRAM password mismatch); `curl /ready` OK; dry-run then `--apply --apply-confirm` on `http://127.0.0.1:8000/api/v1`: **applied=126 err=0**; already_complete=735; unmatched=5; `zero_price_writes=true`. No staging/prod; AC ≥200 SKU QA still open. Task → `in_progress` 75%.
- [x] **CAT-002 transition fill (Strategy C-as-A) — dry-run partial** — KNOW node offline dry-run PASS (`scripts/enrich_insize_from_shopmill.py --reuse-crawl --reuse-export`): 867 crawl / 861 matched payloads; `zero_price_writes=true`; country≠material. Artifacts + provenance under `data/imports/insize/shopmill/`. **Apply HALTED** (local `127.0.0.1:8000` down — `lathe_api` crash-loop). No staging/prod; no HC-09. Task → `in_progress` 40%. AC ≥200 SKU QA still open.
- [x] **CAT-002 / KB-001 schedule unblock** — lifted mandatory revisit/start gate **2026-09-23** (**D22** supersedes D8 schedule part only; D7/D8 kept as history). Both remain `todo` (15% / 10%) and are **eligible to start now** (deps CAT-001 / SEO-003 done). Residual mirrors aligned: `DECISIONS.md`, `RELEASE_PLAN.md`, `KANBAN_BOARD.md`, `README.md`, export CSVs, operator skill §7. No catalog/KB implementation. D16 image-plan authority unchanged.
- [x] **FE-002 done** — PDP PDF catalog CTA (after trust strip) + always-visible accessories slot with honest empty / label / product-card states.
- [x] **SEO-008 done** — Brand Hub sitemap (`/brands/{slug}` for product_count≥1) + homepage brand-strip links to hubs; `/brands` index still deferred (Q4=B).
- [x] **SEO-008 IMPL (route)** — Storefront `/brands/[slug]` Brand Hub per Accepted contract (D21); PDP brand link prefers hub URL; sitemap/nav residual.
- [x] **CR-014 CLOSED** — Brand Hub page contract **Accepted** (Q1–Q5 = D21); Canon Lock + registry; SEO-008 IMPL unblocked (separate node).
- [x] **CR-005 CLOSED (Option A)** — BE-01 incremental: checkout_service cleared (`submit_contact` → endpoint commit); **D20**. Residual: otp/cart/product/brand/category/idempotency/hesabfa.
- [x] **CR-022 CLOSED (Option A)** — `FRONTEND_INTEGRATION.md` + `API_CHANGELOG.md` aligned to binary `is_available`; legacy stock fields deprecated in changelog; **D19**. Admin bulk migrate = follow-up IMPL.
- [x] **CR-020 CLOSED (Option A)** — Bilingual policy: EN contracts / FA operator deploy; `translated_from`/`normative_role`; settings paths proposed/non-Canon; deploy one-VPS (`CR-011`); **D18**.
- [x] **CR-017 CLOSED (Option B)** — Policy/defer deletes; hangover refreshed to cite live `git branch -r --no-merged` / `git worktree list`; residual branch/worktree debt acknowledged; **D17** recorded. No mass deletes / worktree remove in this node.
- [x] **CR-019 CLOSED (Option A)** — `CATALOG_IMAGES_PLAN.md` remains authorized image-import plan; Phase-3 pause annotated superseded-for-now (losing side) via **D7**/**D8**; **D16** recorded. No import run in this node.
- [x] **CR-013 CLOSED** — Registered orphans as **FE-003** (was CONTENT-URL-001, #109) and **SEO-010** (was SEO-001 follow-up, #101); reconciled primary PMO mirrors; milestones M0–M4 → done; MASTER_ROADMAP O3–O6 checked; README hours from tasks.json (~82% weighted); SEC-001 KANBAN/DONE honesty. Residual: GENERATED wallboard/printable/CSV — regenerate, do not hand-patch.
- [x] **CR-006 CLOSED (Option B)** — Scorecard demoted `HISTORICAL`; live quality bar = v2 master audit + `REMEDIATION-TO-9`; CONTRIBUTING updated; Option A (v3 audit) deferred.
- [x] **CR-016 CLOSED (Option A)** — Pytest SoT = `pyproject.toml` only; deleted duplicate `pytest.ini` after carrying `python_classes`/`python_functions`.
- [x] **CR-018 CLOSED** — Added `.github/pull_request_template.md` from Accepted `pr-checklist.md` + citation minima; TECH_DEBT cleared.
- [x] **CR-014 SPEC (Proposed)** — Brand Hub page contract drafted at `docs/architecture/information-architecture/brand-hub-page-contract.md`; Q1–Q5 await HC-01; SEO-008 still blocked for IMPL.
- [x] **CR-008 CLOSED (Option C)** — EPIC-1 ↔ PMO mapping (**D14**); tasks `SEO-005`…`SEO-009`, `BE-002`, `FE-002`; Sprint 05 Board wave; checkpoint deferrals unchanged.
- [x] **CR-002 CLOSED (Option A)** — Canon `feature/*` wins; CONTRIBUTING + COLLABORATOR_DEPLOY aligned; `feat/*` grandfathered (no mass-rename); `cursor/*` carve-out documented.
- [x] **CR-003 CLOSED (Option A)** — Coverage prose aligned to enforced **68%** (`pyproject.toml` + `backend-ci.yml` SoT); `README.md` / `docs/TESTING.md` / `docs/API_CHANGELOG.md` + TECH_DEBT updated.
- [x] **CR-023 CLOSED** — Fixed broken doc links (`BACKEND_CHANGES` relatives + Bible/IA/architecture README not-in-repo prune); `--gate links` clean; links baseline emptied.
- [x] **CR-010 CLOSED** — ADR/RFC indexes list only in-repo Accepted files; reserved IDs not linked; baseline shrunk; residual Bible/IA/arch README dangling links reassigned to `CR-023`.
- [x] **CR-009 CLOSED (Option B)** — Binding SoR = this Git repo only; Canon Lock / git workflow / PROMOTION-WAVE1 no longer treat `Website/docs/` as Authoring SoR; missing Binding rows removed; `CR-010` closed separately (index prune).
- [x] **CR-011 CLOSED (Option B)** — `deploy-staging.yml` no longer runs on push to `main`; `workflow_dispatch` only; `COLLABORATOR_DEPLOY.md` updated; same-VPS residual tracked until Option A.
- [x] **CR-021 CLOSED** — Release + rollback owner = Mohammad Shebahati / محمد شباهتی (single-operator S1); `RELEASE_PLAN.md` §0; D6 checked; BLOCKERS/DEPENDENCIES/EXECUTIVE_SUMMARY aligned.
- [x] **Cursor rule** Added always-on `aods-kickoff-gate.mdc` — fill AODS NODE KICKOFF, wait for human confirm, then execute (survives chat context compaction); no PMO task ID (CR-008).
- [x] **OI-GOV-02 CLOSED** — Protect main requires `lint`+`test`+`aods` (verified 2026-07-30).
- [x] **OI-GOV-02 apply path** — script `scripts/ops_require_aods_status_check.sh` ready; Protect main currently requires `lint`+`test` only; `aods` pending repo-admin apply (agent token HTTP 403).
- [x] **CR-004 residual B+C CLOSED** — `scripts/ingestion_boundary.py` fail-closed guard; deploy-staging sets Category B env for `publish_seo003_articles.py`; policy/SCRIPTS docs updated.
- [x] **Phase 4 / OI-GOV-05** — Backend CI job `aods` runs `aods_validate.py` (incl. openapi); `CR-012` CLOSED; minute `BOARD-MINUTE-AODS-PHASE4-CI.md`.
- [x] **CR-015 CLOSED** — quarantined `frontend/AI_CONTEXT.md` (Option A: stub + archive under `docs/archive/`).
- [x] **CR-007 CLOSED** — Option A: `progress/` + `sprints/` canonical; deleted 19 root twin files; living-PMO rule + GOV prompt updated.
- [x] **CR-004 CLOSED** — 18 scripts default to local API/asset base (ADR-012 Option A); `--gate ingestion-boundary` PASS; residual fail-closed/Category-B classify tracked as tech debt.
- [x] **CR-001 CLOSED** — Canon Lock on `main` via #125; registry `on_main` reconciled (53 docs); baseline CR-001 link findings removed.
- [x] **CR-012** Regenerated `openapi/v1.json` (81→82 paths; adds `/api/v1/products/slug/{slug}`); `--gate openapi` PASS; baseline entry removed; CI wiring still Phase-4.
- [x] **Skill** Added Cursor skill `karzar-aods-operator` (`.cursor/skills/karzar-aods-operator/SKILL.md`) — operating pack for Accepted AODS 1.0.0 + Canon Lock on main; refreshed `aods-auto-mode.mdc` CR-001 citation note.
- [x] **D9 / HC-14** Architecture Board **Accepted AODS in full** — ۸ مرداد ۱۴۰۵; signed **Mohammad Shebahati / محمد شباهتی**. Minute: `aods/90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md`. Pack headers + registry → **Accepted / 1.0.0**.
- [x] **AODS-001 → `done`** — PR [#128](https://github.com/Shebahati/Karzar/pull/128). Remaining: merge #125 (Canon Lock row / `CR-001`), then #128 to `main`.

## 2026-07-29
- [x] **AODS-001** AI-Orchestrated Development System designed and delivered under `aods/` — 19 required sections, 23 documents, 11 instantiated prompts, 3 machine-readable registries, and stdlib-only runnable validators. Initially shipped as **Proposed**; Board acceptance recorded 2026-07-30 (see above). Process-only: no application behaviour changed.
- [x] **Validation gates now exist and run** — `python3 aods/tools/aods_validate.py` (8 automatic gates: registry, links, pmo, prompts, graph, naming, openapi, ingestion-boundary; 2 contextual: citation, allowlist). Previously the repository had no validator of any kind.
- [x] **23 governance conflicts registered** in `aods/10-repository-intelligence/CONFLICT-REGISTER.md`, none silently resolved. 5 are BLOCKERs and are now mirrored in `BLOCKERS.md`; the rest feed `RISKS.md` (R9–R11) and `TECH_DEBT.md`.
- [x] **Three conflicts independently confirmed by tooling rather than by reading:** `CR-004` (18 scripts default to the production API, violating Accepted ADR-012), `CR-007` (6 divergent PMO ledger pairs), and `CR-012` — `openapi/v1.json` is missing `/api/v1/products/slug/{slug}`, live since #126 while the snapshot was last regenerated in #111. Two EPIC-1 PRs merged against a stale machine contract with nothing reporting it.
- [x] **`CR-023` opened** — two root-relative links in `docs/BACKEND_CHANGES.md` do not resolve; surfaced because the baseline writer refuses to record an unattributed suppression.
- [x] **31 findings baselined** as visible, owned, dated debt in `aods/registry/validation-baseline.json`. The file may only shrink without approval.
- [x] **Two Cursor rules added** — `aods-auto-mode.mdc` (always-on safety floor: forbidden context, no push/merge/deploy, cite-don't-infer, halt instead of guess) and `aods-node-execution.mdc` (rules for editing AODS itself). `pmo-living-system.mdc` left untouched.
- [x] **Independent accuracy pass on the pack itself** — every numeric and line-number claim re-verified against the repository. Corrected: 55→41 scripts, 58→62 unmerged branches, 78→79 PMO files, ~150→~140 markdown documents, two wrong line citations inside the `RESTATE` example, a gate name (`--gate ingestion`) that did not exist, and a missing prompt-lint rule. Logged in `aods/10-repository-intelligence/REPOSITORY-AUDIT.md` §10 rather than fixed silently.
- [x] **`D9` opened in `DECISIONS.md`** — adopting AODS is a Board decision, not an agent decision.

## 2026-07-28
- [x] **PMO close pass** validated checkpoint-final PMO state against current SoT: only CAT-002 and KB-001 remain open and intentionally deferred
- [x] **Deferred governance hardened** for CAT-002/KB-001 across `tasks.json`, `PROJECT_STATUS.md`, `RELEASE_PLAN.md`, `DECISIONS.md`, `KANBAN_BOARD.md`, `BACKEND_PROGRESS.md`, and `KNOWLEDGE_BASE_PROGRESS.md` with explicit owner `PMO` + revisit date `2026-09-23`
- [x] **Portfolio status corrected** weighted progress updated to 85% (hours-weighted from `exports/tasks.json` progress values)

## 2026-07-27
- [x] **FE-001 follow-up** Separate page footer padding from section tokens — #117 → `main` @174718f (Deploy Staging 30282336447)
- [x] **FE-001** Design system tokens + homepage consistency — #115 → `main` @daa8abd; shared section spacing/type tokens + home-stack; steel/red (closes remaining after #93)
- [x] **TD-001** Pay down category depth/selectable FE drift — #114 → `main` @8cd01bd; depth 2|3 helpers + docs; no depth===3-only filters
- [x] **UX-001** PLP filter + hub IA polish — #113 → `main` @f4ec40b; mobile quick chips ≤3 taps; Persian empty states; hub child nav
- [x] **CAT-003** L1 category image coverage — #112 → `main` @fb7d628; helicoil roots 186–188 curated assets + seed URLs; all live L1 mapped
- [x] **BE-001** Catalog API SEO fields readiness — regenerated `openapi/v1.json` (short_description/meta_*/slug); contract tests green
- [x] **CAT-001** Close enrichment PR triage — #67 phase-A image docs → `main` @f51c9fd; #69 Dohre tooling → `main` @0829571 (Deploy Staging 30274744553); #70–#73 prior; #74 closed; **#90 INSIZE deferred with CAT-002**
- [x] **CAT-002** / **KB-001** explicitly deferred (post-31-Shahrivar / launch-bar) per RELEASE_PLAN + EXECUTIVE_SUMMARY; D7 recorded
- [x] **SEC-001** Security hygiene pass for go-live bar — admin `X-Robots-Tag` + layout noindex; secrets hygiene script green; FE key-material scan 0 hits; step-up PIN coverage inventoried; Pillow→12.3.0; residual ecdsa/Next advisories → RISKS R8
- [x] **REL-001** Release readiness for 31 Shahrivar checkpoint — scope freeze documented (P0 completed/deferred), explicit go/no-go gates, rollback plan, launch-window verification checklist, and residual risk ownership added across PMO artifacts.
- [x] **SEO-003** Publish 24 buyer-intent articles (calendar A01–D06) — #102 → `main` @aa159b0; publish fixes #103/#104; Deploy Staging green (30255672560); CMS `ok=24`; verified `/blog/digital-caliper-workshop-accuracy`
- [x] **SEO-010** Store LocalBusiness geo + official Google Maps place on contact/footer/JSON-LD — #101 → `main` @1e8cd9b (was «SEO-001 follow-up»; registered CR-013)
- [x] **PERF-001** Core Web Vitals foundations (fonts/LCP/image pipeline) — #99 → `main` @d169831; Deploy Staging green (30251144532)
- [x] **UX-002** PDP trust strip + specs SoT presentation — #96 → `main` @e8ea7bf; Deploy Staging green; verified `/product/2000` (trust+RTL specs) + `/product/7115` (trust+JSON-LD)
- [x] **OPS-001** Measurement promote workflow marked done in PMO — #81 → `main` @e1981b6 (merged 2026-07-26; Kanban sync)
- [x] **SEO-004** Technical crawl hygiene — #94 → `main` @a119b38; Deploy Staging green; robots/sitemap/SITE_URL; empty-hub 404; facet+private noindex; sitemap 6007 urls
- [x] **PMO-001** Living PMO bootstrap marked done (in active use since #86)
- [x] **FE-001** (partial) Floating transparent home header over full-bleed hero — #93 → `main` @53f0100; Deploy Staging green
- [x] Taxonomy «عمومی» padding leaves — #87 apply on staging: **23 categories deleted / 1970 products** remapped to L2 parents

## 2026-07-26
- [x] **SEO-002** Category hub intros + internal links (15 metrology/cutting hubs) — #91 → `main` @d92722a; Deploy Staging green; verified `/categories/انواع-کولیس`
- [x] **SEO-001** Storefront JSON-LD: Product + gated Offer + Breadcrumb (PDP); CollectionPage/ItemList (category hubs); Organization + WebSite + SearchAction (layout) — #88 → `main` @89a4cf5; Deploy Staging green; verified `/product/7115`
- [x] Merged to `main`: Measurement promote CI (#81); SAN OU (#73), Mitutoyo leaflets (#72), Dasqua 2025 (#71), Chumpower (#70) enrichment; Hesabfa stock clear asyncpg (#56); CI lint/test unlock for frontend-only PRs (#26); Living PMO (#86)
- [x] Staging deployed for the enrichment PRs above (#70–#73)
- [x] Skipped (not merged): phase-A images continue (#67, open), Dohre enrichment (#69, open), Insize 108A (#74, closed) — **superseded 2026-07-27:** #67/#69 merged; #90 deferred w/ CAT-002
- [x] Created living PMO under `project-management/`
- [x] Seeded tasks.json + import CSVs
- [x] Documented 31 Shahrivar realism assessment

## Prior (repo history — selected)
- [x] Homepage megamenu hero / categories / why-karzar waves
- [x] Metrology taxonomy promote + admin megamenu display flags
- [x] SEO short_description plumbing (#66/#68)
