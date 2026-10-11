# SEP operator refund runbook

Karzar staging/production may use `PAYMENT_PROVIDER=sep`. This runbook is for **SuperAdmin** operators reconciling paid orders after money has already moved outside Karzar.

## Principles

1. Karzar does **not** initiate a general SEP refund through Admin «استرداد وجه و لغو» when capabilities show `refund_mode=external_confirmation`.
2. SEP **ReverseTransaction** is a safety/reconciliation tool, not a general customer refund API. Do not treat it as the normal refund path.
3. The operator performs the actual refund through the authoritative SEP/bank channel (terminal back-office, bank dispute desk, or other official channel).
4. Before recording anything in Karzar, verify **amount**, **order/tracking code**, and **RefNum** (or equivalent) in that external channel.
5. Obtain an **external refund reference** or documentary evidence from the channel (max **64** characters — matches `orders.payment_refund_id`).
6. Only after **confirmed money movement** use Admin: **ثبت استرداد انجام‌شده و لغو سفارش** (`POST /api/v1/payments/refund/external-confirmation` with step-up).
7. Never record a refund merely because a form was submitted; the external channel must already show success.
8. In Karzar, confirm `payment_status=refunded` and `payment_refund_id` matches your external reference.
9. Confirm the order `status=cancelled`.
10. Confirm exactly **one** `RETURN` stock movement for the order (one prior `SALE`, one `RETURN`).
11. If Karzar shows `payment_status=refunded` but the order is **not** cancelled (`reconciliation_required=true` in the API response), escalate to engineering/ops — do **not** submit a second external reference.
12. Never repeat external confirmation with a **different** reference for the same order; conflicting replays are rejected with HTTP 409.

## Shipping quiescence before external refund

Do **not** perform the authoritative SEP/bank refund while Karzar may still be creating or reconciling a Postex parcel for the order. Karzar rejects external refund confirmation (HTTP 409) when any shipment is in an unresolved provider-create window (for example `booking`, `creation_uncertain`, or durable `create_attempted` without a parcel id).

Recommended operator order:

1. Inspect current shipment/fulfillment state in Admin (Postex automation, manual portal, or manual carrier).
2. Ensure no provider create is in `booking` / `creation_uncertain` (or equivalent unresolved create state).
3. Stop or cancel forward fulfillment where applicable; wait for booking/reconciliation to finish or cancel the shipment.
4. Only then perform the authoritative SEP/bank refund.
5. Obtain external refund evidence (reference, amount, RefNum).
6. Record external confirmation in Karzar (`POST /api/v1/payments/refund/external-confirmation` with step-up).
7. Verify `payment_status=refunded`.
8. Verify order `status=cancelled` (or follow reconciliation if cancellation is pending).

## Acceptance example (placeholder only)

Order **29** (`KZ-3904296707BC`) illustrates a live paid SEP order in acceptance notes. **Do not** mutate order 29 during drills; use test orders in non-production environments.

## Related docs

- [`SEP_PAYMENT_GATEWAY.md`](SEP_PAYMENT_GATEWAY.md) — gateway integration and Reverse semantics.
- `GET /api/v1/payments/capabilities` — authoritative `refund_mode` for Admin UI.
