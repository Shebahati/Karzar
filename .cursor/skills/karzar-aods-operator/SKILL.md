---
name: karzar-aods-operator
description: >
  Karzar monorepo work. Use root AGENTS.md plus the domain doc for the change.
  Trigger on app/, frontend/, alembic/, scripts/, docs/architecture/, aods/,
  OpenAPI, Brand Hub, PDP slug, enrichment, or deploy.
---

# Karzar operator

Follow root `AGENTS.md`. Do not preload archived AODS orchestration. Current model: on-demand integrity (`aods/AODS-CHARTER.md`, `aods/README.md`; Board minute `AODS-BOARD-MINUTE-003`).

| Change | Authority |
|--------|-----------|
| URL / SEO / Brand Hub | ADR-010, RFC-004, RFC-005, `docs/COMMERCE.md` |
| Ingestion / enrich | ADR-012, `docs/architecture/data-ingestion-policy.md` |
| Schema | Alembic standards + `HC-08` |
| API shape | `openapi/v1.json` + `docs/API_CONTRACT.md` |
| Payment / availability | `docs/COMMERCE.md`, `docs/SEP_PAYMENT_GATEWAY.md`, `docs/HESABFA.md` |
| Deploy / backup | `docs/OPERATIONS.md` (`CR-011`: staging = live VPS, manual dispatch) |
| Process checks | `aods/README.md` |

Accepted index: `docs/architecture/CANON-LOCK.md`. Conflicts: `aods/10-repository-intelligence/CONFLICT-REGISTER.md` (append-only).

```bash
python3 aods/tools/aods_validate.py
python3 aods/tools/aods_validate.py --gate openapi
python3 aods/tools/aods_validate.py --gate ingestion-boundary
```
