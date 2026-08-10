"use client";

import { useMemo } from "react";
import { useProducts } from "@/features/catalog/queries";
import {
  DEFAULT_MAX_PRICE,
  DEFAULT_MIN_PRICE,
} from "@/components/catalog/use-catalog-params";
import type { ProductListParams, ProductSummary } from "@/types/product";

/**
 * Window size for price-sorted domain probes.
 * Must be > inquiry (null-price) SKUs that sort first on `price_asc`
 * when the API/mock treats missing prices as 0 — `limit=1` otherwise
 * yields a single expensive end and a bogus ±5% pad.
 */
const PRICE_DOMAIN_WINDOW = 100;

/** Selling/display unit price shown on PLP cards (`base_price`). */
export function productFilterPrice(
  product: Pick<ProductSummary, "base_price">,
): number | null {
  if (product.base_price == null || product.base_price === "") return null;
  const n = Number(product.base_price);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

/** Min/max from a product list; ignores inquiry rows without a usable price. */
export function computePriceBounds(
  products: Pick<ProductSummary, "base_price">[],
): { min: number; max: number } | null {
  let min = Infinity;
  let max = -Infinity;
  for (const product of products) {
    const price = productFilterPrice(product);
    if (price == null) continue;
    if (price < min) min = price;
    if (price > max) max = price;
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) return null;
  return { min, max };
}

/**
 * Slider domain when only one priced product (or all share one price).
 * Keeps the dual-thumb control usable without collapsing to a point.
 */
export function expandEqualPriceDomain(min: number, max: number): {
  min: number;
  max: number;
} {
  if (min < max) return { min, max };
  const pad = Math.max(100_000, Math.round(min * 0.05) || 100_000);
  return { min: Math.max(0, min - pad), max: max + pad };
}

/** Adaptive step so short domains still move the thumbs. */
export function priceRangeStep(absoluteMin: number, absoluteMax: number): number {
  const span = Math.max(0, absoluteMax - absoluteMin);
  if (span <= 1) return 1;
  if (span < 10_000) return 1;
  if (span < 1_000_000) return 1_000;
  if (span < 10_000_000) return 10_000;
  return 100_000;
}

/**
 * Price slider domain for the current shop context:
 * cheapest / most expensive **selling** prices (`base_price`) among products
 * matching non-price filters. Scans sorted windows (not limit=1) so null-price
 * inquiry SKUs do not steal the cheap end.
 */
export function useCatalogPriceDomain(
  listParams: ProductListParams,
  /** Optional PLP rows already on screen — always folded into the domain. */
  seedProducts: Pick<ProductSummary, "base_price">[] = [],
): {
  absoluteMin: number;
  absoluteMax: number;
  ready: boolean;
} {
  const facetParams = useMemo(() => {
    const {
      min_price: _min,
      max_price: _max,
      sort: _sort,
      skip: _skip,
      limit: _limit,
      ...rest
    } = listParams;
    return rest;
  }, [listParams]);

  // Default-order sample covers “what’s on the shop” when API sort is flaky.
  const sample = useProducts({
    ...facetParams,
    limit: PRICE_DOMAIN_WINDOW,
    skip: 0,
  });
  // Sorted windows find true ends when the API honors price_asc / price_desc.
  const cheapestWindow = useProducts({
    ...facetParams,
    sort: "price_asc",
    limit: PRICE_DOMAIN_WINDOW,
    skip: 0,
  });
  const dearestWindow = useProducts({
    ...facetParams,
    sort: "price_desc",
    limit: PRICE_DOMAIN_WINDOW,
    skip: 0,
  });

  return useMemo(() => {
    const ready =
      !sample.isLoading && !cheapestWindow.isLoading && !dearestWindow.isLoading;
    const bounds = computePriceBounds([
      ...seedProducts,
      ...(sample.data?.data ?? []),
      ...(cheapestWindow.data?.data ?? []),
      ...(dearestWindow.data?.data ?? []),
    ]);
    if (!bounds) {
      return {
        absoluteMin: DEFAULT_MIN_PRICE,
        absoluteMax: DEFAULT_MAX_PRICE,
        ready,
      };
    }
    const expanded = expandEqualPriceDomain(bounds.min, bounds.max);
    return {
      absoluteMin: expanded.min,
      absoluteMax: expanded.max,
      ready,
    };
  }, [
    seedProducts,
    sample.data,
    sample.isLoading,
    cheapestWindow.data,
    cheapestWindow.isLoading,
    dearestWindow.data,
    dearestWindow.isLoading,
  ]);
}
