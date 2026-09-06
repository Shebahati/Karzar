# Karzar frontend

| App | Path | Local |
|-----|------|-------|
| Storefront | `frontend/Storefront/` | `:3000` |
| Admin | `frontend/admin-panel/` | `:3001` |

Next.js 16 / React 19 / Tailwind / TanStack Query. Locale: `lang="fa"` `dir="rtl"` IRANYekanX.

Setup, env, and scripts: [`docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md).

`NEXT_PUBLIC_API_BASE_URL` is the only public API base (default `http://localhost:8000/api/v1`). `NEXT_PUBLIC_USE_MOCK=true` is local-only.

Domain rules: [`docs/COMMERCE.md`](../docs/COMMERCE.md). Admin session: signed HttpOnly cookie — see Development. Routes: ADR-010 (`/product/{slug}`, 301 from id, `/brands/{slug}`, `/categories/{slug}`).
