# Decision Log (ADR-lite)

- [x] **D1** Megamenu is merchandising over L1 roots — not a second taxonomy
- [x] **D2** Products attach to leaf depth 2 or 3
- [x] **D3** Specs SoT in specifications JSON; long description editorial only
- [x] **D4** Enrichment never writes price/stock/availability
- [x] **D5** Checkpoint KPI ≠ Google #1 on head terms
- [x] **D6** Owner matrix for P0 / release path (2026-07-30): release owner + rollback owner = **Mohammad Shebahati / محمد شباهتی** (single-operator model S1 accepted; closes AODS `CR-021`). Broader per-task owner matrix remains informal (`CODEOWNERS` `* @Shebahati`).
- [x] **D7** Final call: ship or defer KB-001 at Sprint 03 review — **DEFER** post-31-Shahrivar (EXEC/RELEASE freeze; P2 high effort; not checkpoint KPI)
- [x] **D9** Adopt AODS (`aods/`) as the governing process system — **Accepted** ۸ مرداد ۱۴۰۵ (2026-07-30) by Architecture Board, signed **Mohammad Shebahati / محمد شباهتی**. Minute: `aods/90-governance/BOARD-MINUTE-AODS-ACCEPTANCE.md`. Pack version **1.0.0**. Precedence: runtime truth → Canon → operational policy → developer standards → plans → evidence. Canon Lock row still requires merge of PR #125 (`CR-001`).
- [x] **D8** Checkpoint-close defer governance (2026-07-28): keep **CAT-002** and **KB-001** as deferred backlog (not done); assign owner **PMO**; set revisit date **2026-09-23** for post-checkpoint planning.
- [x] **D10** PMO canonical paths (2026-07-30): `project-management/progress/*_PROGRESS.md` and `project-management/sprints/SPRINT_XX.md` only — closes AODS `CR-007` Option A; root twins deleted.
- [x] **D11** CR-004 residual B+C (2026-07-30): fail-closed `KARZAR_ALLOW_PRODUCTION_WRITE=1` + `KARZAR_INGESTION_CATEGORY=B` via `scripts/ingestion_boundary.py`; `publish_seo003_articles.py` classified Category B deploy publisher.
- [x] **D12** Phase 4 / OI-GOV-05 (2026-07-30): Backend CI job `aods` runs baseline-aware `aods_validate.py` on every PR/`main` push; minute `BOARD-MINUTE-AODS-PHASE4-CI.md`; `CR-012` CLOSED.
- [x] **D13** OI-GOV-02 (2026-07-30): Protect main ruleset requires `lint`+`test`+`aods` (strict) — merge-blocking AODS gates.
- [x] **D14** EPIC-1 ↔ PMO join (2026-07-30): closes AODS `CR-008` **Option C**. Checkpoint PMO stays authoritative for *when/status* of the 31 Shahrivar freeze; Board EPIC-1 stays authoritative for *what* is correct. Mapping (`epic1-ia-readiness.md` → `tasks.json`):

  | EPIC-1 # | Deliverable | PMO task | Status |
  |----------|-------------|----------|--------|
  | 1–2 | PDP `/product/{slug}` + 301 id→slug | **SEO-005** | done (#127) |
  | 3 | Cards / breadcrumbs / sitemap slug | **SEO-006** | done (residual: some account `/product/{id}` links) |
  | 4 | JSON-LD `@id` / BreadcrumbList slug URL | **SEO-007** | done |
  | 5 | Brand Hub `/brands/{slug}` | **SEO-008** | todo (blocked on SPEC / `CR-014`) |
  | 6 | Brand meta for hubs | **BE-002** | done (#126) |
  | 7 | PDF CTA + accessories slot | **FE-002** | todo |
  | 8 | Category Hub `/categories/{slug}` affirm | **SEO-009** | done |

  Sprint container for the Board wave: `sprints/SPRINT_05.md`. Does **not** reopen checkpoint P0s. *(Schedule start-gate for CAT-002/KB-001 later lifted by **D22**; this row remains the EPIC-1 ↔ PMO join.)*
- [x] **D15** CR-013 orphan registration (2026-07-30): register `CONTENT-URL-001` → **FE-003** (#109) and «SEO-001 follow-up» → **SEO-010** (#101) in `exports/tasks.json`; reconcile primary PMO mirrors. Residual: `printable/` wallboard + CSV exports remain **GENERATED** and must be regenerated (not hand-patched).
- [x] **D16** Image-import priority (2026-07-30): closes AODS `CR-019` **Option A**. While **KB-001** remains unimplemented (**D7**/**D8** historical deferral), `docs/CATALOG_IMAGES_PLAN.md` is the authorized product-image import plan; the Knowledge Platform Phase-3 pause is **superseded-for-now** (losing side). Does **not** authorize production imports (ADR-012 / HC-09 still apply). *(**D22** lifts the **2026-09-23** start gate only; this row’s image-plan authority is unchanged until KB-001 is implemented or Board revisits.)*
- [x] **D17** Repo hygiene residual (2026-07-30): closes AODS `CR-017` **Option B** (policy/defer deletes). Hangover in `docs/development/git-development-workflow.md` cites live `git branch -r --no-merged origin/main` and `git worktree list` instead of missing `worktree-cleanup-execution-plan.md`. Residual unmerged remotes / worktree debt remains operator-owned; agents must not unilaterally destroy worktrees or mass-delete branches (§7). Does **not** invent a cleanup execution plan.
- [x] **D18** Bilingual doc pairs (2026-07-30): closes AODS `CR-020` **Option A**. **EN** is normative for contracts / FE–BE gap lists; **FA** is normative for operator-facing deploy guidance; companions carry `translated_from` / `normative_role` and must update in the same PR. Unbuilt site-settings paths remain **proposed / non-Canon** until Backend Architect names one (no path chosen in HC-03). Deploy pair aligned to one-VPS reality (`CR-011`). Does **not** implement any API.
- [x] **D19** Availability semantics (2026-07-30): closes AODS `CR-022` **Option A**. Binding model = binary `is_available` (`README.md`, `docs/HESABFA.md`, `app/crud/product.py`). Corrected `docs/FRONTEND_INTEGRATION.md`; documented legacy stock field/route deprecation in `docs/API_CHANGELOG.md`. Does **not** implement qty&lt;10 `low_stock`. Residual: migrate admin bulk path off `POST .../stock/adjust` (separate IMPL).
- [x] **D20** Transaction ownership BE-01 (2026-07-30): closes AODS `CR-005` **Option A** (incremental). Endpoints own `commit`; services `flush` only. First slice: `submit_checkout` already compliant; `submit_contact` commit hoisted to `storefront_content.contact_us` (`checkout_service` now 0 commits). Residual service commits: otp/cart/product/brand/category/idempotency/hesabfa (separate IMPL; money-adjacent next = cart/otp).
- [x] **D21** Brand Hub SPEC Accepted (2026-07-30): freezes Q1=A (≥1), Q2=A (200+noindex), Q3=B (meta_description only), Q4=B (`/brands` index later), Q5=B (logo optional); sets `brand-hub-page-contract.md` **Accepted**; Canon Lock + registry CANON row; closes AODS `CR-014`. Unlocks **SEO-008** IMPL (separate node). Owner explicitly ordered agent to record Accepted.
- [x] **D22** CAT-002 / KB-001 schedule unblock (2026-07-30): supersedes the **schedule / start-gate** part of **D8** only. Historical **D7**/**D8** checkpoint deferral stands as history (tasks were out of launch-bar scope at close). The mandatory revisit date **2026-09-23** no longer blocks start — **CAT-002** and **KB-001** remain `todo` (owner **PMO**) and are **eligible to start now** (deps CAT-001 / SEO-003 already done). Does **not** implement catalog/KB work; HC-09 / ADR-012 still apply before any staging/prod catalog write. Does **not** change **D16** image-plan authority.
