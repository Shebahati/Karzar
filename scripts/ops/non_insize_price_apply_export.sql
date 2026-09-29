-- Read-only snapshot for the non-INSIZE +20% manifest. No writes.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT 'transaction_read_only=' || current_setting('transaction_read_only');
SELECT 'database_name=' || current_database();
SELECT 'insize_candidates=' || count(*)::text
FROM brands
WHERE regexp_replace(lower(name), '[^[:alnum:]]', '', 'g') = 'insize'
   OR regexp_replace(lower(slug), '[^[:alnum:]]', '', 'g') = 'insize'
   OR lower(name) LIKE '%insize%'
   OR lower(slug) LIKE '%insize%'
   OR lower(name) LIKE '%in-size%'
   OR lower(slug) LIKE '%in-size%'
   OR lower(name) LIKE '%in size%'
   OR lower(slug) LIKE '%in size%'
   OR replace(name, chr(8204), '') LIKE '%اینسایز%'
   OR replace(slug, chr(8204), '') LIKE '%اینسایز%'
   OR replace(name, chr(8204), '') LIKE '%این سایز%'
   OR replace(slug, chr(8204), '') LIKE '%این سایز%';
SELECT 'insize_id=' || id::text FROM brands WHERE id = 3;
SELECT 'insize_name=' || name FROM brands WHERE id = 3;
SELECT 'insize_slug=' || slug FROM brands WHERE id = 3;
SELECT 'insize_live=' || count(*)::text FROM products WHERE deleted_at IS NULL AND brand_id = 3;
SELECT 'insize_priced=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND brand_id = 3 AND base_price > 0;
SELECT 'target_count=' || count(*)::text
FROM products
WHERE deleted_at IS NULL
  AND (brand_id IS NULL OR brand_id <> 3)
  AND base_price IS NOT NULL
  AND base_price > 0;
SELECT 'class_a=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND (brand_id IS NULL OR brand_id <> 3)
  AND base_price > 0 AND original_price IS NULL;
SELECT 'class_b=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND (brand_id IS NULL OR brand_id <> 3)
  AND base_price > 0 AND original_price > base_price;
SELECT 'class_c=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND (brand_id IS NULL OR brand_id <> 3)
  AND base_price > 0 AND original_price = base_price;
SELECT 'class_d=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND (brand_id IS NULL OR brand_id <> 3)
  AND base_price > 0 AND original_price < base_price;
SELECT 'class_f=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND (brand_id IS NULL OR brand_id <> 3)
  AND base_price <= 0;
SELECT 'fractional_raw=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND (brand_id IS NULL OR brand_id <> 3)
  AND base_price > 0
  AND (base_price * numeric '1.20') <> trunc(base_price * numeric '1.20');
SELECT 'change_log_reason_rows=' || count(*)::text
FROM product_change_logs
WHERE reason = 'owner_non_insize_price_increase_20pct_2026_09_29';
SELECT 'target_mapped=' || count(*)::text
FROM products p
JOIN hesabfa_item_mappings m ON m.product_id = p.id
WHERE p.deleted_at IS NULL AND (p.brand_id IS NULL OR p.brand_id <> 3)
  AND p.base_price > 0;
SELECT 'target_unmapped=' || count(*)::text
FROM products p
LEFT JOIN hesabfa_item_mappings m ON m.product_id = p.id
WHERE p.deleted_at IS NULL AND (p.brand_id IS NULL OR p.brand_id <> 3)
  AND p.base_price > 0 AND m.id IS NULL;
SELECT 'product_triggers=' || coalesce(string_agg(tg.tgname, ',' ORDER BY tg.tgname), 'NONE')
FROM pg_trigger tg
JOIN pg_class c ON c.oid = tg.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname = 'products' AND NOT tg.tgisinternal;
SELECT '---MANIFEST---';
SELECT json_build_object(
  'product_id', p.id,
  'sku', p.sku,
  'brand_id', p.brand_id,
  'brand_name', b.name,
  'deleted_at', p.deleted_at,
  'old_base_price', p.base_price::text,
  'new_base_price', round(p.base_price * numeric '1.20', 0)::text,
  'old_original_price', p.original_price::text,
  'new_original_price', CASE
    WHEN p.original_price IS NULL THEN NULL
    WHEN p.original_price > p.base_price THEN round(p.original_price * numeric '1.20', 0)::text
    ELSE NULL
  END,
  'price_class', CASE
    WHEN p.original_price IS NULL THEN 'A'
    WHEN p.original_price > p.base_price THEN 'B'
    WHEN p.original_price = p.base_price THEN 'C'
    WHEN p.original_price < p.base_price THEN 'D'
    ELSE 'F'
  END
)::text
FROM products p
LEFT JOIN brands b ON b.id = p.brand_id
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
