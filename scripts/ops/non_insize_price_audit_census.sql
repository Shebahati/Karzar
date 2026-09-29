-- Read-only non-INSIZE price census. Brand id is supplied by the caller.
-- No writes.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT 'transaction_read_only=' || current_setting('transaction_read_only');
SELECT 'insize_row=' || json_build_object('id', id, 'name', name, 'slug', slug)::text
FROM brands
WHERE id = :insize_id;

SELECT 'insize_live=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND brand_id = :insize_id;
SELECT 'insize_priced=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND brand_id = :insize_id AND base_price > 0;
SELECT 'insize_unpriced=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND brand_id = :insize_id AND base_price IS NULL;
SELECT 'insize_zero_base=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND brand_id = :insize_id AND base_price = 0;
SELECT 'insize_negative_base=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND brand_id = :insize_id AND base_price < 0;
SELECT 'insize_active=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND brand_id = :insize_id AND is_active IS TRUE;
SELECT 'insize_inactive=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND brand_id = :insize_id AND is_active IS FALSE;
SELECT 'insize_available_flag=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND brand_id = :insize_id AND is_available IS TRUE;
SELECT 'insize_unavailable_flag=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND brand_id = :insize_id AND is_available IS FALSE;
SELECT 'insize_active_and_available=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id = :insize_id AND is_active IS TRUE AND is_available IS TRUE;

SELECT 'non_insize_live=' || count(*)::text
FROM products WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id;
SELECT 'non_insize_priced=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price > 0;
SELECT 'non_insize_unpriced=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price IS NULL;
SELECT 'non_insize_zero_base=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price = 0;
SELECT 'non_insize_negative_base=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price < 0;
SELECT 'non_insize_active=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND is_active IS TRUE;
SELECT 'non_insize_inactive=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND is_active IS FALSE;
SELECT 'non_insize_available_flag=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND is_available IS TRUE;
SELECT 'non_insize_unavailable_flag=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND is_available IS FALSE;
SELECT 'non_insize_active_and_available=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND is_active IS TRUE AND is_available IS TRUE;
SELECT 'non_insize_brandless=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS NULL;
SELECT 'non_insize_brandless_priced=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS NULL AND base_price > 0;

SELECT 'class_a=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price IS NULL;
SELECT 'class_b=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price > base_price;
SELECT 'class_c=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price = base_price;
SELECT 'class_d=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price < base_price;
SELECT 'class_e=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price IS NULL;
SELECT 'class_f=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price <= 0;
SELECT 'target_count=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0;

SELECT 'class_b_count=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price > base_price;
SELECT 'class_b_min_discount=' || coalesce(min((1 - (base_price / original_price)) * 100)::text, 'NONE')
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price > base_price;
SELECT 'class_b_max_discount=' || coalesce(max((1 - (base_price / original_price)) * 100)::text, 'NONE')
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price > base_price;
SELECT 'class_b_ratio_drift=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price > base_price
  AND (base_price / original_price) IS DISTINCT FROM ((base_price * 1.20) / (original_price * 1.20));
SELECT 'class_b_displayed_int_drift=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price > base_price
  AND round((1 - (base_price / original_price)) * 100)::int
      IS DISTINCT FROM round((1 - ((base_price * 1.20) / (original_price * 1.20))) * 100)::int;
SELECT 'class_b_half_percent_boundary=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price > base_price
  AND abs(((1 - (base_price / original_price)) * 100)
      - trunc((1 - (base_price / original_price)) * 100)) = 0.5;
SELECT 'class_b_int_toman_round_drift=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price > base_price
  AND round(original_price * 1.20, 0) > 0
  AND round((1 - (base_price / original_price)) * 100)::int
      IS DISTINCT FROM round((1 - (round(base_price * 1.20, 0) / round(original_price * 1.20, 0))) * 100)::int;
SELECT 'class_b_1000_toman_round_drift=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price > base_price
  AND round(original_price * 1.20 / 1000, 0) * 1000 > 0
  AND round((1 - (base_price / original_price)) * 100)::int
      IS DISTINCT FROM round((1 - (
        (round(base_price * 1.20 / 1000, 0) * 1000)
        / (round(original_price * 1.20 / 1000, 0) * 1000)
      )) * 100)::int;

