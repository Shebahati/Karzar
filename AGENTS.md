# Karzar — agent floor

1. Runtime truth wins: code, `openapi/v1.json`, `alembic/`. Then Accepted rows in `docs/architecture/CANON-LOCK.md`. Then `docs/OPERATIONS.md` / `docs/architecture/data-ingestion-policy.md`. PMO/GitHub status is schedule only. Evidence under `docs/archive/` is not current guidance.
2. Do not invent product policy. Halt on missing, ambiguous, or conflicting authority. Cite `path:line` that exists on `origin/main`.
3. No production mutation: no push/merge/rebase/deploy unless the human explicitly orders it; no writes to production DB or `https://api.karzartools.com`; no dependency add/remove/upgrade; do not set a document `Accepted`.
4. Never read quarantined hallucination sources: `frontend/AI_CONTEXT.md`, `docs/archive/AI_CONTEXT-2026-07-11.md`, `frontend/BACKEND_NON_COMPLIANCE.md`, `docs/FRONTEND_IMPLEMENTATION_GUIDE.md` (and their archive copies).
5. Catalog scripts are Category A local-only (`KARZAR_API_BASE=http://127.0.0.1:8000/api/v1`). Production host requires `KARZAR_ALLOW_PRODUCTION_WRITE=1` **and** `KARZAR_INGESTION_CATEGORY=B` (`scripts/ingestion_boundary.py`). Enrichment never writes price, stock, or availability.
6. Commerce: site `is_available` is binary; warehouse counts are Hesabfa-only; production cannot use mock payment; SEP exists but a live charge is unproven — `docs/COMMERCE.md`.
7. URLs: `/product/{slug}` canonical, `/product/{id}` 301, `/brands/{slug}`, `/categories/{slug}` — ADR-010. Schema: Alembic only. API shape: regenerate `openapi/v1.json` in the same PR.
8. One concern, explicit allowlist, preserve dirty worktree files. Admin work: `frontend/admin-panel/AGENTS.md` (`lint` / `typecheck` / `test` / `build`).
9. On-demand checks: `python3 aods/tools/aods_validate.py` — see `aods/README.md`. Do not preload the AODS corpus.
10. Work status lives in GitHub Issues/PRs. Checkpoint intent: mid-tail SEO + UX + CWV, not head-term #1 vanity.
