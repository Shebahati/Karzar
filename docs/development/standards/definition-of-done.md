# Definition of Done — Engineering

**Status:** Proposed · Use with [`pr-checklist.md`](./pr-checklist.md)

Every checklist includes: tests, docs, ADR/RFC citations (if relevant), rollback note, ingestion safety.

---

## Feature PR

- [ ] Requirement/ticket linked  
- [ ] Scope matches one concern; branch `feature/*`  
- [ ] Bible → relevant ADR/RFC/Domain/IA read if meaning/URLs/specs touched  
- [ ] Tests added/updated; CI green  
- [ ] Docs updated if behavior/contract changed  
- [ ] ADR/RFC cited in PR when required ([citation rules](./documentation-citation-rules.md))  
- [ ] Rollback note (flag, revert commit, or compensating action)  
- [ ] Ingestion: no production API writes; local proof if enrichment  
- [ ] No secrets; no hand schema edits  

## Bugfix PR

- [ ] Root cause stated; repro steps  
- [ ] Branch `fix/*` (or `hotfix/*` if urgent prod)  
- [ ] Regression test when feasible  
- [ ] Docs only if user-visible contract changed  
- [ ] Cite ADR if fix changes architectural behavior  
- [ ] Rollback note  
- [ ] Ingestion safety unchanged / verified  

## Docs-only PR

- [ ] Branch `docs/*` or `chore/*`  
- [ ] Classification vs legacy packs if architecture doc (MERGE/KEEP awareness)  
- [ ] No silent status upgrade of ADR/RFC to Accepted without Board note  
- [ ] Links resolve; Canon C0–C10 respected if architecture  
- [ ] N/A tests OK; CI docs checks if any  
- [ ] Rollback = git revert  
- [ ] Ingestion: N/A unless policy doc — then must not weaken local-only ban  

## Schema migration PR

- [ ] Alembic revision under `alembic/versions/`  
- [ ] Upgrade + downgrade (or explicit irreversible note with Board risk)  
- [ ] Applied on **local** baseline; `alembic current` verified  
- [ ] No hand-edit of prod/local schema outside Alembic  
- [ ] ADR/RFC cited if SoT / Fact / Property / URL schema  
- [ ] Data backfill separate Category A/B job — not sneaked into migration without declaration  
- [ ] Rollback: downgrade plan + backup expectation for Category B  
- [ ] Ingestion boundary unchanged unless RFC says otherwise  

## SEO / URL PR (slug / redirect)

- [ ] ADR-010 and RFC-004/005 cited  
- [ ] Canonical = `/product/{slug}` singular; 301 from `/product/{id}`  
- [ ] No dependency on Facts tables for EPIC 1  
- [ ] Tests: 301 matrix, canonical tags, no open redirect  
- [ ] Sitemap / internal links updated or ticketed  
- [ ] Rollback: feature flag / route revert  
- [ ] Ingestion: N/A (routing only)  

## Enrichment script PR

- [ ] Declares Source, Destination, Owner, Validation, Audit, Rollback  
- [ ] Default / docs show **local** `KARZAR_API_BASE` (not production)  
- [ ] Category A only unless Category B ticket path documented  
- [ ] Dry-run / fail-closed on unexpected delta when available  
- [ ] Property/ADR-004 considered if new JSON keys  
- [ ] `top:*` not presented as customer Properties  
- [ ] Proof run on local baseline attached or described  
- [ ] Rollback / inverse job noted  
- [ ] **No** production write in CI or developer default  

---

## Shared exit criteria

PR approved · CI green · Lifecycle stages respected (`development-lifecycle-standard.md`) · Repo protection intent intact (no force-push to main).
