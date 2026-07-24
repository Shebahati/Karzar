# Admin Panel — کارزار

Next.js App Router dashboard for Karzar super-admins (catalog, orders, CMS, audit).

## Local setup

```bash
cd frontend/admin-panel
cp .env.example .env.local
npm install
npm run dev -- --port 3001
```

Open http://localhost:3001

### Env

| Variable | Default | Notes |
|----------|---------|--------|
| `NEXT_PUBLIC_USE_MOCK` | `false` | `true` = in-memory mock API (no backend) |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | Live FastAPI base |
| `NEXT_PUBLIC_MOCK_LATENCY_MS` | `650` | Simulated mock latency |

### Mock credentials (only when `USE_MOCK=true`)

- Phone: `09120000000`
- Password: `Admin@123456`
- Step-up PIN: `84729101`

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev server |
| `npm run build` / `start` | Production |
| `npm test` | Vitest unit tests |
| `npm run test:e2e` | Playwright smoke (mock) |

## Auth model

- Login: OAuth2 password form → JWT in `localStorage`
- Soft session cookie `karzar_admin_session` for middleware UX
- `AuthGate` confirms `/auth/me` role `super_admin`
- Destructive actions require step-up PIN (`X-Step-Up-Token`)
- Optional password login setting is **mock-only**

See also: `../docs/auth-cookie-httponly-contract.md`, `../AI_CONTEXT.md`, `../README.md`.
