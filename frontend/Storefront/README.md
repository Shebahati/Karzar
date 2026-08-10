# Storefront — کارزار

Customer-facing Next.js shop (catalog, dual-lane cart, OTP checkout, account).

## Local setup

```bash
cd frontend/Storefront
cp .env.example .env.local
npm install
npm run dev -- --port 3000
```

Open http://localhost:3000

### Env

See `.env.example`:

- `NEXT_PUBLIC_USE_MOCK` — offline mock layer
- `NEXT_PUBLIC_API_BASE_URL` — FastAPI `/api/v1`
- `NEXT_PUBLIC_ASSET_BASE_URL` — optional image origin for `next/image` allowlist
- `NEXT_PUBLIC_MOCK_LATENCY_MS` — mock delay

### Mock OTP

When `NEXT_PUBLIC_USE_MOCK=true`, OTP code is `111111` (see `OTP_MOCK_CODE` / mock API).

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev server |
| `npm run build` / `start` | Production |
| `npm test` | Vitest (validation, idempotency, cart lanes, pending payment) |
| `npm run test:e2e` | Playwright checkout smoke (mock) |

## Product rules

- Priced products → purchase cart → payment
- Unpriced → quote/inquiry lane
- Stable `Idempotency-Key` for checkout/payment retries
- Pending payment recovery via session + localStorage + tracking code

Parent docs: `../README.md`. (`../AI_CONTEXT.md` is quarantined — CR-015; do not use as SoT.)
