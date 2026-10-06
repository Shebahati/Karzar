# FINAL REPORT — Product 1789 brand integrity

## Status

`READY_FOR_OWNER_REPAIR`

## Identity

| Field | Value |
| --- | --- |
| product_id | 1789 |
| sku | 1114-150 |
| manufacturer_code | 1114-150 |
| historical brand | 3 / INSIZE |
| current brand | NULL |
| expected brand | 3 / INSIZE |
| identity proof | PASS (live row + Wave0/Phase2C/INSIZE manifests + trailing-A identity-only) |

## Timeline

- Availability: actor 3 toggles 2026-10-04 11:11:45/48/50 (logged).
- Brand loss window: after 2026-10-03 brand=3 evidence; by Wave1A; correlated with 2026-10-04 `product_update` price writes; **exact clear time unproven**.
- Brand change-log rows: **0** (pre-rehearsal).

## Root cause

`ADMIN_PATH_DEFECT` — admin product update could mutate `brand_id` without `ProductChangeLog` (tracked_fields gap). Exact historical writer not proven.

## Writer audit

Unaudited brand-capable app path found and hardened. Scripts that PUT via API inherit the fix. Direct SQL remains unaudited by design.

## Systemic

| Class | Count |
| --- | ---: |
| live brandless | 296 |
| KNOWN_LEGITIMATE_BRANDLESS (also null in Wave0) | 295 |
| PROVEN_BRAND_LOSS | 1 (1789 only) |
| POTENTIAL_BRAND_LOSS | 0 |

No other rows repaired.

## Code hardening

- `app/services/product_service.py` — track+log `brand_id`
- `app/api/endpoints/products_admin.py` — pass actor
- `app/services/brand_service.py` — log brand-delete clears
- `tests/test_product_brand_change_audit.py` — 4 tests

## Repair manifest

- rows: 1
- SHA256: `c5c572b3aadc65ec13f0692e019c645a60cd4f09e87691ddf27da20b952821d8`
- expected_current_hash: `262b9c550257a32c248c650ab283c676e80e689eaa4d551dcd6afe3645f42555`

## Production rehearsal

| Check | Result |
| --- | --- |
| identity gate | PASS |
| transient product updates | 1 |
| transient audit rows | 1 |
| protected-field changes | 0 |
| rollback | YES |
| post brand_id NULL | YES |
| rehearsal logs absent | YES |
| persistent mutations | 0 |

## Safety

availability/price/activation/Hesabfa/deploy mutations: **NO**

```text
REAL_REPAIR_AUTHORIZED = NO
```
