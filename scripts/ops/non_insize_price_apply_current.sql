-- Read-only post-commit target and INSIZE prices. No writes.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT '---CURRENT---';
SELECT json_build_object(
  'product_id', p.id,
  'base_price', p.base_price::text,
  'original_price', p.original_price::text
)::text
FROM products p
WHERE p.deleted_at IS NULL
  AND (p.brand_id IS NULL OR p.brand_id <> 3)
  AND p.base_price IS NOT NULL
  AND p.base_price > 0
ORDER BY p.id;
SELECT '---INSIZE---';
SELECT json_build_object(
  'product_id', p.id,
  'base_price', p.base_price::text,
  'original_price', p.original_price::text
)::text
FROM products p
WHERE p.deleted_at IS NULL AND p.brand_id = 3
ORDER BY p.id;
SELECT '---END---';
ROLLBACK;
