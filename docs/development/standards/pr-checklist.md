# PR Checklist — Karzar

**Status:** **Accepted** (Wave-1 · part of Developer Standards) · Paste into PR description or use as review gate  
**Canon Lock:** [`docs/architecture/CANON-LOCK.md`](../../architecture/CANON-LOCK.md)

## Always

- [ ] Branch from current mainline (`feature/*` | `fix/*` | `hotfix/*` | `chore/*` | `docs/*`) — **no direct `main` commits**  
- [ ] One concern per PR  
- [ ] CI green  
- [ ] Reviewer approved  
- [ ] **No secrets** committed (`.env`, keys, tokens)  
- [ ] **No production API base** in enrichment scripts / defaults for routine work  
- [ ] Rollback note present  
- [ ] DoD checklist for PR type completed ([`definition-of-done.md`](./definition-of-done.md))  
- [ ] **Canon Lock checked** — relevant **Accepted/Binding** rows cited in PR body (see [`CANON-LOCK.md`](../../architecture/CANON-LOCK.md))  

## Architecture / meaning triggers

- [ ] Touches product **meaning** (entities, Facts, Properties)? → Domain + relevant ADR cited  
- [ ] Touches **URLs / SEO**? → **ADR-010** / **RFC-004** / **RFC-005** cited (Wave-1 Accepted) + IA epic1 readiness  
- [ ] Touches **specs keys / JSONB**? → Property governance / ADR-004 considered  
- [ ] Touches **AI / RAG / embeddings**? → ADR-009 gates checked (Evidence≈0 ⇒ no gen answers); not authorized by Wave-1 lock  
- [ ] Touches **schema**? → Alembic revision + local upgrade proof  
- [ ] Touches **ingestion / enrichers**? → **ADR-012** + `data-ingestion-policy.md` Category declared; local-only proof  
- [ ] Large cross-cutting change? → RFC **Accepted** (or linked Draft with Board path — not self-Accept)  

## Storefront / API

- [ ] Breaking API changes versioned or documented  
- [ ] FA content: display strings ≠ raw spec keys as Properties  
- [ ] Error handling: no silent empty that hides PDF/accessories slots when IA requires honesty  

## Explicit fails (reject PR)

- Production `KARZAR_API_BASE` as default for Category A scripts  
- Hand SQL schema change on prod/local bypassing Alembic  
- Self-marking ADR/RFC Implemented/Accepted without Board  
- Force-push instructions to `main`  
- Dual-write / Fact publish without RFC-001/003 gates  
- EPIC 1 URL/SEO/enrich PR **without** citing Wave-1 Canon Lock rows (ADR-010 / RFC-004/005 / ADR-012 as applicable)  
- Using Proposed-only docs as sole merge justification while ignoring Accepted Canon Lock  
