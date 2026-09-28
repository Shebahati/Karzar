# Emalls product extraction API (Karzar adapter)

**Status:** Implementation evidence (not Board-Accepted).  
**Concern:** Read-only marketplace compatibility adapter.  
**Does not mutate:** catalog, prices, availability, images, categories, KB facts, payment, shipping.

## 1. Purpose

Expose Karzar's **canonical public storefront catalog** to Emalls via a dedicated compatibility contract.

```
Karzar canonical catalog
        ↓
Emalls read-only compatibility adapter
        ↓
Emalls
```

Emalls must **not** consume `GET /api/v1/products/` directly. This adapter owns authentication, pagination, field mapping, and observability for Emalls.

## 2. Route

| Item | Value |
|------|-------|
| Method | `POST` |
| Path | `/api/v1/integrations/emalls/products` |
| Auth | Emalls request `token` (validated remotely; cached) |
| Admin session | Not required / not used |
| Catalog writes | None |

## 3. Request contract

WordPress-plugin-compatible field names. Accepted encodings (WP `get_param` parity):

1. `application/json`
2. `application/x-www-form-urlencoded`
3. Equivalent POST query parameters (merged; body overlays query)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `token` | string | yes | Supplied by Emalls. Never logged. Never echoed. |
| `page` | int | no | Default `1`, minimum `1` |
| `limit` | int | no | Default `50`, minimum `1`, **maximum `100`** |
| `variation` | any | no | Accepted and **ignored** (Karzar has no WC variations) |

Malformed page/limit/token still return Karzar's standard **422** envelope.

## 4. Response contract

```json
{
  "count": 1234,
  "max_pages": 25,
  "products": [ /* EmallsProduct */ ],
  "Version": "1.3.0",
  "NeedSession": true
}
```

| Field | Semantics (official plugin v1.3.0) |
|-------|-------------------------------------|
| `Version` | Emalls **compatibility/protocol** version (`EMALLS_COMPAT_VERSION`, default `1.3.0`) — not the internal Karzar adapter software version |
| `NeedSession` | `true` after a fresh remote token validation; `false` when served from a still-valid positive cache hit |

### Security decision: `TokenSendByEmalls`

Official WordPress plugin responses may echo `TokenSendByEmalls`. Karzar **does not** return the raw token in the response. Emalls already sent it; reflecting secrets is unnecessary and unsafe.

**EXTERNAL_COMPATIBILITY_GATE:** Does Emalls require `TokenSendByEmalls` in custom integrations? Verify during staging/live-token handoff. Reintroduce only in a separately reviewed change if Emalls proves it is required.

Fake WordPress/PHP/WooCommerce metadata is **not** included.

## 5. Field mapping

| Emalls field | Karzar source |
|--------------|---------------|
| `title` | `product.name` |
| `subtitle` | `""` (no English title field; do not invent) |
| `parent_id` | `0` |
| `page_unique` | `product.id` (stable) |
| `current_price` | `product.base_price` as decimal string (TOMAN); `""` if null |
| `old_price` | `product.original_price` when present; otherwise `base_price` (Emalls/WooCommerce regular-price parity); `""` if both null |
| `availability` | `product_is_available(product)` → `instock` / `outofstock` |
| `category_name` | assigned category `name` (leaf/current; not breadcrumb) |
| `image_link` | first valid public image (primary-first), absolutized |
| `image_links` | all valid public images, primary first, no duplicates/placeholders |
| `page_url` | `{EMALLS_PUBLIC_SITE_ORIGIN}/product/{slug}` |
| `short_desc` | `product.short_description` or `""` |
| `spec` | `[{ ...public technical_specs, dimensions, features..., "شناسه کالا": sku }]` |
| `guarantee` | `product.warranty_text` or `""` |
| `registry` | `""` (no regulated registry field) |
| `date_added` | `created_at` ISO-8601 |
| `date_updated` | `updated_at` ISO-8601 |
| `product_type` | `"simple"` |

### Null / no-discount price behavior

| Karzar | Emalls `current_price` | Emalls `old_price` |
|--------|------------------------|--------------------|
| `base_price` set, `original_price` null (no discount) | `base_price` | `base_price` (regular-price parity) |
| `base_price` set, `original_price` set (discount) | `base_price` | `original_price` |
| both null | `""` | `""` |

Adapter-only fallback: do **not** write `original_price` in the DB and do **not** change storefront discount semantics. Inquiry/unpriced SKUs remain exportable when storefront-public.

## 6. Price unit = TOMAN

Site catalog prices are **TOMAN**.

```
current_price = base_price                          # exact pass-through
old_price     = original_price or base_price or ""  # WC regular-price parity
```

- Do **not** multiply or divide by 10.
- Do **not** convert to IRR for this adapter unless Emalls later **explicitly** confirms a custom-API rial requirement.
- Example: storefront `2,500,000 تومان` → `current_price = "2500000"`.

**External remaining gate:** confirm with Emalls whether their custom API expects تومان or ریال. Karzar defaults to TOMAN pass-through.

## 7. Availability semantics

Canonical site availability is binary:

```
product_is_available = product.is_active AND product.is_available
```

| Result | Emalls `availability` |
|--------|------------------------|
| True | `instock` |
| False | `outofstock` |

**`stock_quantity` is NOT authoritative inventory.** Warehouse counts live in Hesabfa only. This adapter never reads `stock_quantity` for availability.

