"use client";

import { useMemo } from "react";
import { useProductsByIds } from "@/features/catalog/queries";
import { useOrder } from "@/features/orders/queries";
import type { OrderDetail } from "@/types/order";

/** Batch-fetch products to enrich order line items (decision 4-B). */
export function useEnrichedOrder(id: number) {
  const query = useOrder(id);
  const productIds = useMemo(
    () => (query.data?.items ?? []).map((i) => i.product_id),
    [query.data?.items],
  );
  const productsQuery = useProductsByIds(productIds);

  const enriched = useMemo((): OrderDetail | undefined => {
    if (!query.data) return undefined;
    if (!productsQuery.data?.length) return query.data;

    const byId = new Map(
      productsQuery.data.map((p) => [p.id, { name: p.name, sku: p.sku }]),
    );

    // Only enrich line item names/SKUs — preserve shipping, timeline, invoice, etc.
    return {
      ...query.data,
      items: query.data.items.map((item) => {
        const product = byId.get(item.product_id);
        if (!product) return item;
        return {
          ...item,
          product_name: product.name,
          sku: product.sku,
        };
      }),
    };
  }, [query.data, productsQuery.data]);

  return {
    ...query,
    data: enriched,
    isEnriching: productsQuery.isPending && productIds.length > 0,
  };
}
