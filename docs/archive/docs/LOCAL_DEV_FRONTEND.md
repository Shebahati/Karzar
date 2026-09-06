# Local Backend for Frontend E2E Testing (NEXT_PUBLIC_USE_MOCK=false)

Use this guide when the storefront or admin panel runs against the real API instead of mocks.

## Prerequisites

- Python 3.12+
- PostgreSQL 15+ (or Docker Compose stack)
- Node frontends on `http://localhost:3000` (storefront) and/or `http://localhost:3001` (admin)

## Quick start

```bash
cd Karzar
cp .env.example .env
# Set at minimum: POSTGRES_*, SECRET_KEY (32+ chars), ADMIN_STEP_UP_PIN (6–12 digits)

# Option A — Docker
docker compose up -d
docker compose exec app alembic upgrade head

# Option B — Local Python
./scripts/setup-dev.sh
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Required `.env` values for payment flow testing

```env
DEBUG=true
OTP_DEV_ECHO=true
PAYMENT_PROVIDER=mock
PAYMENT_CALLBACK_URL=http://localhost:8000/api/v1/payments/verify
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
INITIAL_SUPER_ADMIN_PHONE=09120000000
INITIAL_SUPER_ADMIN_PASSWORD=change-me-admin-password
ADMIN_STEP_UP_PIN=8472916350
```

## Seed data (automatic on first startup)

When the database has no categories, startup seeds:

- A shallow category tree with `spec_template_key` on leaf categories
- Three brands
- One active product: SKU `DEV-CHECKOUT-001`, price 250,000 Toman, stock 100

## Checkout → payment smoke test

1. Request OTP: `POST /api/v1/auth/otp/request` with `{"phone":"09123456789"}`
2. Verify OTP (dev echo): `POST /api/v1/auth/otp/verify` with phone + `dev_code`
3. Checkout: `POST /api/v1/checkout` with Bearer token, purchase mode, shipping, and `DEV-CHECKOUT-001` product id
4. Init payment: `POST /api/v1/payments/init` with `{"order_id": <id>}`
5. Open `payment_url` or call verify: `POST /api/v1/payments/verify` with authority

Guest orders return `error_code: GUEST_ORDER_NOT_PAYABLE` on payment init — the storefront must force OTP login first.

## API base URL for frontends

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

## Health checks

- `GET http://localhost:8000/health`
- `GET http://localhost:8000/ready`

## Run backend tests

```bash
pytest
```
