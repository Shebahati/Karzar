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

  Sprint container for the Board wave: `sprints/SPRINT_05.md`. Does **not** reopen checkpoint P0s or lift CAT-002/KB-001 deferral.
