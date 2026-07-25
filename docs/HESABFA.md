# Hesabfa (حسابفا) Level-4 integration

## Scope (locked product decisions)

| Concern | Direction |
|---------|-----------|
| Catalog & prices | **Site is source of truth** — do not push catalog/prices site→Hesabfa as primary |
| Stock | **Pull Hesabfa → site** for SKU-matched items only; never push site-only stock |
| Contacts | One Hesabfa contact **per customer** (create/link on demand by phone) |
| Inquiry / proforma | **Not synced** |
| Sale invoice | Created in Hesabfa **after payment verify** (hook wired; skipped while `HESABFA_TEST_MODE=true`) |
| Admin | Shows **Hesabfa total sales** vs **website-only paid sales** separately |

## Environment variables (VPS / `.env`)

Set these on the API host only (Compose env file or `/opt/karzar/.deploy-secrets`). **Never commit real keys.**

```bash
# Master switch
HESABFA_ENABLED=true

# Secrets (from Hesabfa: Settings → API)
HESABFA_API_KEY=...
HESABFA_LOGIN_TOKEN=...

# Optional legacy auth if loginToken is unavailable
# HESABFA_USER_ID=
# HESABFA_PASSWORD=

# API
HESABFA_BASE_URL=https://api.hesabfa.com/v1
HESABFA_TIMEOUT_SECONDS=15

# true = stock sync + admin reads OK; invoice writes are skipped (sandbox)
HESABFA_TEST_MODE=true

# Optional warehouse filter for GetQuantity
# HESABFA_WAREHOUSE_CODE=

# Background stock pull interval (seconds)
HESABFA_STOCK_SYNC_INTERVAL_SECONDS=3600

# Site stores Tomans; Hesabfa invoices usually expect Rials
HESABFA_CURRENCY_UNIT=rial
HESABFA_CURRENCY_CODE=IRR
```

### Staging checklist

1. Add the vars to the API container env on VPS `195.177.255.198` (container often `lathe_api`).
2. Run migrations: `alembic upgrade head` (creates `hesabfa_*` tables).
3. Keep `HESABFA_TEST_MODE=true` until credentials and SKU matches are verified.
4. Admin: `POST /api/v1/hesabfa/mappings/sync` then `POST /api/v1/hesabfa/stock/sync`.
5. When payment gateway is live and ready for real docs: set `HESABFA_TEST_MODE=false`.

## Admin API

All routes require super-admin auth.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/hesabfa/status` | Enabled / configured / test mode (no secrets) |
| POST | `/api/v1/hesabfa/mappings/sync` | Match site `sku` ↔ Hesabfa `ProductCode` |
| POST | `/api/v1/hesabfa/stock/sync` | Pull stock for matched codes |
| GET | `/api/v1/hesabfa/sales-summary` | Website paid total vs Hesabfa sale invoice sum |

## Matching rule

Hesabfa item `ProductCode` must equal the site product `sku` (case-insensitive). Accounting `Code` is stored in `hesabfa_item_mappings` and used on invoices.

## Payment hook

`verify_order_payment` calls `maybe_create_invoice_after_payment` after a successful verify. Failures are logged and recorded in `hesabfa_invoice_records`; they never roll back payment success.

While the gateway is not live / `HESABFA_TEST_MODE=true`, the hook no-ops with status `skipped`.
