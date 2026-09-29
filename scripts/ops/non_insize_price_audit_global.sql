-- Read-only global product census. No writes.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT 'transaction_read_only=' || current_setting('transaction_read_only');
SELECT 'database_name=' || current_database();
SELECT 'live_products=' || count(*)::text FROM products WHERE deleted_at IS NULL;
SELECT 'soft_deleted_products=' || count(*)::text FROM products WHERE deleted_at IS NOT NULL;
SELECT 'priced_live_products=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND base_price IS NOT NULL AND base_price > 0;
SELECT 'unpriced_live_products=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND base_price IS NULL;
SELECT 'zero_base_live_products=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND base_price = 0;
SELECT 'negative_base_live_products=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND base_price < 0;
SELECT 'product_triggers=' || coalesce(string_agg(tg.tgname, ',' ORDER BY tg.tgname), 'NONE')
FROM pg_trigger tg
JOIN pg_class c ON c.oid = tg.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relname = 'products'
  AND NOT tg.tgisinternal;
ROLLBACK;
