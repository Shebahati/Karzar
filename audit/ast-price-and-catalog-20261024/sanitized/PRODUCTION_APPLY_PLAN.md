# Production APPLY plan

1. Owner accepts `AST_COOPERATION_LIST_RIAL_DIV_10` in COMMERCIAL_PRICING_DECISION.md.
2. Resolve HOLD / ABNORMAL_UPDATE_REVIEW rows (large-swing and duplicate-SKU collisions stay out of UPDATE; see `ABNORMAL_UPDATE_REVIEW.csv` for current count).
3. Per-row CREATE QA: set `approval_status=OWNER_APPROVED_FOR_APPLY` only on validated CREATE manifest rows.
4. Backup production DB.
5. Fresh catalog snapshot + stale-state check (UPDATE `expected_current_price` / SKU guards).
6. Dry-run: `python scripts/ops/ast_price_catalog_apply_once.py` (default; no DB write).
7. UPDATE canary → post-commit verify → CREATE canary → verify.
8. Full cohort APPLY (single transaction journal): `ast_price_catalog_apply_once.py --apply` with Category B env +
   manifest SHA/count confirmations. CLI returns `APPLIED` only after real UPDATE/CREATE execution and post-verify.
9. Post-verify API + storefront.

**Rollback (committed journal only):** `ast_price_catalog_apply_once.py --rollback --rollback-journal audit/.../journals/AST_APPLY_<batch>.json`
— UPDATE rollback only when current price still equals the applied price; CREATE rollback soft-deletes exact journal IDs
with no `order_items` activity.

**Authorization tokens:** `AUTHORIZE_AST_PRICE_CATALOG_APPLY` / `AUTHORIZE_AST_PRICE_CATALOG_ROLLBACK`

**Manifest SHA256**
- UPDATE: `ba2eb3784f7b2026fc7c72a0cbc9260fa4484ec60de6af87cc8cc58720dcb891`
- CREATE: `MANIFEST_ABSENT`
- LEDGER: `353ffebe948ed8c6e60db1cc9447805a2967af0b3b3cfb8b829a491be80d7003`
