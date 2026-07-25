# Hesabfa (حسابفا) Level-4 integration

## Scope (locked product decisions)

| Concern | Direction |
|---------|-----------|
| Catalog & prices | **Site is source of truth** — do not push catalog/prices site→Hesabfa as primary |
| Stock / warehouse counts | **Hesabfa only** — site never stores or displays numeric stock; only **موجود / ناموجود** (`is_available`) |
| Item shells | **Site → Hesabfa** create/upsert on product save + backfill (`ProductCode` = site `sku`, stock left at **0**) |
| Contacts | One Hesabfa contact **per customer** (create/link on demand by phone) |
| Inquiry / proforma | **Not synced** |
| Sale invoice | Created in Hesabfa **after payment verify** (hook wired; skipped while `HESABFA_TEST_MODE=true`) |
| Admin | Shows **Hesabfa total sales** vs **website-only paid sales** separately |
| Categories | **Not synced** by default — shop IA ≠ accounting `nodeFamily`; match products by SKU only |

## Environment variables (VPS / `.env`)

Set these on the API host only (Compose env file or `/opt/karzar/.deploy-secrets`). **Never commit real keys.**

```bash
HESABFA_ENABLED=true
HESABFA_API_KEY=...
HESABFA_LOGIN_TOKEN=...
HESABFA_BASE_URL=https://api.hesabfa.com/v1
HESABFA_TIMEOUT_SECONDS=15
# true = invoice writes skipped; item push still allowed
HESABFA_TEST_MODE=true
HESABFA_CURRENCY_UNIT=rial
HESABFA_CURRENCY_CODE=IRR
```

### Staging checklist

1. Add vars to API container on VPS `195.177.255.198`.
2. `alembic upgrade head` (hesabfa tables + `products.is_available`).
3. Keep `HESABFA_TEST_MODE=true` until verified.
4. `POST /api/v1/hesabfa/items/push` to backfill site products (qty 0).
5. When gateway live: `HESABFA_TEST_MODE=false`.

## Admin API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/hesabfa/status` | Enabled / configured / test mode |
| POST | `/api/v1/hesabfa/mappings/sync` | Match site `sku` ↔ Hesabfa `ProductCode` |
| POST | `/api/v1/hesabfa/items/push` | Create/upsert site products in Hesabfa (stock 0) |
| POST | `/api/v1/hesabfa/stock/sync` | **Deprecated no-op** |
| GET | `/api/v1/hesabfa/sales-summary` | Website vs Hesabfa sales |

## Inventory policy

- Warehouse counts: **Hesabfa only**.
- Site: `is_available` boolean. Storefront shows **موجود** / **ناموجود**.
- Do **not** import `GetQuantity` into the site.
- Product create/update pushes Hesabfa item shell at qty 0 when integration is enabled.

## Categories

Hesabfa `item/save` supports `nodeFamily`, but site categories are **not synced** (shop IA ≠ accounting folders). Match by SKU only.

## Payment hook

`verify_order_payment` → `maybe_create_invoice_after_payment`. Failures never roll back payment. `HESABFA_TEST_MODE=true` → skip with status `skipped`.