SELECT 'base_multiple_1_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price > 0
  AND (base_price * 10) = trunc(base_price * 10);
SELECT 'base_multiple_10_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price > 0
  AND base_price = trunc(base_price);
SELECT 'base_multiple_100_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price > 0
  AND mod(base_price, 10) = 0;
SELECT 'base_multiple_1000_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price > 0
  AND mod(base_price, 100) = 0;
SELECT 'base_multiple_10000_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price > 0
  AND mod(base_price, 1000) = 0;
SELECT 'base_multiple_100000_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price > 0
  AND mod(base_price, 10000) = 0;
SELECT 'base_fractional_toman=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price > 0
  AND base_price <> trunc(base_price);

SELECT 'original_present=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price IS NOT NULL;
SELECT 'original_multiple_1_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price IS NOT NULL
  AND (original_price * 10) = trunc(original_price * 10);
SELECT 'original_multiple_10_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price IS NOT NULL
  AND original_price = trunc(original_price);
SELECT 'original_multiple_100_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price IS NOT NULL
  AND mod(original_price, 10) = 0;
SELECT 'original_multiple_1000_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price IS NOT NULL
  AND mod(original_price, 100) = 0;
SELECT 'original_multiple_10000_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price IS NOT NULL
  AND mod(original_price, 1000) = 0;
SELECT 'original_multiple_100000_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price IS NOT NULL
  AND mod(original_price, 10000) = 0;

SELECT 'raw_base_fractional_toman=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price > 0
  AND (base_price * 1.20) <> trunc(base_price * 1.20);
SELECT 'raw_base_fractional_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price > 0
  AND (base_price * 12) <> trunc(base_price * 12);
SELECT 'raw_base_not_multiple_1000_toman=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price > 0
  AND mod(base_price * 1.20, 1000) <> 0;
SELECT 'raw_base_not_multiple_10000_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id AND base_price > 0
  AND mod(base_price * 1.20, 1000) <> 0;
SELECT 'raw_original_fractional_toman=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price IS NOT NULL
  AND (original_price * 1.20) <> trunc(original_price * 1.20);
SELECT 'raw_original_fractional_irr=' || count(*)::text
FROM products
WHERE deleted_at IS NULL AND brand_id IS DISTINCT FROM :insize_id
  AND base_price > 0 AND original_price IS NOT NULL
  AND (original_price * 12) <> trunc(original_price * 12);

SELECT 'target_with_hesabfa_mapping=' || count(*)::text
FROM products p
JOIN hesabfa_item_mappings m ON m.product_id = p.id
WHERE p.deleted_at IS NULL AND p.brand_id IS DISTINCT FROM :insize_id AND p.base_price > 0;
SELECT 'target_without_hesabfa_mapping=' || count(*)::text
FROM products p
LEFT JOIN hesabfa_item_mappings m ON m.product_id = p.id
WHERE p.deleted_at IS NULL AND p.brand_id IS DISTINCT FROM :insize_id AND p.base_price > 0
  AND m.id IS NULL;
SELECT 'insize_with_hesabfa_mapping=' || count(*)::text
FROM products p
JOIN hesabfa_item_mappings m ON m.product_id = p.id
WHERE p.deleted_at IS NULL AND p.brand_id = :insize_id;
SELECT 'name_looks_insize_other_brand=' || count(*)::text
FROM products p
WHERE p.deleted_at IS NULL
  AND p.brand_id IS DISTINCT FROM :insize_id
  AND (
    lower(p.name) LIKE '%insize%'
    OR lower(p.sku) LIKE '%insize%'
    OR replace(p.name, chr(8204), '') LIKE '%اینسایز%'
    OR replace(p.sku, chr(8204), '') LIKE '%اینسایز%'
  );

