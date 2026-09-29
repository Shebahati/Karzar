-- Read-only fingerprints. No catalog writes.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT 'transaction_read_only=' || current_setting('transaction_read_only');
SELECT 'nonprice_fp=' || md5(coalesce(string_agg(
  id::text || '|' || is_active::text || '|' || is_available::text || '|' ||
  stock_quantity::text || '|' || coalesce(brand_id::text, '') || '|' ||
  category_id::text || '|' || sku || '|' || slug || '|' || name || '|' ||
  coalesce(deleted_at::text, '') || '|' || coalesce(product_type_id::text, ''),
  E'\n' ORDER BY id
), ''))
FROM products;
SELECT 'insize_price_fp=' || md5(coalesce(string_agg(
  id::text || '|' || coalesce(base_price::text, '') || '|' || coalesce(original_price::text, ''),
  E'\n' ORDER BY id
), ''))
FROM products
WHERE deleted_at IS NULL AND brand_id = 3;
SELECT 'nontarget_price_fp=' || md5(coalesce(string_agg(
  id::text || '|' || coalesce(base_price::text, '') || '|' || coalesce(original_price::text, ''),
  E'\n' ORDER BY id
), ''))
FROM products
WHERE NOT (
  deleted_at IS NULL
  AND (brand_id IS NULL OR brand_id <> 3)
  AND base_price IS NOT NULL
  AND base_price > 0
);
SELECT 'orders_fp=' || md5(coalesce(string_agg(
  id::text || '|' || coalesce(estimated_total::text, '') || '|' || status || '|' || payment_status,
  E'\n' ORDER BY id
), ''))
FROM orders;
SELECT 'order_items_fp=' || md5(coalesce(string_agg(
  id::text || '|' || coalesce(unit_price::text, '') || '|' || quantity::text,
  E'\n' ORDER BY id
), ''))
FROM order_items;
SELECT 'payments_fp=' || md5(coalesce(string_agg(
  id::text || '|' || amount::text || '|' || status,
  E'\n' ORDER BY id
), ''))
FROM payment_transactions;
ROLLBACK;
