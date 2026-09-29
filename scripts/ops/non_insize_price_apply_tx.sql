-- Owner-authorized price apply. The caller has already started the transaction
-- and loaded manifest_raw(line jsonb). This file commits only after assertions.
SET LOCAL lock_timeout = '30s';
SET LOCAL statement_timeout = '180s';
LOCK TABLE hesabfa_item_mappings IN SHARE MODE;

DO $lock$
BEGIN
  PERFORM id
  FROM products
  WHERE deleted_at IS NULL
    AND (
      brand_id = 3
      OR (
        (brand_id IS NULL OR brand_id <> 3)
        AND base_price IS NOT NULL
        AND base_price > 0
      )
    )
  ORDER BY id
  FOR UPDATE;
END
$lock$;

CREATE TEMP TABLE price_before AS
SELECT
  id, sku, slug, name, brand_id, category_id, product_type_id,
  base_price, original_price, is_active, is_available, stock_quantity, deleted_at
FROM products;

CREATE TEMP TABLE manifest AS
SELECT
  (line->>'product_id')::int AS product_id,
  line->>'sku' AS sku,
  CASE WHEN line->>'brand_id' IS NULL THEN NULL ELSE (line->>'brand_id')::int END AS brand_id,
  line->>'brand_name' AS brand_name,
  CASE WHEN line->>'deleted_at' IS NULL THEN NULL ELSE (line->>'deleted_at')::timestamptz END AS deleted_at,
  (line->>'old_base_price')::numeric AS old_base_price,
  (line->>'new_base_price')::numeric AS new_base_price,
  CASE WHEN line->>'old_original_price' IS NULL THEN NULL ELSE (line->>'old_original_price')::numeric END AS old_original_price,
  CASE WHEN line->>'new_original_price' IS NULL THEN NULL ELSE (line->>'new_original_price')::numeric END AS new_original_price,
  line->>'price_class' AS price_class
FROM manifest_raw;

CREATE TEMP TABLE map_before AS
SELECT md5(coalesce(string_agg(
  id::text || ':' || product_id::text || ':' || sku || ':' || hesabfa_code,
  ',' ORDER BY id
), '')) AS fingerprint,
count(*) AS mapping_rows
FROM hesabfa_item_mappings;

DO $assert$
BEGIN
  IF (SELECT count(*) FROM manifest) <> 4065 THEN
    RAISE EXCEPTION 'APPLY_ABORT manifest_count';
  END IF;
  IF (SELECT count(*) FROM manifest WHERE price_class = 'A') <> 4058 THEN
    RAISE EXCEPTION 'APPLY_ABORT class_a';
  END IF;
  IF (SELECT count(*) FROM manifest WHERE price_class = 'B') <> 7 THEN
    RAISE EXCEPTION 'APPLY_ABORT class_b';
  END IF;
  IF (SELECT count(*) FROM manifest WHERE price_class NOT IN ('A', 'B')) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT unexpected_class';
  END IF;
  IF (SELECT count(*) FROM manifest WHERE brand_id = 3 OR deleted_at IS NOT NULL) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT scope';
  END IF;
  IF (SELECT count(*) FROM manifest WHERE old_base_price IS NULL OR old_base_price <= 0) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT old_base';
  END IF;
  IF (SELECT count(*) FROM manifest WHERE (old_base_price * numeric '1.20') <> trunc(old_base_price * numeric '1.20')) <> 17 THEN
    RAISE EXCEPTION 'APPLY_ABORT fractional_raw';
  END IF;
  IF (SELECT count(*) FROM manifest WHERE new_base_price <> round(old_base_price * numeric '1.20', 0)) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT base_rounding';
  END IF;
  IF (SELECT count(*) FROM manifest WHERE price_class = 'A' AND (old_original_price IS NOT NULL OR new_original_price IS NOT NULL)) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT class_a_original';
  END IF;
  IF (SELECT count(*) FROM manifest WHERE price_class = 'B' AND (
    old_original_price IS NULL
    OR old_original_price <= old_base_price
    OR new_original_price IS DISTINCT FROM round(old_original_price * numeric '1.20', 0)
  )) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT class_b_original';
  END IF;
  IF (SELECT count(*) FROM manifest WHERE new_base_price <> trunc(new_base_price) OR new_base_price <= 0) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT new_base_whole';
  END IF;
  IF (SELECT coalesce(sum(new_base_price - (old_base_price * numeric '1.20')), 0)
      FROM manifest
      WHERE (old_base_price * numeric '1.20') = trunc(old_base_price * numeric '1.20')) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT rounding_delta_not_only_fractional';
  END IF;
  IF (SELECT count(*) FROM price_before WHERE deleted_at IS NULL AND brand_id = 3) <> 872 THEN
    RAISE EXCEPTION 'APPLY_ABORT insize_live';
  END IF;
  IF (SELECT count(*) FROM price_before WHERE deleted_at IS NULL AND brand_id = 3 AND base_price > 0) <> 487 THEN
    RAISE EXCEPTION 'APPLY_ABORT insize_priced';
  END IF;
  IF (SELECT count(*)
      FROM manifest m
      JOIN price_before p ON p.id = m.product_id
      WHERE p.base_price = m.old_base_price
        AND p.original_price IS NOT DISTINCT FROM m.old_original_price
        AND p.brand_id IS NOT DISTINCT FROM m.brand_id
        AND p.deleted_at IS NOT DISTINCT FROM m.deleted_at
        AND p.sku = m.sku) <> 4065 THEN
    RAISE EXCEPTION 'APPLY_ABORT compare_and_swap';
  END IF;
  IF (SELECT count(*)
      FROM price_before p
      WHERE p.deleted_at IS NULL
        AND (p.brand_id IS NULL OR p.brand_id <> 3)
        AND p.base_price IS NOT NULL
        AND p.base_price > 0
        AND NOT EXISTS (SELECT 1 FROM manifest m WHERE m.product_id = p.id)) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT missing_manifest_row';
  END IF;
  IF (SELECT count(*) FROM product_change_logs WHERE reason = 'owner_non_insize_price_increase_20pct_2026_09_29') <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT already_applied';
  END IF;
