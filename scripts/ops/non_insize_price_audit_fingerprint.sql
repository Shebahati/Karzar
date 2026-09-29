-- Read-only catalog fingerprint. No writes.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT current_setting('transaction_read_only') AS transaction_read_only;
SELECT md5(coalesce(string_agg(
  id::text || ':' ||
  coalesce(base_price::text, '') || ':' ||
  coalesce(original_price::text, '') || ':' ||
  coalesce(brand_id::text, '') || ':' ||
  is_active::text || ':' ||
  is_available::text || ':' ||
  stock_quantity::text || ':' ||
  coalesce(deleted_at::text, ''),
  ',' ORDER BY id
), '')) AS catalog_fingerprint
FROM products;
ROLLBACK;
