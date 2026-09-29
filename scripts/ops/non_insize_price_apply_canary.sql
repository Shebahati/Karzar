-- Read-only canary rows. No writes.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT json_build_object(
  'product_id', id,
  'sku', sku,
  'brand_id', brand_id,
  'base_price', base_price::text,
  'label', 'brand'
)::text
FROM (
  SELECT id, sku, brand_id, base_price,
         row_number() OVER (PARTITION BY brand_id ORDER BY id) AS n
  FROM products
  WHERE deleted_at IS NULL
    AND brand_id IN (2, 4, 5, 8, 13, 20)
    AND is_active IS TRUE
    AND base_price > 0
) picked
WHERE n <= 5
ORDER BY brand_id, id;
SELECT json_build_object(
  'product_id', id,
  'sku', sku,
  'brand_id', brand_id,
  'base_price', base_price::text,
  'label', 'class_b'
)::text
FROM (
  SELECT id, sku, brand_id, base_price
  FROM products
  WHERE deleted_at IS NULL
    AND brand_id IS NULL
    AND base_price > 0
    AND original_price > base_price
  ORDER BY id
  LIMIT 1
) class_b;
ROLLBACK;
