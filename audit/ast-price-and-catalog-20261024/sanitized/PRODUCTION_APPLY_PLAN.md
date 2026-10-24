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
- UPDATE: `956cadc7bd6b29f81dcc360455d8c635b6d84d8f46ce63b0c1ec7e121b2eb428`
- CREATE: `59fb155de7b2f3a2620cf8d445088982a213fb1321cf79004e777daebdb88619`
- LEDGER: `98908e4bf0f070b84dafce77f0319b30400adfc06e8330b2c677394e4a264c5b`