Public + unavailable products **remain exported** as `outofstock` (they do not disappear from Emalls solely because they are out of stock).

## 8. Visibility / export policy

Exact predicate (SQL + settings): `storefront_public_product_filters()` from `app/utils/public_catalog.py`:

1. `deleted_at IS NULL`
2. `is_active = true`
3. When `STOREFRONT_HIDE_IMAGELESS_PRODUCTS` (default true): at least one non-placeholder product image URL exists
4. When `STOREFRONT_REQUIRE_MATERIALIZED_IMAGES` (DEBUG default): primary public image must exist on local upload disk

Ordering: `Product.id DESC` (stable pagination; no duplicates across adjacent pages under a static dataset).

## 9. Token validation flow

1. Emalls POSTs `token` (+ page/limit) as JSON **or** form-urlencoded (query params also merged).
2. Cache lookup: key `emalls:token:<sha256(token + normalized_domain)>`.
3. Cache hit → serve products with `NeedSession=false` (no outbound call).
4. Cache miss → `POST` to `EMALLS_VALIDATION_URL` with `token`, `shop_domain`, `version=EMALLS_COMPAT_VERSION` (default `1.3.0`).
5. Success **only** when `success === true` **and** normalized message equals exactly `the token is valid` → cache positive marker for TTL → serve products with `NeedSession=true`.
6. Any other success/message combination → HTTP **401** (invalid token). Invalid tokens are never positively cached.
7. Timeout / 5xx / network / malformed JSON with **no** valid cache → fail closed HTTP **503**.

Raw tokens are never logged, never stored in Postgres, and never returned in responses.

## 10. Cache behavior

| Setting | Default |
|---------|---------|
| `EMALLS_TOKEN_CACHE_TTL_SECONDS` | `3600` |
| Backend | Redis when `REDIS_HOST` set; else process-local memory |
| Cached value | Positive `"1"` marker only |

## 11. Error behavior

| HTTP | When |
|------|------|
| 422 | Invalid page/limit/body/content-type (Pydantic / parser) |
| 401 | Emalls token invalid |
| 429 | Per-IP throttle exceeded |
| 503 | Validator unavailable and no valid cache |
| 500 | Unexpected internal error (no exception internals leaked) |

## 12. Security rules

- Redact token from logs (`[redacted]`).
- Do not echo secrets in error bodies.
- Do not log raw request bodies.
- Body size limited by existing `MAX_REQUEST_BODY_BYTES` middleware.
- Dedicated throttle: `PUBLIC_THROTTLE_EMALLS_MAX` / `WINDOW` (default 120 / 60s).
- No admin auth dependency.
- No DB writes from this path.
- Redis token cache writes are allowed.

## 13. Staging test procedure

1. Point client at local/staging API base (`http://127.0.0.1:8000/api/v1`).
2. Use a **test** Emalls token (never commit real tokens).
3. Run `python scripts/emalls_preflight.py --request-format form --base-url ... --token "$TOKEN"` (form is the default external-compat mode).
4. Confirm PRICE / AVAILABILITY / URL / IMAGE / SKU canary against known products.
5. Paginate with `limit=100` and verify `count`, `max_pages`, no duplicate `page_unique`.
6. Only label a run **FULL FEED PREFLIGHT** when executed against a real local/staging catalog snapshot — not a two-row fixture.

## 14. Production handoff procedure

1. Merge PR; Owner-authorized deploy separately (not part of this change).
2. Set env: `EMALLS_SHOP_DOMAIN`, `EMALLS_PUBLIC_SITE_ORIGIN`, `EMALLS_COMPAT_VERSION=1.3.0`, Redis available for cache.
3. Register endpoint URL with Emalls: `https://api.karzartools.com/api/v1/integrations/emalls/products`.
4. Emalls supplies live token; validate with preflight against staging first if possible.
5. Confirm price-unit expectation with Emalls (TOMAN vs IRR) before go-live claims.
6. Confirm whether `TokenSendByEmalls` is required for custom integrations.

## 15. Rollback procedure

1. Disable route at reverse-proxy / deploy previous image — **no catalog data rollback required** (read-only adapter).
2. Optionally set throttle max to `1` as a temporary soft disable while investigating.
3. Clear Redis keys matching `emalls:token:*` if a poisoned cache marker is suspected (rare; only positive markers are stored).

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `EMALLS_VALIDATION_URL` | `https://emalls.ir/swservice/wp_plugin.ashx` | Token validator |
| `EMALLS_TOKEN_CACHE_TTL_SECONDS` | `3600` | Positive cache TTL |
| `EMALLS_SHOP_DOMAIN` | `karzartools.com` | Validator shop_domain |
| `EMALLS_PUBLIC_SITE_ORIGIN` | `https://www.karzartools.com` | PDP URL origin |
| `EMALLS_HTTP_TIMEOUT_SECONDS` | `8` | Outbound timeout |
| `EMALLS_COMPAT_VERSION` | `1.3.0` | Protocol version for validator + response `Version` |
| `EMALLS_ADAPTER_SOFTWARE_VERSION` | `1.0.0` | Internal software version (logs/docs only) |
| `PUBLIC_THROTTLE_EMALLS_MAX` | `120` | Per-IP request budget |
| `PUBLIC_THROTTLE_EMALLS_WINDOW` | `60` | Throttle window seconds |

There is **no** `EMALLS_TOKEN` setting — the token arrives on each Emalls request.
