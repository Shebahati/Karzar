## Summary
<!-- One concern. What changed and why. -->

## Task / Node
- Task: <!-- PMO ID from project-management/exports/tasks.json, or NONE — CR-008 -->
- Node: <!-- AODS NODE_ID when executed under Auto Mode, else N/A -->

## Canon Lock
Canon Lock: docs/architecture/CANON-LOCK.md (Wave-1)
Refs: <!-- ADR/RFC IDs that bind this change -->
Packs: <!-- IA / policy paths if URL, SEO, or ingestion -->
Authority: <!-- paths cited for AODS nodes; must resolve on origin/main -->

```text
<!-- Minimum citation block (documentation-citation-rules.md) — fill or delete unused lines -->
Canon Lock: docs/architecture/CANON-LOCK.md (Wave-1)
Refs:
Packs:
Baseline:
```

## Checklist (Always)
<!-- From docs/development/standards/pr-checklist.md — Accepted -->

- [ ] Branch from current mainline (`feature/*` | `fix/*` | `hotfix/*` | `chore/*` | `docs/*`) — no direct `main` commits; no new `feat/*` (CR-002 A)
- [ ] One concern per PR
- [ ] CI green
- [ ] Reviewer approved
- [ ] No secrets committed (`.env`, keys, tokens)
- [ ] No production API base in enrichment scripts / defaults for routine Category A work
- [ ] Rollback note present (below)
- [ ] DoD checklist for PR type completed (`docs/development/standards/definition-of-done.md`)
- [ ] Canon Lock checked — relevant Accepted/Binding rows cited above

## Frontend collaborator (if author is FE Write collaborator)
<!-- docs/FRONTEND_COLLABORATOR_CHARTER.md — self-merge allowed when CI green; no Owner review required -->
- [ ] Paths limited to frontend allowlist (no `package.json` / lockfile; no backend/Canon/OpenAPI)
- [ ] Did **not** use quarantined docs (`frontend/AI_CONTEXT.md`, `BACKEND_NON_COMPLIANCE`, `FRONTEND_IMPLEMENTATION_GUIDE`)
- [ ] No Facts assert/publish, dual-write, RAG, Taxonomy/Dictionary editors, `PRODUCT_CLASSIFIED_AS`
- [ ] OpenAPI / as-built: no invented API fields
- [ ] Local: `tsc --noEmit` + lint + test in touched app
- [ ] After merge: Deploy Staging + smoke www/admin/api `/ready` (staging = live VPS)

## Architecture triggers (tick if applicable)
- [ ] Product meaning / Facts / Properties → Domain + ADR cited
- [ ] URLs / SEO → ADR-010 + RFC-004/005 + IA cited
- [ ] Specs / JSONB → Property governance / ADR-004 considered
- [ ] Schema → Alembic revision + local upgrade proof
- [ ] Ingestion / enrichers → ADR-012 + Category declared; local-only proof

## Test plan
- [ ] <!-- Commands / checks a reviewer can run -->

## Rollback
<!-- Flag, revert commit, or compensating action -->
