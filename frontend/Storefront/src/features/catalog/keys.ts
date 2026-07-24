/** Shared catalog query keys — safe for RSC and client (no "use client"). */

import type { ProductListParams } from "@/types/product";

export const catalogKeys = {
  all: ["catalog"] as const,
  categoriesTree: () => [...catalogKeys.all, "categories", "tree"] as const,
  categoriesFlat: () => [...catalogKeys.all, "categories", "flat"] as const,
  brands: () => [...catalogKeys.all, "brands"] as const,
  products: (params: ProductListParams) =>
    [...catalogKeys.all, "products", params] as const,
  product: (id: number) => [...catalogKeys.all, "product", id] as const,
  related: (id: number) => [...catalogKeys.all, "related", id] as const,
  comments: (id: number) => [...catalogKeys.all, "comments", id] as const,
  articles: () => [...catalogKeys.all, "articles"] as const,
  article: (slug: string) => [...catalogKeys.all, "article", slug] as const,
  productsByIds: (ids: number[]) => [...catalogKeys.all, "productsByIds", ids] as const,
  hero: () => [...catalogKeys.all, "hero"] as const,
  specLabels: () => [...catalogKeys.all, "spec-labels"] as const,
  specFilterOptions: (categoryId: number) =>
    [...catalogKeys.all, "spec-filter-options", categoryId] as const,
};
