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