END
$assert$;

LOCK TABLE product_change_logs IN SHARE ROW EXCLUSIVE MODE;

DO $apply$
DECLARE
  log_rows integer;
  updated_rows integer;
  id_default text;
BEGIN
  SELECT column_default INTO id_default
  FROM information_schema.columns
  WHERE table_schema = 'public'
    AND table_name = 'product_change_logs'
    AND column_name = 'id';

  IF id_default IS NOT NULL AND position('nextval' in id_default) > 0 THEN
    INSERT INTO product_change_logs (
      product_id, field_name, old_value, new_value, reason, actor_user_id
    )
    SELECT
      product_id,
      field_name,
      old_value,
      new_value,
      'owner_non_insize_price_increase_20pct_2026_09_29',
      NULL
    FROM (
      SELECT
        product_id,
        'base_price'::text AS field_name,
        to_char(trunc(old_base_price), 'FM999999999999999') AS old_value,
        to_char(trunc(new_base_price), 'FM999999999999999') AS new_value
      FROM manifest
      UNION ALL
      SELECT
        product_id,
        'original_price'::text,
        to_char(trunc(old_original_price), 'FM999999999999999'),
        to_char(trunc(new_original_price), 'FM999999999999999')
      FROM manifest
      WHERE price_class = 'B'
    ) changes;
  ELSE
    INSERT INTO product_change_logs (
      id, product_id, field_name, old_value, new_value, reason, actor_user_id
    )
    SELECT
      COALESCE((SELECT max(id) FROM product_change_logs), 0) + row_number() OVER (ORDER BY product_id, field_name),
      product_id,
      field_name,
      old_value,
      new_value,
      'owner_non_insize_price_increase_20pct_2026_09_29',
      NULL
    FROM (
      SELECT
        product_id,
        'base_price'::text AS field_name,
        to_char(trunc(old_base_price), 'FM999999999999999') AS old_value,
        to_char(trunc(new_base_price), 'FM999999999999999') AS new_value
      FROM manifest
      UNION ALL
      SELECT
        product_id,
        'original_price'::text,
        to_char(trunc(old_original_price), 'FM999999999999999'),
        to_char(trunc(new_original_price), 'FM999999999999999')
      FROM manifest
      WHERE price_class = 'B'
    ) changes;
  END IF;

  GET DIAGNOSTICS log_rows = ROW_COUNT;
  IF log_rows <> 4072 THEN
    RAISE EXCEPTION 'APPLY_ABORT log_rows %', log_rows;
  END IF;

  UPDATE products p
  SET
    base_price = m.new_base_price,
    original_price = CASE
      WHEN m.price_class = 'B' THEN m.new_original_price
      ELSE p.original_price
    END
  FROM manifest m
  WHERE p.id = m.product_id
    AND p.deleted_at IS NULL
    AND (p.brand_id IS NULL OR p.brand_id <> 3)
    AND p.base_price = m.old_base_price
    AND p.original_price IS NOT DISTINCT FROM m.old_original_price
    AND p.brand_id IS NOT DISTINCT FROM m.brand_id
    AND p.sku = m.sku
    AND p.base_price > 0
    AND (
      (m.price_class = 'A' AND p.original_price IS NULL AND m.new_original_price IS NULL)
      OR (
        m.price_class = 'B'
        AND p.original_price > p.base_price
        AND m.new_original_price IS NOT NULL
      )
    );

  GET DIAGNOSTICS updated_rows = ROW_COUNT;
  IF updated_rows <> 4065 THEN
    RAISE EXCEPTION 'APPLY_ABORT updated_rows %', updated_rows;
  END IF;
