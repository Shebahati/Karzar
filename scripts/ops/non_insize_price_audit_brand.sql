-- Read-only INSIZE brand resolution. No writes.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT current_setting('transaction_read_only') AS transaction_read_only;
SELECT current_database() AS database_name;
SELECT json_build_object(
  'id', id,
  'name', name,
  'slug', slug
)::text
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
   OR replace(slug, chr(8204), '') LIKE '%این سایز%'
ORDER BY id;
ROLLBACK;
