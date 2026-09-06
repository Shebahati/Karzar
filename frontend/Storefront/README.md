# Storefront

Public shop (`:3000`). Setup: [`docs/DEVELOPMENT.md`](../../docs/DEVELOPMENT.md). Domain: [`docs/COMMERCE.md`](../../docs/COMMERCE.md).

| Variable | Notes |
|----------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | FastAPI `/api/v1` |
| `NEXT_PUBLIC_USE_MOCK` | Local mock only; OTP code `111111` when mock |
| `NEXT_PUBLIC_ASSET_BASE_URL` | Optional `next/image` origin |

Routes: `/product/{slug}` (canonical), `/product/{id}` 301, `/brands/{slug}`, `/categories/{slug}` (ADR-010).

Scripts: `npm run dev`, `npm test`, `npm run test:e2e`, `npm run build`.
