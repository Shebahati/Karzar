-- Guarded rollback for Product 1789 brand repair
-- Only restores brand_id NULL if current state still matches post-repair guards.
BEGIN;
UPDATE products
SET brand_id = NULL
WHERE id = 1789
  AND brand_id = 3
  AND sku = '1114-150'
  AND manufacturer_code = '1114-150'
  AND deleted_at IS NULL;
-- Expect ROW_COUNT = 1; otherwise ROLLBACK manually.
INSERT INTO product_change_logs (product_id, field_name, old_value, new_value, reason, actor_user_id)
VALUES (1789, 'brand_id', '3', NULL,
        'owner_authorized_brand_integrity_repair_rollback', NULL);
COMMIT;