END
$apply$;

DO $post$
DECLARE
  base_changed integer;
  original_changed integer;
BEGIN
  SELECT count(*) INTO base_changed
  FROM products p
  JOIN manifest m ON m.product_id = p.id
  JOIN price_before b ON b.id = p.id
  WHERE p.base_price IS DISTINCT FROM b.base_price;

  SELECT count(*) INTO original_changed
  FROM products p
  JOIN manifest m ON m.product_id = p.id
  JOIN price_before b ON b.id = p.id
  WHERE p.original_price IS DISTINCT FROM b.original_price;

  IF base_changed <> 4065 THEN
    RAISE EXCEPTION 'APPLY_ABORT base_changed %', base_changed;
  END IF;
  IF original_changed <> 7 THEN
    RAISE EXCEPTION 'APPLY_ABORT original_changed %', original_changed;
  END IF;
  IF (SELECT count(*) FROM products p JOIN manifest m ON m.product_id = p.id
      WHERE p.base_price IS NULL OR p.base_price <= 0 OR p.base_price <> trunc(p.base_price)) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT stored_base';
  END IF;
  IF (SELECT count(*) FROM products p JOIN manifest m ON m.product_id = p.id
      WHERE p.base_price IS DISTINCT FROM round(m.old_base_price * numeric '1.20', 0)) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT stored_base_formula';
  END IF;
  IF (SELECT count(*) FROM products p JOIN manifest m ON m.product_id = p.id
      WHERE m.price_class = 'A' AND p.original_price IS NOT NULL) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT class_a_original_written';
  END IF;
  IF (SELECT count(*) FROM products p JOIN manifest m ON m.product_id = p.id
      WHERE m.price_class = 'B'
        AND p.original_price IS DISTINCT FROM round(m.old_original_price * numeric '1.20', 0)) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT class_b_original_formula';
  END IF;
  IF (SELECT count(*) FROM products p JOIN manifest m ON m.product_id = p.id
      WHERE m.price_class = 'B'
        AND round((1 - (m.old_base_price / m.old_original_price)) * 100)::int
            IS DISTINCT FROM round((1 - (p.base_price / p.original_price)) * 100)::int) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT discount_drift';
  END IF;
  IF (SELECT count(*) FROM products p
      JOIN price_before b ON b.id = p.id
      WHERE NOT EXISTS (SELECT 1 FROM manifest m WHERE m.product_id = p.id)
        AND (p.base_price IS DISTINCT FROM b.base_price OR p.original_price IS DISTINCT FROM b.original_price)) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT non_target_price';
  END IF;
  IF (SELECT count(*) FROM products p
      JOIN price_before b ON b.id = p.id
      WHERE b.brand_id = 3 AND b.deleted_at IS NULL
        AND (p.base_price IS DISTINCT FROM b.base_price OR p.original_price IS DISTINCT FROM b.original_price)) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT insize_price';
  END IF;
  IF (SELECT count(*) FROM products p
      JOIN price_before b ON b.id = p.id
      WHERE p.is_active IS DISTINCT FROM b.is_active
         OR p.is_available IS DISTINCT FROM b.is_available
         OR p.stock_quantity IS DISTINCT FROM b.stock_quantity
         OR p.brand_id IS DISTINCT FROM b.brand_id
         OR p.category_id IS DISTINCT FROM b.category_id
         OR p.sku IS DISTINCT FROM b.sku
         OR p.slug IS DISTINCT FROM b.slug
         OR p.name IS DISTINCT FROM b.name
         OR p.deleted_at IS DISTINCT FROM b.deleted_at
         OR p.product_type_id IS DISTINCT FROM b.product_type_id) <> 0 THEN
    RAISE EXCEPTION 'APPLY_ABORT non_price_column';
  END IF;
  IF (SELECT count(*) FROM product_change_logs WHERE reason = 'owner_non_insize_price_increase_20pct_2026_09_29') <> 4072 THEN
    RAISE EXCEPTION 'APPLY_ABORT log_total';
  END IF;
  IF (SELECT count(*) FROM product_change_logs WHERE reason = 'owner_non_insize_price_increase_20pct_2026_09_29' AND field_name = 'base_price') <> 4065 THEN
    RAISE EXCEPTION 'APPLY_ABORT log_base';
  END IF;
  IF (SELECT count(*) FROM product_change_logs WHERE reason = 'owner_non_insize_price_increase_20pct_2026_09_29' AND field_name = 'original_price') <> 7 THEN
    RAISE EXCEPTION 'APPLY_ABORT log_original';
  END IF;
  IF (SELECT fingerprint FROM map_before) IS DISTINCT FROM (
    SELECT md5(coalesce(string_agg(
      id::text || ':' || product_id::text || ':' || sku || ':' || hesabfa_code,
      ',' ORDER BY id
    ), ''))
    FROM hesabfa_item_mappings
  ) THEN
    RAISE EXCEPTION 'APPLY_ABORT hesabfa_mapping_changed';
  END IF;
  IF (SELECT mapping_rows FROM map_before) IS DISTINCT FROM (SELECT count(*) FROM hesabfa_item_mappings) THEN
    RAISE EXCEPTION 'APPLY_ABORT hesabfa_mapping_count';
  END IF;
