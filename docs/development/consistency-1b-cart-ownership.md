# Consistency 1B — cart ownership / guest merge (implementation note)

Non-binding evidence for audit finding F03 only. Does not change Accepted Canon.

## Persisted cart ownership model

- Key: `karzar.storefront.cart` (Zustand persist **version 2**).
- Persisted slice: `{ stash: { attribution, cart, quote } | null }`.
- Visible `cart` / `quote` are publication surfaces (memory); they are **not** the sole persist envelope.
- Attribution is explicit:
  - `{ kind: "guest", guestToken }` — lines belong to guest token G
  - `{ kind: "customer", customerId }` — lines belong to verified customer A
- `"cart token exists"` is never treated as proof of guest provenance. Authenticated requests may still create a local token while the backend ignores `X-Cart-Token`.

## Migration (legacy)

- Legacy v1 `{ cart, quote }` with no owner is **discarded** (fail closed).
- Never adopted via customer hint, session cookie marker, or presence of a cart token.

## Guest → customer transfer

1. Capture guest stash attributed to G (must match the current guest token).
2. Authenticate verified customer A (`getVerifiedCustomerId()` / Consistency 1A fence).
3. `POST /cart/merge` with exact G.
4. Only local-only lines proven under G participate in transfer.
5. Active attribution becomes customer A; guest token cleared after successful merge.
6. Same-owner reconcile follows under A.

## Customer → customer switch (A → logout → B)

- Logout hides published lines; does **not** relabel A stash as guest.
- Logout issues **no** cart clear/remove/upsert.
- B login with foreign A stash uses **server-authoritative replace** (empty B server → empty UI).
- A local-only lines are never upserted into B.

## Same-owner reload

- Customer stash may publish only after verified owner matches attribution.
- While `/auth/me` is pending (`unknown` / `checking`), customer stash stays unpublished.
- Leftover cart tokens do not trigger guest `/cart/merge`.

## Failure behavior

- Failed guest merge keeps guest attribution; does not relabel lines as the customer.
- Late reconcile/upsert completion is fenced by verified owner + session generation (and guest token+generation for guest ops). Stale completions do not publish or upsert under a new owner.

## Explicit exclusions

- **F04** request ordering / mutation queues / optimistic concurrency — unchanged.
- **F06** profile persistence, **F07** refresh machine, **F08** authoritative logout — unchanged.
- No backend cart API/schema changes; authenticated identity still wins over `X-Cart-Token`.
