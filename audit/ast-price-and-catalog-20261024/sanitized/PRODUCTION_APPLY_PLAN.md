# Production APPLY plan

1. Owner accepts `AST_COOPERATION_LIST_RIAL_DIV_10` in COMMERCIAL_PRICING_DECISION.md.
2. Resolve HOLD / ABNORMAL_UPDATE_REVIEW rows.
3. Backup production DB.
4. Fresh snapshot + drift check.
5. Dry-run apply CLI.
6. UPDATE canary → verify → CREATE canary → verify.
7. Full cohort apply with journal.
8. Post-verify API + storefront.

**Authorization tokens:** `AUTHORIZE_AST_PRICE_CATALOG_APPLY` / `AUTHORIZE_AST_PRICE_CATALOG_ROLLBACK`

**Manifest SHA256**
- UPDATE: `ba2eb3784f7b2026fc7c72a0cbc9260fa4484ec60de6af87cc8cc58720dcb891`
- CREATE: `f2d3d55729b7ec6a65ab9770d5043ea6c7f3ca0cc999ceedc5c81ad4d83ca606`
- LEDGER: `ca33573626957f7f5b29c3b233fe344254d03d2d27738ba62e5b748974b42608`
