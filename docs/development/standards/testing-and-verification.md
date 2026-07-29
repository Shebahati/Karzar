# Testing & Verification

**Status:** Proposed

---

## Expectations by change type

| Type | Minimum |
|------|---------|
| Feature | Unit and/or API tests for new behavior; manual smoke on local |
| Bugfix | Regression test when practical |
| Schema | Local Alembic upgrade; smoke read/write affected paths |
| SEO/URL | 301/canonical matrix; sample crawl |
| Enrichment | Dry-run or count validation on local; fail-closed check |
| Docs-only | Link/render sanity |

## Environments

Run against **local** baseline DB/API. Do not require production writes to “verify enrichment.”

## Ready / smoke

Use project `/ready` or equivalent health checks after boot/migrate when available.

## AI / search

Offline eval stubs before generative features; refusal cases when Evidence missing (RFC-006).

## What “green” means

CI pass ≠ production Category B authorization. Lifecycle still requires review + local + deploy path.
