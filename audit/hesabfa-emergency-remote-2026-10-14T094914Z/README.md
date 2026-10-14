# Hesabfa emergency remote inventory (2026-10-14)

Read-only `item/getItems` snapshot from production API container before integration cutover.

- **TOTAL_REMOTE:** 3792 (pagination proven: fetched == TotalCount)
- **ACTIVE_BEFORE:** 1172
- **INACTIVE_BEFORE:** 2620
- **UNKNOWN_ACTIVE:** 0

Karzar API activation via `item/save` was **not** performed (`BLOCKED_SAFE_HESABFA_ACTIVATION_METHOD_NOT_PROVEN`).

Full `REMOTE_ITEMS.csv` and `INACTIVE_CODES.csv` (2620 codes) remain on VPS under
`/opt/karzar/logs/hesabfa-emergency-remote-2026-10-14T094914Z/`.
