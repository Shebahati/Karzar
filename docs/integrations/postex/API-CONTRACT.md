# Postex API contract (Karzar extraction)

**Status:** Implementation evidence (not Board-Accepted).  
**Source (sole request/response authority):** [https://api.postex.ir/developers-docs/index.html](https://api.postex.ir/developers-docs/index.html)  
**Machine spec loaded by that page:** `https://api.postex.ir/swagger/external-v1/swagger.json`  
**Retrieval date:** 2026-09-10  
**OpenAPI:** `3.0.4` — title «مستندات فنی پستکس»  
**Local snapshot for tests:** `tests/fixtures/postex/swagger-external-v1.json`

This document records the official ReDoc/OpenAPI spec **and**, where labeled, Owner-authorized live production observations. WooCommerce plugin behavior is labeled **cross-check only** and never overrides the official spec or live evidence.

## 1. Auth

Official `info.description`:

> احراز هویت API های پستکس با استفاده از API Key صورت می‌گیرد  
> مقدار API Key می‌بایست در Header هر درخواست با اسم **x-api-key** ارسال گردد.

| Item | Official |
|------|----------|
| Scheme | API key in HTTP header |
| Header name | `x-api-key` |
| Security schemes object | **Absent** from `components.securitySchemes` (header is described in prose only) |
| `POST /user/access-token` | «با استفاده از API Key، توکن دسترسی کاربر برای فراخوانی سرویس‌های نیازمند احراز هویت دریافت می‌شود.» — request/response body **not** specified. Karzar v1 does **not** implement user-token login. |

`GET /user/whoami`: «اطلاعات حساب کاربری مرتبط با API Key ارسال‌شده را برمی‌گرداند.» Response schema **not** specified (HTTP 200 OK only).

## 2. Base URL

Official OpenAPI has **no** `servers` array. Paths are rooted at `/api/v1/...`.

Karzar config default (matches known production layout and the path prefix in the spec):

```
https://api.postex.ir/api/v1
```

Client calls are `{POSTEX_BASE_URL}{relative_path}` e.g. `POST /shipping/quotes` → `https://api.postex.ir/api/v1/shipping/quotes`.

Staging/production: host **must** be `api.postex.ir` over HTTPS. Localhost override is development/tests only (SEP-style).

## 3. Units (official)

| Quantity | Official field | Unit |
|----------|----------------|------|
| Parcel length / width / height | `ParcelPropertyDto.length` / `width` / `height` | **centimetres**, `int32` |
| Parcel total weight | `ParcelPropertyDto.total_weight` | **grams**, `int64` |
| Item weight | `ParcelItemDto.weight` | integer grams (`int32`), optional |
| Declared parcel value | `ParcelPropertyDto.total_value` | **«ارزش ریالی کل مرسوله»** — Rial. Format `double` in the spec. |
| Declared currency | `ParcelPropertyDto.total_value_currency` | example `IRR` (nullable) |
| Wallet balance | `BalanceResponse.amount` | **Rial** (`int64`). Description: «مبلغ موجودی به **ریال** است.» |
| Wallet top-up | `TopupRequest.amount` | Rial |

### Quote response monetary unit — **LIVE VERIFIED 2026-09-10**

`POST /shipping/quotes` response remains **undocumented** in OpenAPI (HTTP 200 OK, no schema).

**Live Owner-authorized read-only quote** (sanitized fixture `tests/fixtures/postex/live-quote-2026-09-10.json`) returned:

| Field | Observed |
|-------|----------|
| `currency` | **`"IRR"`** (top-level) |
| `pickup_price` | `1200000` |
| `shipping_prices[].service_price[].totalPrice` / `initPrice` | `1298000` |
| nested `vat` | `100000` (already included in `totalPrice`) |
| `total_cost` | `2498000` (= `pickup_price` + `totalPrice`) |
| `serviceName` | `پست پیشتاز` |
| `slaDays` | `از 84 تا 168 ساعت کاری` |

Therefore quote monetary amounts are **CONFIRMED_IRR**. Convert IRR → Toman with Karzar `TOMAN_TO_RIAL = 10`.

Karzar parser rules:

- `currency == "IRR"` → parse with `irr_to_toman`
- `currency` **absent** → explicit backward-compatible fallback to IRR (documented Postex money fields are Rial; historical fixtures)
- `currency` present and **≠ IRR** → **fail closed** (`SHIPPING_PROVIDER_CURRENCY`)
- Do **not** add nested `vat` / top-level `shipping_price_vat` on top of `totalPrice` (live identity: `pickup_price + totalPrice = total_cost`)
- When a single-service quote includes `total_cost`, require `pickup_price + service totalPrice == total_cost`

Cross-check only (WooCommerce plugin, not authority): response keys `pickup_price`, `shipping_prices[].custom_parcel_id`, `shipping_prices[].service_price[].initPrice`, `shipping_prices[].service_price[].totalPrice`. Karzar parsers accept these names **and** snake_case variants if the live API uses them, without treating the plugin as contract.

## 4. Enums documented in request schemas

### `collection_type`

From `CreateBulkParcelCommand.collection_type` / `GetShippingQuotesRequest.collection_type`:

| Value | Meaning (official HTML in description) |
|-------|----------------------------------------|
| `pick_up` | درخواست جمع‌آوری از محل فرستنده |
| `courier_drop_off` | تحویل حضوری به شرکت پستی |
| `postex_drop_off` | تحویل حضوری به پستکس |

### Courier `payment_type` (official example text)

| Value | Meaning |
|-------|---------|
| `SENDER` | پرداخت توسط فرستنده |
| `COD` | پرداخت در محل |
| `FREE_SHIPPING` | ارسال رایگان |
| `RECEIVER` | گیرنده یا پس‌کرایه |

Karzar v1 uses **`SENDER` only**. COD / wallet / Postex payment products are out of scope.

### Courier identity

`CreateParcelCourierDto`: required `name` (courier code, example `IR_POST,CHAPAR,DEKAPOST,MAHEX,etc`), `service_type` (example `EXPRESS`), `payment_type`.

## 5. Endpoints Karzar uses

Relative to `POSTEX_BASE_URL` (which already includes `/api/v1`).

### 5.1 Read / reference (bounded retry allowed)

| Method | Path | Official summary | Mutating? | Retry |
|--------|------|------------------|-----------|-------|
| GET | `/user/whoami` | Validate API key / account | Read | Yes (transient) |
| GET | `/locality/provinces` | List provinces (`q` optional) | Read | Yes |
| GET | `/locality/cities/all` | All cities | Read | Yes |
| GET | `/locality/cities/{province-code}` | Cities in province | Read | Yes |
| GET | `/locality/cities/to/all` | Destination cities (`keyword`) | Read | Yes |
| GET | `/locality/cities/from/all` | Origin cities | Read | Yes |
| GET | `/shipping-methods` | Active couriers/services for booking | Read | Yes |
| GET | `/common/shipping-methods` | Same purpose (common catalog) | Read | Yes |
| GET | `/common/boxes` | Official box sizes | Read | Yes |
| GET | `/common/payment-methods` | Payment methods | Read | Yes |
| GET | `/common/statuses` | Parcel status vocabulary | Read | Yes |
| GET | `/wallet/balance` | Wallet in Rial (admin-only, optional) | Read | Yes |

### 5.2 Quotes (non-mutating per official summary «محاسبه هزینه»)

| Method | Path | Mutating? | Retry |
|--------|------|-----------|-------|
| POST | `/shipping/quotes` | Calculate collection + shipping cost | **No create side-effect documented** | Bounded retry |

**Request (official `GetShippingQuotesRequest`, required):** `collection_type`, `from_city_code`, `parcels`.

Optional in OpenAPI: `courier` (`GetQuotesCourier`), `value_added_service` (`OptionalServices`).

**Live-observed production behavior (2026-09-10):** omitting `courier` or `value_added_service` returns HTTP 400 `invalid_fields` requiring both. Karzar therefore **always** sends:

- `courier`: `{ "courier_code": "<code>", "service_type": "<type>" }` for each enabled Postex quote service (`POSTEX_QUOTE_SERVICES`, default live-verified `IR_POST:EXPRESS`)
- `value_added_service`: `{ "request_label": false, "request_packaging": false, "request_sms_notification": false }` (OpenAPI `OptionalServices`; minimal live-compatible object)

OpenAPI vs live: treat OpenAPI as the field-name authority; treat live 400/200 evidence as the presence requirement for these two objects.

Each parcel (`GetShippingQuotesQueryParcels`): `custom_parcel_id`, `to_city_code`, `payment_type`, `parcel_properties`.

**Quote does not require** postal code or street address in the official request schema.

**Response schema:** not in OpenAPI. See §3 (live-verified shape).

### 5.3 Parcel create (side effect — **no generic retry**)

| Method | Path | Official | Mutating? | Retry |
|--------|------|----------|-----------|-------|
| POST | `/parcels/bulk` | «امکان ثبت چندین مرسوله در یک درخواست» | **Yes** | **Never** generic retry. See §8 |

**Request (`CreateBulkParcelCommand`):** `collection_type`, `remark`, `custom_batch_no`, `custom_channel`, `parcels[]` (`CreateParcelCommand`).

Each parcel required: `from`, `to`, `parcel_items`, `parcel_properties`, `courier`. Optional: `added_service`, `custom_order_no`, `custom_reference_no`, `submit_channel`, `ready_to_accept`, `drop_off_location_id`, `additional_data`.

**Response schema:** not in OpenAPI.

Cross-check only: WooCommerce reads `data.shipments[0].tracking.barcode`. Karzar maps barcode / parcel number from documented-looking keys if present, and stores the redacted raw body.

### 5.4 Lookup / reconcile

| Method | Path | Official | Use |
|--------|------|----------|-----|
| GET | `/parcels/custom-order-no/{custom-order-no}` | Lookup by `custom_order_no` sent at create | Read — **reconciliation after ambiguous timeout** |
| GET | `/parcels/{parcel-no}` | Get by parcel id (`int64`) | Read |
| GET | `/parcels` | List with `page_size`, `page_index`, filters | Read |
| GET | `/parcels/{parcel-no}/status` | Status by parcel id | Read |
| GET | `/orders/{orderNo}` | Get order (`int64`) | Read |

**Idempotency key header:** **not documented**. There is **no** documented idempotency-key support.

Stable Karzar reference: `custom_order_no` = shipment public UUID. Lookup uses `GET /parcels/custom-order-no/{custom-order-no}`.

### 5.5 Label

| Method | Path | Notes |
|--------|------|--------|
| GET | `/parcels/{parcel-no}/label` | «تولید برچسب پستی برای یک مرسوله». Path param is **string** `parcel-no` (not tracking code in the official spec). Response schema not specified; treated as PDF bytes when `Content-Type` is PDF. |
| POST | `/parcels/labels/bulk` | Array of string ids. Not used in Karzar v1 (single-parcel labels). |
| GET | `/orders/orders/{order-no}/labels` | All parcels in an order. Not used in v1. |

**Cross-check mismatch:** WooCommerce calls `/parcels/{tracking_code}/label`. Official path parameter is `parcel-no`. Karzar uses the official parcel number.

### 5.6 Ready / edit / cancel

| Method | Path | Official | Notes |
|--------|------|---------|-------|
| POST | `/parcels/mark-ready` | «آماده به ارسال کردن مرسوله». Body: array of `int64` parcel ids | Mutating. No cutoff documented. |
| PATCH/PUT | `/parcels/{parcel-no}` | Edit (`UpdateParcelRequest`) | Mutating. **No cutoff documented.** |
| POST | `/parcels/cancel-request/{parcel-no}` | «درخواست انصراف از ارسال». Body `CancelParcelRequest.reason` | Mutating. Response is HTTP 200 **OK with no schema**. Official text is a **cancellation request**, not a documented final cancel. Karzar sets `cancellation_pending` + `cancellation_requested_at` and confirms `cancelled` only from later tracking/status. Provider 4xx is returned as cutoff. Already delivered/returned/cancelled → 409. |

`POST /shipping/time-windows` exists (pickup/delivery windows). Request/response **not** specified. Isolated behind the provider; Karzar v1 does not expose it until the body schema is official.

### 5.7 Tracking — **no webhook in official spec**

No callback/webhook path, signature, or replay contract appears in the OpenAPI.

| Method | Path | Official |
|--------|------|----------|
| GET | `/tracking/events/{parcel-no}` | Track by parcel id (`int64`) |
| GET | `/tracking/events/{courier}/{tracking-code}` | Track by courier + barcode |
| GET | `/tracking/report` | Status-change report (`from_date`, `to_date`). Response: array of `StatusChangeReport` |

**Karzar decision:** polling via `GET /tracking/events/{parcel-no}` (and barcode path when parcel id is missing). `GET /common/statuses` feeds the mapper. No webhook implementation (nothing to verify).

### 5.8 Out of Karzar v1 (documented but not implemented)

Wallet top-up / withdraw / cash-out, bank accounts, `POST /store/enroll`, `POST /user/access-token`, COD, Postex customer auth. Optional admin **read** of `GET /wallet/balance` only.

## 6. Request schemas used by Karzar

### 6.1 `ParcelPropertyDto` (required)

`length`, `width`, `height` (cm int), `total_weight` (g int), `total_value` (Rial number), `box_type_id` (int). Optional: `is_fragile`, `is_liquid`, `pre_paid_amount`, `total_value_currency`.

### 6.2 `ParcelLocationDto`

Required `contact` (`ContactDto`: `first_name`, `last_name`, `mobile_no`; optional telephone, email, `company_name`, `national_code`) and `location` (`LocationDto`: required `address`, `city_id`; optional `post_code`, `country`, `city_name`, `lat`, `lon` as **strings**).

### 6.3 `OptionalServices`

`request_label`, `request_packaging`, `request_sms_notification` (booleans). Official schema has **no** insurance field (plugin sends extra keys — ignored).

### 6.4 `UpdateParcelRequest`

Required `to` (`To`: contact required; location optional with address+post_code only), `parcel_items`, `parcel_properties`. Optional `request_label`.

### 6.5 `StatusChangeReport` (the only tracking event schema)

`order_no`, `tracking_no`, `change_status_date`, `change_status_date_utc`, `change_status_time`, `change_status_time_utc`, `event_code`, `event_name`, `event_desc`, `custom_order_no`, `custom_reference_no`.

## 7. Error contract

| Item | Official |
|-------|----------|
| Shared error object | `ApiResult`: `isSuccess` boolean, `message` string nullable |
| Documented on | Wallet balance/top-up **400** and **401** only |
| Other operations | Response bodies **not** specified |
| Rate limits | **Not documented** |
| Idempotency | **Not documented** |

Karzar client also accepts PascalCase `IsSuccess` / `Message` if returned. Non-JSON bodies are not dumped; HTTP status is preserved.

## 8. Retry / ambiguous write (mandatory)

1. **GET / quotes:** bounded retry on timeout / 5xx / network.
2. **POST /parcels/bulk, mark-ready, cancel, PATCH/PUT, wallet writes:** no generic automatic retry.
3. If create returns a **definitive** 4xx validation/`isSuccess=false` before a parcel exists: record failure; safe to retry later.
4. **Durable create attempt (crash-safety):** before any `POST /parcels/bulk`, Karzar commits a `booking` row (`create_attempted`, attempt counter). A flush is not durable. The `SELECT FOR UPDATE` is released before the network call. On process restart, `booking` / `creation_uncertain` **never** blindly POST create; they `GET /parcels/custom-order-no/{custom_order_no}` first. Retry create only after **two** empty lookups. Local `cancelled` without a Postex cancel-request is allowed only for `pending_booking` that has **never** started a create. `booking` / `creation_uncertain` / any attempted-create state must lookup first; a found parcel is persisted and `POST /parcels/cancel-request/{parcel-no}` is issued (`cancellation_pending`, never a false local `cancelled`).
5. If create **times out**, the TCP session resets, the remote protocol disconnects, a read fails after the body was sent, or an equivalent HTTPX transport error occurs, **or** a mutating call returns HTTP 5xx: the client cannot prove Postex did not receive the write. Mark shipment `creation_uncertain`. **Do not** POST bulk again. Reconcile with `GET /parcels/custom-order-no/{custom_order_no}`. Retry create only after **two** empty lookups. Definitive 4xx validation remains a local `error` (safe to retry create after correction).
6. 404 on lookup after timeout: still `creation_uncertain` until a later poll also 404s **and** a documented empty result is observed (timeout may mean create succeeded but lookup lagged). Karzar waits a bounded backoff before treating 404 as “no parcel” for automatic retry.

## 9. Webhooks vs polling

**No webhook/callback** in the official spec. Karzar uses DB-backed polling of official tracking endpoints.

## 10. Known cross-checks vs official spec

| Claim | Official |
|-------|----------|
| Base `https://api.postex.ir/api/v1` | Consistent with path prefix; no `servers` block |
| Header `x-api-key` | **Confirmed** in `info.description` |
| `GET /user/whoami` | **Confirmed** |
| `POST /shipping/quotes` | **Confirmed** |
| `GET /common/boxes` | **Confirmed** |
| `GET /locality/cities/all` | **Confirmed** |
| `GET /shipping-methods` | **Confirmed** |
| `GET /common/payment-methods` | **Confirmed** |
| `POST /parcels/bulk` | **Confirmed** |
| `GET /parcels/{tracking_code}/label` | **Not official.** Official is `GET /parcels/{parcel-no}/label` |

## 11. Ambiguities / missing documentation (blockers isolated)

| Gap | Karzar handling |
|------|-----------------|
| Quote response schema & currency | Persist raw + treat amounts as IRR pending Owner live quote confirmation |
| Parcel create response schema | Persist redacted raw; map barcode/parcel_no if present |
| Label content-type | Expect PDF; fail clearly otherwise |
| Status vocabulary values | Live `GET /common/statuses` + conservative mapper; never invent delivered |
| Edit/cancel cutoff | Not documented — provider error is returned honestly |
| Time windows body | Not implemented |
| Rate limits | None assumed |
| Box object fields | Not in OpenAPI — parse `id` + dimension-like keys from live/fixture JSON |
| City object fields | Not in OpenAPI — parse `id`/`code` + `name` |

Do **not** invent endpoints for missing operations.