SELECT '=== BRAND_BREAKDOWN ===';
SELECT json_build_object(
  'brand_id', CASE WHEN p.brand_id IS NULL THEN 'BRANDLESS' ELSE p.brand_id::text END,
  'brand_name', CASE WHEN p.brand_id IS NULL THEN 'BRANDLESS' ELSE b.name END,
  'live_product_count', count(*),
  'priced_candidate_count', count(*) FILTER (WHERE p.base_price > 0),
  'sum_old_base_price', coalesce(sum(p.base_price) FILTER (WHERE p.base_price > 0), 0),
  'sum_projected_raw_base_price', coalesce(sum(p.base_price * 1.20) FILTER (WHERE p.base_price > 0), 0)
)::text
FROM products p
LEFT JOIN brands b ON b.id = p.brand_id
WHERE p.deleted_at IS NULL
  AND p.brand_id IS DISTINCT FROM :insize_id
GROUP BY p.brand_id, b.name
ORDER BY count(*) FILTER (WHERE p.base_price > 0) DESC, p.brand_id NULLS FIRST;

SELECT '=== SAMPLE lowest ===';
SELECT coalesce(json_agg(s)::text, '[]')
FROM (
  SELECT json_build_object(
    'product_id', p.id,
    'sku', p.sku,
    'brand', b.name,
    'name', p.name,
    'is_active', p.is_active,
    'is_available', p.is_available,
    'old_base_price', p.base_price,
    'old_original_price', p.original_price,
    'raw_new_base_price', p.base_price * 1.20,
    'raw_new_original_price', CASE WHEN p.original_price IS NULL THEN NULL ELSE p.original_price * 1.20 END,
    'old_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - (p.base_price / p.original_price)) * 100, 6) ELSE NULL END,
    'projected_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - ((p.base_price * 1.20) / (p.original_price * 1.20))) * 100, 6) ELSE NULL END
  ) AS s
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  WHERE p.deleted_at IS NULL AND p.brand_id IS DISTINCT FROM :insize_id AND p.base_price > 0
  ORDER BY p.base_price ASC, p.id ASC
  LIMIT 5
) q;

SELECT '=== SAMPLE highest ===';
SELECT coalesce(json_agg(s)::text, '[]')
FROM (
  SELECT json_build_object(
    'product_id', p.id,
    'sku', p.sku,
    'brand', b.name,
    'name', p.name,
    'is_active', p.is_active,
    'is_available', p.is_available,
    'old_base_price', p.base_price,
    'old_original_price', p.original_price,
    'raw_new_base_price', p.base_price * 1.20,
    'raw_new_original_price', CASE WHEN p.original_price IS NULL THEN NULL ELSE p.original_price * 1.20 END,
    'old_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - (p.base_price / p.original_price)) * 100, 6) ELSE NULL END,
    'projected_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - ((p.base_price * 1.20) / (p.original_price * 1.20))) * 100, 6) ELSE NULL END
  ) AS s
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  WHERE p.deleted_at IS NULL AND p.brand_id IS DISTINCT FROM :insize_id AND p.base_price > 0
  ORDER BY p.base_price DESC, p.id ASC
  LIMIT 5
) q;

SELECT '=== SAMPLE active_available ===';
SELECT coalesce(json_agg(s)::text, '[]')
FROM (
  SELECT json_build_object(
    'product_id', p.id,
    'sku', p.sku,
    'brand', b.name,
    'name', p.name,
    'is_active', p.is_active,
    'is_available', p.is_available,
    'old_base_price', p.base_price,
    'old_original_price', p.original_price,
    'raw_new_base_price', p.base_price * 1.20,
    'raw_new_original_price', CASE WHEN p.original_price IS NULL THEN NULL ELSE p.original_price * 1.20 END,
    'old_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - (p.base_price / p.original_price)) * 100, 6) ELSE NULL END,
    'projected_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - ((p.base_price * 1.20) / (p.original_price * 1.20))) * 100, 6) ELSE NULL END
  ) AS s
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  WHERE p.deleted_at IS NULL AND p.brand_id IS DISTINCT FROM :insize_id AND p.base_price > 0
    AND p.is_active IS TRUE AND p.is_available IS TRUE
  ORDER BY p.id ASC
  LIMIT 5
) q;

