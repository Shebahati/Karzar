# API Change Rules

**Status:** Proposed

---

## Principles

1. **Contract honesty:** document request/response changes in PR.  
2. **Prefer additive** changes; breaking changes need version/strategy note.  
3. **Resolve by slug** for storefront PDP per ADR-010/RFC-004 without removing internal id.  
4. **Brand meta exposure** for hubs (RFC-005) — do not block on Facts.  
5. **Do not strip** accessories/PDF fields from payloads as permanent “cleanup” when IA requires honest empty slots.  
6. **Authz:** material Fact publish ≠ super-admin bypass (Data Governance).  
7. **Errors:** stable error shapes; no stack traces to public clients.

---

## When ADR/RFC required

| API change | Cite |
|------------|------|
| `/product` slug resolve / redirects support | ADR-010, RFC-004 |
| `/brands/{slug}` | ADR-010, RFC-005 |
| Specs → Facts read preference | ADR-003/004, RFC-001/003 |
| Enrichment write endpoints | Ingestion policy, ADR-012 |
| AI/search generative | ADR-009, RFC-006 |

---

## Ingestion-facing APIs

Writes used by enrichers MUST be safe on local; rate/audit expectations; fail-closed validation preferred. Production bulk use = Category B controls.