END
$post$;

SELECT 'base_price_rows_changed=' || count(*)::text
FROM products p
JOIN price_before b ON b.id = p.id
WHERE p.base_price IS DISTINCT FROM b.base_price;
SELECT 'original_price_rows_changed=' || count(*)::text
FROM products p
JOIN price_before b ON b.id = p.id
WHERE p.original_price IS DISTINCT FROM b.original_price;
SELECT 'insize_price_rows_changed=' || count(*)::text
FROM products p
JOIN price_before b ON b.id = p.id
WHERE b.brand_id = 3
  AND b.deleted_at IS NULL
  AND (p.base_price IS DISTINCT FROM b.base_price OR p.original_price IS DISTINCT FROM b.original_price);
SELECT 'non_target_price_rows_changed=' || count(*)::text
FROM products p
JOIN price_before b ON b.id = p.id
WHERE NOT EXISTS (SELECT 1 FROM manifest m WHERE m.product_id = p.id)
  AND (p.base_price IS DISTINCT FROM b.base_price OR p.original_price IS DISTINCT FROM b.original_price);
SELECT 'product_change_log_rows=' || count(*)::text
FROM product_change_logs
WHERE reason = 'owner_non_insize_price_increase_20pct_2026_09_29';
SELECT 'old_total=' || coalesce(sum(old_base_price), 0)::text FROM manifest;
SELECT 'raw_total=' || coalesce(sum(old_base_price * numeric '1.20'), 0)::text FROM manifest;
SELECT 'rounded_total=' || coalesce(sum(new_base_price), 0)::text FROM manifest;
SELECT 'rounding_delta=' || coalesce(sum(new_base_price - (old_base_price * numeric '1.20')), 0)::text FROM manifest;
SELECT 'target_mapped=' || count(*)::text
FROM hesabfa_item_mappings m
JOIN manifest t ON t.product_id = m.product_id;
SELECT 'target_unmapped=' || (4065 - count(*))::text
FROM hesabfa_item_mappings m
JOIN manifest t ON t.product_id = m.product_id;
SELECT 'commit_gate=PASS';
COMMIT;
SELECT 'committed=YES';
