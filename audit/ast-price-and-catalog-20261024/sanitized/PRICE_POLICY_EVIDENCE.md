# AST price policy evidence

## Owner commercial approval

- **Status:** `OWNER_COMMERCIAL_PRICING_POLICY_APPROVED`
- **Policy ID:** `AST_COOPERATION_LIST_RIAL_DIV_10`
- **Formula:** `base_price = verified_pdf_rial / 10` (Toman, Decimal)
- **Scope:** One-time AST supplier archive SHA256 `976fca74faabd4fb62bb57feb396450717c32b660efa2200db0a94b032d55a8b` only.

## Cash discount handling

- Recorded in manifests as `cash_discount_percent` for procurement analysis.
- **Not** subtracted from customer `base_price`.
- **Not** applied as storefront promotion; **do not** modify `original_price`.
- Labels with device/spare split (`*_REVIEW`) set QA flag `QA_DEVICE_SPARE_DISCOUNT_SPLIT` only.

## Manifest fingerprints (post-approval regeneration)

- UPDATE: `ba2eb3784f7b2026fc7c72a0cbc9260fa4484ec60de6af87cc8cc58720dcb891`
- CREATE: `f2d3d55729b7ec6a65ab9770d5043ea6c7f3ca0cc999ceedc5c81ad4d83ca606`
- LEDGER: `ca33573626957f7f5b29c3b233fe344254d03d2d27738ba62e5b748974b42608`
