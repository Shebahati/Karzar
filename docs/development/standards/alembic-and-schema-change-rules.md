# Alembic & Schema Change Rules

**Status:** Proposed · Aligns development-lifecycle-standard · git workflow

---

## Hard rules

1. **All schema changes** go through Alembic revisions under `alembic/versions/`.  
2. **No hand-edit** of production or local schema (psql DDL) as a substitute.  
3. Apply and verify on **local** baseline before any production deploy path.  
4. Production schema changes arrive via **deploy + Alembic upgrade**, not laptop sessions.  
5. Baseline head reference: document intended revision (EPIC 0 freeze cited `c4d5e6f7a8b9` — do not invent “already migrated” Facts tables).

---

## PR requirements

| Requirement | Detail |
|-------------|--------|
| Revision file | One clear concern; message explains why |
| Upgrade | Idempotent-safe as practical |
| Downgrade | Provided OR explicit irreversible + risk acceptance note |
| Local proof | `alembic upgrade head` (or project boot path) + `alembic current` |
| Data backfill | Separate versioned job (Category A/B) — declare; don’t hide in DDL without review |
| Citations | ADR/RFC if Property/Fact/URL/identity schema |

---

## Forbidden

- Editing migrated tables in prod to “match” code  
- Squashing/rewriting applied production revisions without Board process  
- Shipping Fact/dual-write schema without RFC-001/003 gates acknowledged  

---

## Rollback

Prefer Alembic downgrade on non-prod; production downgrade only with backup + owner approval. If irreversible, compensating forward migration + data job.
