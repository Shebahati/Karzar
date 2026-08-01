import type { Metadata } from "next";
import { permanentRedirect, notFound } from "next/navigation";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { ProductDetailView } from "@/components/product/product-detail-view";
import { catalogKeys } from "@/features/catalog/keys";
import { getQueryClient } from "@/lib/get-query-client";
import { buildProductPageJsonLd } from "@/lib/json-ld";
import {
  resolveMetaDescription,
  resolveMetaTitle,
} from "@/lib/product-seo";
import {
  isNumericProductParam,
  productPath,
  safeDecodeURIComponent,
} from "@/lib/product-url";
import { catalogService } from "@/services/catalog";
import type { ProductDetail } from "@/types/product";

type Props = { params: Promise<{ slug: string }> };

async function resolveProduct(param: string): Promise<ProductDetail> {
  const key = safeDecodeURIComponent(param.trim());
  if (!key) throw new Error("missing");

  if (isNumericProductParam(key)) {
    const productId = Number(key);
    return catalogService.getProduct(productId);
  }
  return catalogService.getProductBySlug(key);
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug: rawParam } = await params;
  const param = safeDecodeURIComponent(rawParam);
  try {
    const product = await resolveProduct(param);
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
      alternates: { canonical: productPath(product) },
    };
  } catch {
    return { title: "محصول" };
  }
}

export default async function ProductPage({ params }: Props) {
  const { slug: rawParam } = await params;
  const param = safeDecodeURIComponent(rawParam);
  const queryClient = getQueryClient();

  let product: ProductDetail;
  try {
    product = await resolveProduct(param);
  } catch {
    notFound();
  }

  // RFC-004: permanent redirect from /product/{id} → /product/{slug}
  if (
    isNumericProductParam(param) &&
    product.slug?.trim() &&
    product.slug.trim() !== param.trim()
  ) {
    permanentRedirect(productPath(product));
  }

  await queryClient.prefetchQuery({
    queryKey: catalogKeys.product(product.id),
    queryFn: () => catalogService.getProduct(product.id),
  });

  const jsonLd = buildProductPageJsonLd(product);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <HydrationBoundary state={dehydrate(queryClient)}>
        <ProductDetailView id={product.id} />
      </HydrationBoundary>
    </>
  );
}
