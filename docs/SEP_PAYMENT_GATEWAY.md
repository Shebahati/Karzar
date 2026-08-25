# SEP (Saman Kish) OnlinePG — Karzar

Production-grade integration notes for `PAYMENT_PROVIDER=sep`.
Authority for protocol fields: official technical document **v3.6** (مستند فنی نسخه 3.6).

## Architecture

```text
Storefront → FastAPI init (Token) → Customer → sep.shaparak.ir SendToken
SEP POST form → FastAPI /api/v1/payments/callback/sep
  → validate → reserve RefNum (DB) → VerifyTransaction
  → 303 → Storefront success | verifying | failed
```

Callback **must** hit the API host, not Next.js:

`https://api.karzartools.com/api/v1/payments/callback/sep`

## Environment

| Variable | Default / notes |
|----------|-----------------|
| `PAYMENT_PROVIDER` | `sep` |
| `PAYMENT_CALLBACK_URL` | Backend SEP callback URL |
| `SEP_TERMINAL_ID` | Required in production; never commit |
| `SEP_TOKEN_URL` | `https://sep.shaparak.ir/OnlinePG/OnlinePG` |
| `SEP_SEND_TOKEN_URL` | `https://sep.shaparak.ir/OnlinePG/SendToken` |
| `SEP_VERIFY_URL` | `…/VerifyTransaction` (see spelling conflict) |
| `SEP_REVERSE_URL` | `…/ReverseTransaction` |
| `SEP_TOKEN_EXPIRY_MINUTES` | `30` (range 20–3600) |
| `SEP_VERIFY_DEADLINE_MINUTES` | `30` |
| `SEP_VERIFY_RETRY_INTERVAL_SECONDS` | Worker poll interval |

Production refuses `PAYMENT_PROVIDER=sep` without `SEP_TERMINAL_ID`.
SEP URLs must be HTTPS on host `sep.shaparak.ir` (localhost override only in development).

### Production sample (no secrets)

```env
PAYMENT_PROVIDER=sep
PAYMENT_CALLBACK_URL=https://api.karzartools.com/api/v1/payments/callback/sep
PAYMENT_SUCCESS_REDIRECT_URL=https://www.karzartools.com/checkout/success
PAYMENT_FAILURE_REDIRECT_URL=https://www.karzartools.com/checkout/payment/failed
PAYMENT_TIMEOUT_SECONDS=12
SEP_TERMINAL_ID=
SEP_TOKEN_URL=https://sep.shaparak.ir/OnlinePG/OnlinePG
SEP_SEND_TOKEN_URL=https://sep.shaparak.ir/OnlinePG/SendToken
SEP_VERIFY_URL=https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/VerifyTransaction
SEP_REVERSE_URL=https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/ReverseTransaction
SEP_TOKEN_EXPIRY_MINUTES=30
```

## Token request

`POST` JSON to `SEP_TOKEN_URL` with `Action=Token`, `TerminalId`, `Amount` (rials from order snapshot),
`ResNum=order.tracking_code`, `RedirectUrl=callback`, optional normalized `CellNumber`, `TokenExpiryInMin`.

Success: `status == 1` and non-empty token → stored in `orders.payment_authority`.
TLS verification always on. Do not log full tokens.

## Callback fields

Form POST fields include `Token`, `ResNum`, `RefNum`, `State`, `Status`, `TerminalId`, `MID`,
`TraceNo`, `RRN`/`Rrn`, `Amount`, masked pan fields. Full PAN is never stored.
Success gate before Verify: `State=OK` (uppercase) and `Status=2`.

## Verify logic

Only after callback validation:

- `Success` true **and** `ResultCode == 0` (not `> 0`)
- Response `RefNum` / `TerminalNumber` / `OrginalAmount` (typo key; fallback `OriginalAmount`) /
  `AffectiveAmount` match order
- Then mark `paid` and best-effort Hesabfa invoice

### Endpoint spelling conflict

Official packages disagree:

- PDF + Python samples: `VerifyTransaction` / `ReverseTransaction`
- Postman / some ASP samples: `VerifyTranscation` / `ReverseTranscation`

Defaults use the PDF spelling. URLs remain configurable. **No automatic fallback** between
spellings (avoids duplicate monetary Verify). Confirm the live path with SEP when activating the terminal.

## Timeout and retry

Verify timeout does **not** mark the order failed. Status stays `verifying` with
`payment_next_verify_at` / `payment_verify_deadline`. A DB-backed worker in FastAPI lifespan
(with Redis distributed lock when available) retries with backoff 5→15→30→60s until deadline,
then `reconciliation_required`. Order expiry only cancels `payment_status=unpaid`.

## Double-spend protection

- Unique partial index `uq_orders_payment_ref_id_not_null` on `orders.payment_ref_id`
- Reserve RefNum in a short DB transaction before Verify
- Same RefNum on paid order → idempotent success
- RefNum bound to another order → security reject
- IntegrityError on race → controlled failure redirect (no raw 500)

## Reverse vs refund

SEP Reverse is a time-boxed correction (~50 minutes), not a general refund API.
`POST /payments/refund` returns a controlled unsupported error for `sep`.
Automatic Reverse is only used for safety paths such as amount mismatch; never treat a Reverse
request alone as settled refund without ledger evidence.

## IP whitelist

SEP must whitelist the **egress IP** of the API VPS that calls Token/Verify (NAT egress if any).
Cloudflare/edge ingress IP is irrelevant. Callback must accept public HTTPS Form POST.

## Deployment checklist

1. DB backup
2. Run Alembic migration `g8h9i0j1k2l3`
3. Set secrets on VPS only (`SEP_TERMINAL_ID`, callback URLs)
4. Confirm SEP IP + callback + Verify path spelling
5. Deploy API + Storefront
6. Health/readiness
7. Smoke without real payment
8. Real payment only with explicit owner approval
9. Check `payment_transactions` ledger + SEP report portal
10. Rollback plan ready

## Manual test checklist (after Terminal issued)

1. HTTPS callback reachable
2. IP whitelist confirmed
3. Token with controlled amount
4. Browser redirect to SEP
5. User cancel → failed ledger
6. Low-amount pay with owner approval
7. Callback + Verify + amount match
8. Order paid + Admin visibility
9. Hesabfa only after paid
10. Duplicate callback idempotent
11. `report.sep.ir` reconciliation
12. Logs contain no full token / full PAN

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Token reject | Terminal ID, egress IP, amount in rials |
| Callback 405 | Must be POST; no trailing-slash redirect |
| Stuck verifying | Worker logs, Redis lock, deadline columns |
| Amount mismatch | Ledger `reconciliation_required`, Reverse attempt |
| Open redirect | Redirect bases only from settings |

## Reconciliation

Orders with `payment_status=reconciliation_required` need manual review against SEP reports
(`report.sep.ir`). Do not mark paid from Admin without gateway evidence.

## Card data policy

Never store or log full PAN, CVV2, PIN, or raw callback bodies containing secrets.
Masked `SecurePan` / hashed pan only when needed for audit.
