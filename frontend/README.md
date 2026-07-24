# Karzar Frontend

Frontend monorepo for **کارزار (Karzar)** — B2B/B2C industrial tools commerce.

Two independent Next.js App Router apps share one repo for synchronized releases:

```text
karzar-frontend/
├── Storefront/          # Customer shop (default local :3000)
├── admin-panel/         # Super-admin ops dashboard (default local :3001)
├── docs/
│   ├── audits/          # API & UI/UX audit reports (FA + EN)
│   ├── gaps/            # BE↔FE non-compliance (FE-ahead & unused BE APIs)
│   └── deploy/          # Production deployment guides (FA + EN)
├── INTEGRATION_RUNTIME_NOTES.md
├── LOCAL_STACK_ACCESS.md
└── FRONTEND_CHANGES.md
```

Backend lives in a separate codebase (`backend`, FastAPI). This repository does **not** contain or publish the API.

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Framework | Next.js 14+ (App Router) |
| Language | TypeScript |
| Styling | Tailwind CSS + logical RTL properties |
| Data | TanStack Query v5 · Zustand (Storefront cart) |
| Forms | React Hook Form + Zod |
| HTTP | Axios (`NEXT_PUBLIC_API_BASE_URL`) + optional mock layer |

**Locale (non-negotiable):** `lang="fa"` · `dir="rtl"` · **IRANYekanX** · Persian digits via `toPersianDigits` / `formatToman` / `tnum`.

---

## Core product rules

1. **Dual-lane commerce** — Priced SKUs → `/cart` → purchase checkout/payment. Unpriced (`base_price == null`) → `/quote` → inquiry checkout.
2. **Storefront auth** — OTP primary; password reset/change available under `/account/security`.
3. **Admin auth** — Password login + step-up PIN (`X-Step-Up-Token`) for destructive actions.
4. **Idempotency** — `Idempotency-Key` on checkout and payment init.
5. **Honesty** — No fabricated SMS success; Documents/Settings labeled until server APIs exist.

---

## Recent remediation (July 2026)

Phases 1–5 of frontend audit remediation on `main`:

1. **Critical** — stable idempotency, payment recovery, admin redirect sanitize, session refresh, bulk step-up, Reports honesty, CSP localhost connect-src
2. **Session/cart** — post-OTP cart reconcile, AuthGate + role check, dynamic mock-api, cookie contract doc
3. **Honesty UX** — estimated timeline, SMS copy, order tabs, product enrich, moderation/terms, mock-only optional password
4. **SEO/perf** — home RSC prefetch, product sitemap, lazy PDP sections, image allowlist
5. **Hardening** — Vitest + Playwright smoke, real admin README/`.env.example`, prod CSP without `unsafe-eval`, skip-link + mobile menu focus trap

Details: `docs/audits/`, `AI_CONTEXT.md` §21, app READMEs.

---

## Documentation index

| Topic | فارسی | English |
|-------|--------|---------|
| API gaps audit | [`docs/audits/01-api-gaps-fa.md`](docs/audits/01-api-gaps-fa.md) | [`docs/audits/01-api-gaps-en.md`](docs/audits/01-api-gaps-en.md) |
| UI/UX audit | [`docs/audits/02-uiux-audit-fa.md`](docs/audits/02-uiux-audit-fa.md) | [`docs/audits/02-uiux-audit-en.md`](docs/audits/02-uiux-audit-en.md) |
| FE ahead → BE must build | [`docs/gaps/01-fe-ahead-be-needed-fa.md`](docs/gaps/01-fe-ahead-be-needed-fa.md) | [`docs/gaps/01-fe-ahead-be-needed-en.md`](docs/gaps/01-fe-ahead-be-needed-en.md) |
| BE exists → FE should use | [`docs/gaps/02-be-exists-fe-should-use-fa.md`](docs/gaps/02-be-exists-fe-should-use-fa.md) | [`docs/gaps/02-be-exists-fe-should-use-en.md`](docs/gaps/02-be-exists-fe-should-use-en.md) |
| Deployment | [`docs/deploy/DEPLOYMENT_fa.md`](docs/deploy/DEPLOYMENT_fa.md) | [`docs/deploy/DEPLOYMENT_en.md`](docs/deploy/DEPLOYMENT_en.md) |

---

## Getting started (local)

**Prerequisites:** Node.js 18.17+ (20 LTS recommended), running API at `http://localhost:8000` (or enable mocks).

### Storefront

```bash
cd Storefront
cp .env.example .env.local
npm install
npm run dev -- --port 3000
```

### Admin panel

```bash
cd admin-panel
cp .env.example .env.local
npm install
npm run dev -- --port 3001
```

### Environment

| Variable | Meaning |
|----------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | Default `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_USE_MOCK` | `true` = in-memory mock; production must be `false` |

See `LOCAL_STACK_ACCESS.md` for local URL map (no production secrets).

---

## Scripts

| App | Dev | Typecheck |
|-----|-----|-----------|
| Storefront | `npm run dev` | `npx tsc --noEmit` |
| Admin | `npm run dev` | `npx tsc --noEmit` |

---

## Backend relationship

- API contract is owned by `backend` OpenAPI (`/api/docs` when enabled).
- Gaps where **frontend needs new backend APIs**: `docs/gaps/01-fe-ahead-be-needed-*`.
- Gaps where **backend already exists but FE should deepen usage**: `docs/gaps/02-be-exists-fe-should-use-*`.
- Production deploy (Nginx, Docker, security): `docs/deploy/`.

---

## License / ownership

Private product repository. Do not commit `.env`, `.env.local`, or live credentials.
