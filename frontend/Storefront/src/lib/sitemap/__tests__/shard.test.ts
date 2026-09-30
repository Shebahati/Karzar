import { describe, expect, it } from "vitest";
import { PRODUCT_SITEMAP_SHARD_SIZE } from "../constants";
import {
  isValidProductShardIndex,
  productShardCount,
  productShardSkip,
} from "../shard";

const S = PRODUCT_SITEMAP_SHARD_SIZE;

describe("product sitemap shard math", () => {
  const cases = [0, 1, 999, 1000, 1001, 1999, 2000, 2001, 19999, 20000, 20001, 49000, 50000, 50001, 100000];

  it.each(cases)("count=%i", (count) => {
    const shards = productShardCount(count);
    const expected = count <= 0 ? 0 : Math.ceil(count / S);
    expect(shards).toBe(expected);
    expect(shards).not.toBeGreaterThan(Math.ceil(100_000 / S));
  });

  it("100k catalog produces 100 shards at size 1000", () => {
    expect(productShardCount(100_000)).toBe(100);
  });

  it("no 20k hard stop", () => {
    expect(productShardCount(20_001)).toBe(21);
  });

  it("shard skip boundaries", () => {
    expect(productShardSkip(0)).toBe(0);
    expect(productShardSkip(1)).toBe(S);
    expect(productShardSkip(99)).toBe(99 * S);
  });

  it("invalid shard when none exist", () => {
    expect(isValidProductShardIndex(0, 0)).toBe(false);
  });

  it("valid shard range for 2500 products", () => {
    expect(isValidProductShardIndex(0, 2500)).toBe(true);
    expect(isValidProductShardIndex(2, 2500)).toBe(true);
    expect(isValidProductShardIndex(3, 2500)).toBe(false);
    expect(isValidProductShardIndex(-1, 2500)).toBe(false);
  });
});
