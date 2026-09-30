import type { Metadata } from "next";
import { permanentRedirect, notFound } from "next/navigation";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { ProductDetailView } from "@/components/product/product-detail-view";
import { catalogKeys } from "@/features/catalog/keys";
import { getQueryClient } from "@/lib/get-query-client";
import { rejectUnlessEntityNotFound } from "@/lib/entity-lookup";
import { buildProductPageJsonLd } from "@/lib/json-ld";
import {
  resolveMetaDescription,
  resolveMetaTitle,
} from "@/lib/product-seo";
import {
  isNumericProductParam,
  numericProductRedirectPath,
  productPath,
  safeDecodeURIComponent,
} from "@/lib/product-url";
import { catalogService } from "@/services/catalog";
import type { ProductDetail } from "@/types/product";

type Props = { params: Promise<{ slug: string }> };

async function resolveProduct(param: string): Promise<ProductDetail> {
  const key = safeDecodeURIComponent(param.trim());
  if (!key) notFound();

  if (isNumericProductParam(key)) {
    const productId = Number(key);
    return catalogService.getProduct(productId);
  }
  return catalogService.getProductBySlug(key);
}

/**
 * Resolve early in generateMetadata so `notFound()` / redirects establish HTTP
 * status before the root layout streams (otherwise Next falls back to 200 +
 * not-found UI / meta-refresh — see middleware numeric-redirect comment).
 */
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug: rawParam } = await params;
  const param = safeDecodeURIComponent(rawParam);
  let product: ProductDetail;
  try {
    product = await resolveProduct(param);
  } catch (error) {
    rejectUnlessEntityNotFound(error);
  }

  const redirectTo = numericProductRedirectPath(param, product);
  if (redirectTo) {
    permanentRedirect(redirectTo);
  }

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
}

export default async function ProductPage({ params }: Props) {
  const { slug: rawParam } = await params;
  const param = safeDecodeURIComponent(rawParam);
  const queryClient = getQueryClient();

  let product: ProductDetail;
  try {
    product = await resolveProduct(param);
  } catch (error) {
    rejectUnlessEntityNotFound(error);
  }

  // RFC-004: permanent redirect from /product/{id} → /product/{slug}
  // Prefer middleware (before layout streams); keep page-level as belt-and-suspenders.
  const redirectTo = numericProductRedirectPath(param, product);
  if (redirectTo) {
    permanentRedirect(redirectTo);
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
