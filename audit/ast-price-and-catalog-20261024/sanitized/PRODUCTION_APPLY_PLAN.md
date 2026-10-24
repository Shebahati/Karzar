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
- CREATE: `702b2ec9b5c0ef93e8d788066b7c28b329d01932cb313b5338351da9462a6882`
- LEDGER: `ea28ce9ba1b5a6321b63574af989c6f19897c31c33ab7227e702e1747a92d91a`
