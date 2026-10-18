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

-- Follow-up on verified 2026-10-18 10:40:12Z snapshot:
-- A candidate pre-APPLY *data* gate, not APPLY, not media or rights clearance.
-- Fixed expected values intentionally go stale when anyone changes either row.
WITH expected (
  id, sku, manufacturer_code, category_id, current_brand_id,
  current_base_price, current_original_price, current_updated_at,
  approved_brand_id, approved_base_price, approved_original_price
) AS (
  VALUES
    (1944, '3203-1506'::text, '3203-1506'::text, 58, NULL::integer,
     47100000.00::numeric, 47100000.00::numeric,
     '2026-10-18 09:20:42.106058+00'::timestamptz,
     3, 40035000.00::numeric, 47100000.00::numeric),
    (3639, 'S3-2824'::text, NULL::text, 63, NULL::integer,
     NULL::numeric, 10.00::numeric,
     '2026-10-18 09:18:13.567359+00'::timestamptz,
     3, 45390000.00::numeric, 53400000.00::numeric)
)
SELECT
  e.id AS product_id,
  e.sku AS expected_sku,
  p.updated_at AS observed_updated_at,
  e.current_updated_at AS expected_updated_at,
  p.brand_id AS observed_brand_id,
  p.base_price AS observed_base_price,
  p.original_price AS observed_original_price,
  e.approved_brand_id AS proposed_brand_id,
  e.approved_base_price AS proposed_base_price,
  e.approved_original_price AS proposed_original_price,
  CASE
    WHEN p.id IS NULL THEN 'STOP_MISSING_PRODUCT'
    WHEN p.sku IS DISTINCT FROM e.sku
      OR p.manufacturer_code IS DISTINCT FROM e.manufacturer_code
      OR p.category_id IS DISTINCT FROM e.category_id
      OR p.brand_id IS DISTINCT FROM e.current_brand_id
      OR p.deleted_at IS NOT NULL THEN 'STOP_IDENTITY_DRIFT'
    WHEN NOT EXISTS (
      SELECT 1 FROM brands b
      WHERE b.id = e.approved_brand_id AND b.name ILIKE 'INSIZE%'
    ) THEN 'STOP_BRAND_MASTER'
    WHEN NOT EXISTS (
      SELECT 1 FROM product_change_logs l
      WHERE l.product_id = e.id AND l.field_name = 'brand_id'
        AND l.old_value = '3' AND l.new_value IS NULL
        AND l.reason = 'product_update'
    ) THEN 'STOP_BRAND_PROVENANCE'
    WHEN p.updated_at IS DISTINCT FROM e.current_updated_at
      OR p.base_price IS DISTINCT FROM e.current_base_price
      OR p.original_price IS DISTINCT FROM e.current_original_price
      OR p.is_active IS DISTINCT FROM TRUE
      OR p.is_available IS DISTINCT FROM TRUE THEN 'STOP_STATE_OR_PRICE_DRIFT'
    WHEN EXISTS (
      SELECT 1 FROM product_images pi WHERE pi.product_id = e.id
    ) THEN 'STOP_IMAGE_STATE_CHANGED'
    ELSE 'DATA_SNAPSHOT_MATCH_MEDIA_AND_AUTH_PENDING'
  END AS candidate_data_gate
FROM expected e
LEFT JOIN products p ON p.id = e.id
ORDER BY e.id;

-- Audit metadata only; no actor identity, personal details or JSON payloads.
SELECT id, action, entity_type, entity_id, created_at
FROM admin_audit_logs
WHERE entity_id IN ('1944', '3639')
ORDER BY created_at DESC, id DESC
LIMIT 20;

ROLLBACK;
