import type { Metadata } from "next";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { ProductDetailView } from "@/components/product/product-detail-view";
import { catalogKeys } from "@/features/catalog/keys";
import { getQueryClient } from "@/lib/get-query-client";
import { buildProductPageJsonLd } from "@/lib/json-ld";
import {
  resolveMetaDescription,
  resolveMetaTitle,
} from "@/lib/product-seo";
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
    const title = resolveMetaTitle(product.meta_title, product.name);
    const description = resolveMetaDescription({
      metaDescription: product.meta_description,
      shortDescription: product.short_description,
      description: product.description,
      name: product.name,
    });
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

  let jsonLd: Record<string, unknown> | null = null;

  if (Number.isFinite(productId) && productId > 0) {
    await queryClient.prefetchQuery({
      queryKey: catalogKeys.product(productId),
      queryFn: () => catalogService.getProduct(productId),
    });

    try {
      const product = await catalogService.getProduct(productId);
      jsonLd = buildProductPageJsonLd(product);
    } catch {
      jsonLd = null;
    }
  }

  return (
    <>
      {jsonLd ? (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      ) : null}
      <HydrationBoundary state={dehydrate(queryClient)}>
        <ProductDetailView id={productId} />
      </HydrationBoundary>
    </>
  );
}
