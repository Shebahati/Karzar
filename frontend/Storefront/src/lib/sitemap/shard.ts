import { PRODUCT_SITEMAP_SHARD_SIZE, SITEMAP_PROTOCOL_MAX_URLS_PER_FILE } from "./constants";

export function productShardCount(totalPublicProducts: number): number {
  if (totalPublicProducts <= 0) return 0;
  return Math.ceil(totalPublicProducts / PRODUCT_SITEMAP_SHARD_SIZE);
}

export function productShardSkip(shardIndex: number): number {
  return shardIndex * PRODUCT_SITEMAP_SHARD_SIZE;
}

export function isValidProductShardIndex(
  shardIndex: number,
  totalPublicProducts: number,
): boolean {
  if (!Number.isInteger(shardIndex) || shardIndex < 0) return false;
  const shards = productShardCount(totalPublicProducts);
  if (shards === 0) return false;
  return shardIndex < shards;
}

export function assertShardUrlCountWithinProtocolLimit(urlCount: number): void {
  if (urlCount > SITEMAP_PROTOCOL_MAX_URLS_PER_FILE) {
    throw new Error(
      `Sitemap shard exceeds protocol limit (${urlCount} > ${SITEMAP_PROTOCOL_MAX_URLS_PER_FILE})`,
    );
  }
}
