# Admin panel

Next.js App Router dashboard (`:3001`). Setup: [`docs/DEVELOPMENT.md`](../../docs/DEVELOPMENT.md).

| Variable | Default |
|----------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_USE_MOCK` | `false` |

Scripts: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`. Optional: `npm run test:e2e`.

## Auth (as-built)

Password login → API proves `super_admin` → signed **HttpOnly** cookie `karzar_admin_session` for middleware. AuthGate re-checks API session + role. Destructive actions need step-up PIN (`X-Step-Up-Token`).

JWT-in-`localStorage` is **not** the session model. Some **editor drafts** (static pages, proformas) still persist in browser `localStorage` — that is draft UX, not auth.

Do not show Hesabfa sales/stock widgets (`docs/HESABFA.md`).
