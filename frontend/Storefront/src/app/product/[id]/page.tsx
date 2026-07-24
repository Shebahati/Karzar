import type { Metadata } from "next";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { ProductDetailView } from "@/components/product/product-detail-view";
import { catalogKeys } from "@/features/catalog/keys";
import { getQueryClient } from "@/lib/get-query-client";
import { catalogService } from "@/services/catalog";

type Props = { params: Promise<{ id: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const productId = Number(id);
  if (!Number.isFinite(productId)) {
    return { title: "محصول" };
  }
  try {
    const product = await catalogService.getProduct(productId);
    const title = product.name;
    const description =
      product.description?.slice(0, 160) ||
      `خرید ${product.name} از فروشگاه کارزار با ضمانت اصالت.`;
    const images = product.thumbnail ? [{ url: product.thumbnail }] : undefined;
    return {
      title,
      description,
      openGraph: { title, description, images },
      alternates: { canonical: `/product/${productId}` },
    };
  } catch {
    return { title: "محصول" };
  }
}

export default async function ProductPage({ params }: Props) {
  const { id } = await params;
  const productId = Number(id);
  const queryClient = getQueryClient();

  if (Number.isFinite(productId) && productId > 0) {
    await queryClient.prefetchQuery({
      queryKey: catalogKeys.product(productId),
      queryFn: () => catalogService.getProduct(productId),
    });
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ProductDetailView id={productId} />
    </HydrationBoundary>
  );
}
