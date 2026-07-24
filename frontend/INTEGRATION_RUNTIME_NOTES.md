# Frontend ↔ Backend Integration Runtime Notes

**Date:** 2026-07-17  
**Scope:** Frontend changes (`karzar-frontend`) + minimal runtime Docker fix.  
**Backend policy:** no feature/API changes. One Dockerfile ordering fix required to boot Docker (documented below).

## Backend runtime touch (2026-07-17)

| File / action | Change | Why |
|---------------|--------|-----|
| `backend/Dockerfile` | Create `appuser` **before** `chown … appuser` | Image build failed: `chown: invalid user` |
| `backend/.env` | Created for local Docker + FE CORS/OTP echo | Required to `docker compose up` |
| DB runtime `ALTER otp_codes.code VARCHAR(64)` | Widen column | Hashed OTP (SHA-256) is 64 chars; column was 12 → OTP 500 |
| `app/db/models/content.py` | `OtpCode.code` `String(12)` → `String(64)` | Same bug; prevents re-break after volume recreate |

---

## 1. What was fixed in the frontend (2026-07-17)

### P0 — Live API blockers
| Item | Change |
|------|--------|
| OTP body | Storefront now sends `{ phone }` / `{ phone, code }` (was `phone_number`) |
| Product PUT stock | Admin `toProductUpdatePayload` omits `stock_quantity`; edit form field is read-only |
| Stock endpoints | Admin maps `GET /stock` + `POST /stock/adjust` (ProductDetail) to UI shape |
| Mock default | `.env.example` + `.env.local` set `NEXT_PUBLIC_USE_MOCK=false` |

### P1 — Commerce / session
| Item | Change |
|------|--------|
| Idempotency | `Idempotency-Key` on `POST /checkout` and `POST /payments/init` |
| Tracking timeline | Prefer server `timeline`; fallback to local builder |
| Refresh tokens | Storefront + Admin store/rotate via `/auth/refresh` |
| Logout | Calls `POST /auth/logout` then clears local storage |
| Cart server sync | `cartService` + Zustand best-effort sync + merge after OTP |
| Refund flow | Admin order panel: refund+cancel via `POST /payments/refund` + step-up |
| RATE_LIMITED | Step-up dialog surfaces Retry-After message |
| Category/Brand slug | Types + `GET /categories/slug/{slug}` / `GET /brands/slug/{slug}` resolution in catalog |

### P2 — Content
| Item | Change |
|------|--------|
| Product comments | PDP form posts `POST /products/{id}/comments` (auth required) |
| CMS Admin | Articles / Hero / Comments moderation / Contact submissions (see CMS agent deliverable) |

---

## 2. Backend runtime checklist (no code edits)

Run these **against the existing backend tree** before smoke tests:

```bash
cd backend
# ensure .env has at least:
# SECRET_KEY (32+), ADMIN_STEP_UP_PIN (6-12 digits), POSTGRES_*, 
# CORS_ORIGINS=http://localhost:3000,http://localhost:3001
# OTP_DEV_ECHO=true, PAYMENT_PROVIDER=mock, ENABLE_API_DOCS=true
# PAYMENT_CALLBACK_URL=http://localhost:3000/checkout/payment/callback
# PAYMENT_SUCCESS_REDIRECT_URL=http://localhost:3000/checkout/success
# PAYMENT_FAILURE_REDIRECT_URL=http://localhost:3000/checkout/payment/failed

alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
# Storefront :3000
cd karzar-frontend/Storefront && npm install && npm run dev -- --port 3000

# Admin :3001
cd karzar-frontend/admin-panel && npm install && npm run dev -- --port 3001
```

---

## 3. Smoke E2E checklist

1. Storefront OTP request/verify with live API (`dev_code` in DEBUG)
2. PLP filters + PDP + add to cart/quote
3. Checkout purchase → payment init → callback verify → track timeline
4. Checkout inquiry (guest OK)
5. Admin login → edit product (no stock overwrite) → stock adjust
6. Admin order: ship with postal code; refund paid order; cancel unpaid with step-up
7. Admin CMS list/create/delete (step-up on delete)
8. Product comment create while logged in

---

## 4. Known remaining gaps (backend API limitations — not FE bugs)

| Gap | Owner |
|-----|--------|
| Product `slug` not in Product API | Backend (use `/product/[id]` until added) |
| No `/reports` aggregate API | Backend / FE client-side aggregate OK for now |
| No PDF invoice endpoint | Backend |
| Documents page storage | Backend or remove mock later |
| Public tracking omits `estimated_total` / postal / ETA by design | Backend (intentional) |

---

## 5. Deploy env (production)

```env
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_BASE_URL=https://<api-host>/api/v1
```

CORS on backend must include the production storefront + admin origins.

---

*Logged by frontend integration work — 2026-07-17*