SELECT '=== SAMPLE active_unavailable ===';
SELECT coalesce(json_agg(s)::text, '[]')
FROM (
  SELECT json_build_object(
    'product_id', p.id,
    'sku', p.sku,
    'brand', b.name,
    'name', p.name,
    'is_active', p.is_active,
    'is_available', p.is_available,
    'old_base_price', p.base_price,
    'old_original_price', p.original_price,
    'raw_new_base_price', p.base_price * 1.20,
    'raw_new_original_price', CASE WHEN p.original_price IS NULL THEN NULL ELSE p.original_price * 1.20 END,
    'old_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - (p.base_price / p.original_price)) * 100, 6) ELSE NULL END,
    'projected_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - ((p.base_price * 1.20) / (p.original_price * 1.20))) * 100, 6) ELSE NULL END
  ) AS s
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  WHERE p.deleted_at IS NULL AND p.brand_id IS DISTINCT FROM :insize_id AND p.base_price > 0
    AND p.is_active IS TRUE AND p.is_available IS FALSE
  ORDER BY p.id ASC
  LIMIT 5
) q;

SELECT '=== SAMPLE inactive ===';
SELECT coalesce(json_agg(s)::text, '[]')
FROM (
  SELECT json_build_object(
    'product_id', p.id,
    'sku', p.sku,
    'brand', b.name,
    'name', p.name,
    'is_active', p.is_active,
    'is_available', p.is_available,
    'old_base_price', p.base_price,
    'old_original_price', p.original_price,
    'raw_new_base_price', p.base_price * 1.20,
    'raw_new_original_price', CASE WHEN p.original_price IS NULL THEN NULL ELSE p.original_price * 1.20 END,
    'old_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - (p.base_price / p.original_price)) * 100, 6) ELSE NULL END,
    'projected_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - ((p.base_price * 1.20) / (p.original_price * 1.20))) * 100, 6) ELSE NULL END
  ) AS s
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  WHERE p.deleted_at IS NULL AND p.brand_id IS DISTINCT FROM :insize_id AND p.base_price > 0
    AND p.is_active IS FALSE
  ORDER BY p.id ASC
  LIMIT 5
) q;

SELECT '=== SAMPLE brandless ===';
SELECT coalesce(json_agg(s)::text, '[]')
FROM (
  SELECT json_build_object(
    'product_id', p.id,
    'sku', p.sku,
    'brand', b.name,
    'name', p.name,
    'is_active', p.is_active,
    'is_available', p.is_available,
    'old_base_price', p.base_price,
    'old_original_price', p.original_price,
    'raw_new_base_price', p.base_price * 1.20,
    'raw_new_original_price', CASE WHEN p.original_price IS NULL THEN NULL ELSE p.original_price * 1.20 END,
    'old_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - (p.base_price / p.original_price)) * 100, 6) ELSE NULL END,
    'projected_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - ((p.base_price * 1.20) / (p.original_price * 1.20))) * 100, 6) ELSE NULL END
  ) AS s
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  WHERE p.deleted_at IS NULL AND p.brand_id IS NULL AND p.base_price > 0
  ORDER BY p.id ASC
  LIMIT 5
) q;

SELECT '=== SAMPLE class_b ===';
SELECT coalesce(json_agg(s)::text, '[]')
FROM (
  SELECT json_build_object(
    'product_id', p.id,
    'sku', p.sku,
    'brand', b.name,
    'name', p.name,
    'is_active', p.is_active,
    'is_available', p.is_available,
    'old_base_price', p.base_price,
    'old_original_price', p.original_price,
    'raw_new_base_price', p.base_price * 1.20,
    'raw_new_original_price', p.original_price * 1.20,
    'old_discount_percent', round((1 - (p.base_price / p.original_price)) * 100, 6),
    'projected_discount_percent', round((1 - ((p.base_price * 1.20) / (p.original_price * 1.20))) * 100, 6)
  ) AS s
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  WHERE p.deleted_at IS NULL AND p.brand_id IS DISTINCT FROM :insize_id
    AND p.base_price > 0 AND p.original_price > p.base_price
  ORDER BY p.id ASC
  LIMIT 5
) q;

