# Consistency 1A — private account state (implementation note)

Non-binding evidence for audit findings F01/F02. Does not change Accepted Canon.

## Persistence

- Saved addresses: `localStorage` key `karzar.addresses`, Zustand persist **version 2**.
- Shape: `{ byOwner: Record<customerId, SavedAddress[]> }` — visible `addresses` are memory-only.
- Legacy v1 entries (`state.addresses` without `byOwner`) are **discarded** on migrate (no attributable owner). Users re-enter addresses once.

## Session boundary

- Module: `frontend/Storefront/src/lib/customer-session.ts`
- Verified owner + monotonic `generation` gate private reads, React Query keys, and address getters.
- Logout / 401 / account switch clears visible private state immediately; server HttpOnly session may remain (F08).

## Limitations (unchanged by this patch)

- Cart ownership (F03), server logout proof (F08), profile PATCH (F06), invoice snapshot rules remain separate.
