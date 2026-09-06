# Karzar — agent floor

1. Code, `openapi/v1.json`, and `alembic/` are evidence of *current implemented state*. Accepted/Binding rows in `docs/architecture/CANON-LOCK.md` are the *requirement*. If they drift, report the conflict and follow Accepted Canon unless a newer Accepted decision supersedes it (`aods/AODS-CHARTER.md` Φ3). Do not invent policy.
2. Halt on missing or conflicting authority. Cite `path:line` that exists on `origin/main`.
3. No production mutation: no push/merge/rebase/deploy unless the human explicitly orders it; no writes to production DB or `https://api.karzartools.com`; no dependency add/remove/upgrade; do not set a document `Accepted`.
4. Never read quarantined hallucination sources: `docs/archive/frontend/AI_CONTEXT.md`, `docs/archive/AI_CONTEXT-2026-07-11.md`, `docs/archive/frontend/BACKEND_NON_COMPLIANCE.md`, `docs/archive/docs/FRONTEND_IMPLEMENTATION_GUIDE.md`.
5. Catalog scripts are Category A local-only (`KARZAR_API_BASE=http://127.0.0.1:8000/api/v1`). Production host requires `KARZAR_ALLOW_PRODUCTION_WRITE=1` **and** `KARZAR_INGESTION_CATEGORY=B` (`scripts/ingestion_boundary.py`). Enrichment never writes price, stock, or availability.
6. Commerce: site `is_available` is binary; warehouse counts are Hesabfa-only; production cannot use mock payment; SEP exists but a live charge is unproven — `docs/COMMERCE.md`.
7. URLs: `/product/{slug}` canonical, `/product/{id}` 301, `/brands/{slug}`, `/categories/{slug}` — ADR-010. Schema: Alembic only. API shape: regenerate `openapi/v1.json` in the same PR.
8. One concern, explicit allowlist, preserve dirty worktree files. Admin work: `frontend/admin-panel/AGENTS.md` (`lint` / `typecheck` / `test` / `build`).
9. CI integrity checks: `python3 aods/tools/aods_validate.py` (`aods/README.md`). Current AODS model is the Board-approved on-demand layer (`AODS-CHARTER.md` current operating model; minute `AODS-BOARD-MINUTE-003`). Do not run archived 1.0.0 prompts/task-graph as live ceremony.
10. Operational status: GitHub Issues/PRs. Checkpoint intent: mid-tail SEO + UX + CWV, not head-term #1 vanity.
