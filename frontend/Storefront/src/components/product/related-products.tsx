"use client";

import { useRelatedProducts } from "@/features/catalog/queries";
import { ProductCarousel } from "@/components/home/product-carousel";

export function RelatedProducts({ productId }: { productId: number }) {
  const { data, isLoading } = useRelatedProducts(productId);

  if (!isLoading && !data?.length) return null;

  return <ProductCarousel products={data ?? []} isLoading={isLoading} />;
}
