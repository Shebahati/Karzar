-- OWNER PRICE + MEDIA PRE-FLIGHT — ONLY product IDs 1944 and 3639.
-- Execute via an approved, read-only Production DB connection:
--   psql "$READ_ONLY_DSN" -X -v ON_ERROR_STOP=1 \
--     -f scripts/catalog_target/insize_two_product_readonly_preflight_20261018.sql
-- Do not paste DSN/credentials into chat or commit them. Confirm actual live
-- data-plane identity independently; APP_ENV=staging is not a safe indicator.
-- There are no DML, DDL, API, Hesabfa or deployment operations in this file.
\set ON_ERROR_STOP on
\pset pager off

BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '15s';

SELECT
  now() AS snapshot_at,
  current_database() AS database_name,
  current_user AS database_role,
  inet_server_addr()::text AS database_server_address,
  current_setting('transaction_read_only') AS transaction_read_only;

SELECT
  p.id AS product_id,
  p.sku,
  CASE
    WHEN p.id = 1944 AND p.sku = '3203-1506' AND p.brand_id = 3 THEN 'IDENTITY_MATCH'
    WHEN p.id = 3639 AND p.sku = 'S3-2824' AND p.brand_id = 3 THEN 'IDENTITY_MATCH'
    ELSE 'STOP_IDENTITY_MISMATCH'
  END AS identity_gate,
  p.name,
  p.manufacturer_code,
  p.brand_id,
  p.category_id,
  p.product_type_id,
  p.slug,
  p.deleted_at,
  p.updated_at,
  p.is_active,
  p.is_available,
  p.base_price,
  p.original_price,
  CASE
    WHEN p.base_price > 0 AND p.original_price > p.base_price
    THEN ROUND((1 - p.base_price / p.original_price) * 100, 2)
    ELSE NULL
  END AS derived_discount_percent,
  COALESCE((
    SELECT jsonb_agg(
      jsonb_build_object(
        'id', pi.id,
        'url', pi.image_url,
        'is_primary', pi.is_primary,
        'display_order', pi.display_order
      ) ORDER BY pi.display_order, pi.id
    )
    FROM product_images pi
    WHERE pi.product_id = p.id
  ), '[]'::jsonb) AS image_rows,
  EXISTS (
    SELECT 1 FROM product_images pi
    WHERE pi.product_id = p.id
      AND pi.image_url IS NOT NULL
      AND LENGTH(TRIM(pi.image_url)) > 0
      AND pi.image_url !~* 'placeholder|woocommerce-placeholder|no[-_]?image|default[-_]?(image|product)|karzar-editorial|/images/placeholders/'
  ) AS has_nonplaceholder_image_row
FROM products p
WHERE p.id IN (1944, 3639)
ORDER BY p.id;

SELECT
  COUNT(*) AS found_target_rows,
  ARRAY_AGG(id ORDER BY id) AS found_ids,
  COUNT(*) FILTER (
    WHERE (id = 1944 AND sku = '3203-1506' AND brand_id = 3)
       OR (id = 3639 AND sku = 'S3-2824' AND brand_id = 3)
  ) AS matching_identity_rows,
  COUNT(*) FILTER (WHERE deleted_at IS NULL) AS nondeleted_rows
FROM products
WHERE id IN (1944, 3639);

ROLLBACK;