SELECT '=== SAMPLE class_c ===';
SELECT coalesce(json_agg(s)::text, '[]')
FROM (
  SELECT json_build_object(
    'product_id', p.id,
    'sku', p.sku,
    'brand', b.name,
    'name', p.name,
    'is_active', p.is_active,
    'is_available', p.is_available,
    'old_base_price', p.base_price,
    'old_original_price', p.original_price,
    'raw_new_base_price', p.base_price * 1.20,
    'raw_new_original_price', p.original_price * 1.20,
    'old_discount_percent', NULL,
    'projected_discount_percent', NULL
  ) AS s
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  WHERE p.deleted_at IS NULL AND p.brand_id IS DISTINCT FROM :insize_id
    AND p.base_price > 0 AND p.original_price = p.base_price
  ORDER BY p.id ASC
  LIMIT 5
) q;

SELECT '=== SAMPLE class_d ===';
SELECT coalesce(json_agg(s)::text, '[]')
FROM (
  SELECT json_build_object(
    'product_id', p.id,
    'sku', p.sku,
    'brand', b.name,
    'name', p.name,
    'is_active', p.is_active,
    'is_available', p.is_available,
    'old_base_price', p.base_price,
    'old_original_price', p.original_price,
    'raw_new_base_price', p.base_price * 1.20,
    'raw_new_original_price', p.original_price * 1.20,
    'old_discount_percent', NULL,
    'projected_discount_percent', NULL
  ) AS s
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  WHERE p.deleted_at IS NULL AND p.brand_id IS DISTINCT FROM :insize_id
    AND p.base_price > 0 AND p.original_price < p.base_price
  ORDER BY p.id ASC
  LIMIT 5
) q;

SELECT '=== SAMPLE fractional ===';
SELECT coalesce(json_agg(s)::text, '[]')
FROM (
  SELECT json_build_object(
    'product_id', p.id,
    'sku', p.sku,
    'brand', b.name,
    'name', p.name,
    'is_active', p.is_active,
    'is_available', p.is_available,
    'old_base_price', p.base_price,
    'old_original_price', p.original_price,
    'raw_new_base_price', p.base_price * 1.20,
    'raw_new_original_price', CASE WHEN p.original_price IS NULL THEN NULL ELSE p.original_price * 1.20 END,
    'old_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - (p.base_price / p.original_price)) * 100, 6) ELSE NULL END,
    'projected_discount_percent', CASE WHEN p.original_price > p.base_price THEN round((1 - ((p.base_price * 1.20) / (p.original_price * 1.20))) * 100, 6) ELSE NULL END
  ) AS s
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  WHERE p.deleted_at IS NULL AND p.brand_id IS DISTINCT FROM :insize_id AND p.base_price > 0
    AND (
      (p.base_price * 1.20) <> trunc(p.base_price * 1.20)
      OR (p.base_price * 12) <> trunc(p.base_price * 12)
    )
  ORDER BY p.id ASC
  LIMIT 5
) q;

SELECT '=== SAMPLE name_looks_insize ===';
SELECT coalesce(json_agg(s)::text, '[]')
FROM (
  SELECT json_build_object(
    'product_id', p.id,
    'sku', p.sku,
    'brand_id', p.brand_id,
    'brand', b.name,
    'name', p.name,
    'is_active', p.is_active,
    'is_available', p.is_available,
    'old_base_price', p.base_price,
    'old_original_price', p.original_price,
    'raw_new_base_price', CASE WHEN p.base_price IS NULL THEN NULL ELSE p.base_price * 1.20 END,
    'raw_new_original_price', CASE WHEN p.original_price IS NULL THEN NULL ELSE p.original_price * 1.20 END,
    'old_discount_percent', NULL,
    'projected_discount_percent', NULL
  ) AS s
  FROM products p
  LEFT JOIN brands b ON b.id = p.brand_id
  WHERE p.deleted_at IS NULL
    AND p.brand_id IS DISTINCT FROM :insize_id
    AND (
      lower(p.name) LIKE '%insize%'
      OR lower(p.sku) LIKE '%insize%'
      OR replace(p.name, chr(8204), '') LIKE '%اینسایز%'
    )
  ORDER BY p.id ASC
  LIMIT 8
) q;
ROLLBACK;
