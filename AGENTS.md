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

## Execution discipline

11. GitHub Issue/PR state is canonical. Before implementation: `git fetch origin`, attest current `origin/main`, issue scope, linked dependencies, branch/head, and worktree cleanliness. Prompt SHAs are hints until re-attested.
12. One Issue = one execution scope. Do not silently widen scope, combine unrelated cleanup, or consume adjacent backlog. If target main moves materially, report `TARGET_MOVED` and re-evaluate before merge/rebase.
13. Use the cheapest adequate model first. Routine exploration, grep, docs, test scaffolding, simple fixes, and evidence formatting stay on Cursor/cheap models. Escalate to frontier reasoning only for ambiguous root cause, auth/payment/security, concurrency/transactions, or critical review.
14. Keep exploration bounded. Prefer issue → relevant docs/tests → targeted search → implementation. If evidence is still insufficient after focused inspection, stop with `BLOCKED_BY_MISSING_EVIDENCE` instead of broad repository wandering.
15. One Issue = one Cursor conversation where practical. Do not carry unrelated historical chat context forward; reload truth from GitHub, repo, tests, and accepted docs.
16. Merged != Done. Do not report Done without the acceptance evidence required by the issue/program (deploy, production verification, restore drill, live verification, etc.).
17. Standard exit summary must stay concise: `STATUS`, `IDENTITY`, `CHANGED_PATHS`, `TESTS`, `CI`, `RISKS`, `BLOCKERS`, `PR`, `NEXT_STEP`, `SAFETY`. Expand only for failures or disputed evidence.
