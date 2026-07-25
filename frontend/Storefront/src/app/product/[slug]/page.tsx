import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { ProductDetailView } from "@/components/product/product-detail-view";
import { catalogKeys } from "@/features/catalog/keys";
import { getQueryClient } from "@/lib/get-query-client";
import {
  resolveJsonLdDescription,
  resolveMetaDescription,
  resolveMetaTitle,
} from "@/lib/product-seo";
import { catalogService } from "@/services/catalog";
import type { ProductDetail } from "@/types/product";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "https://www.karzartools.com";

type Props = { params: Promise<{ slug: string }> };

function productPath(product: ProductDetail): string {
  return product.slug ? `/product/${product.slug}` : `/product/${product.id}`;
}

async function loadProduct(param: string): Promise<ProductDetail | null> {
  const asId = Number(param);
  try {
    if (Number.isFinite(asId) && asId > 0 && String(asId) === param) {
      return await catalogService.getProduct(asId);
    }
    return await catalogService.getProductBySlug(param);
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const product = await loadProduct(slug);
  if (!product) {
    return { title: "محصول" };
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
  const { slug } = await params;
  const product = await loadProduct(slug);

  if (!product) {
    return (
      <HydrationBoundary state={dehydrate(getQueryClient())}>
        <ProductDetailView id={Number.NaN} />
      </HydrationBoundary>
    );
  }

  // Permanent redirect from numeric id URLs to the canonical slug URL (FE-S-02).
  if (product.slug && String(product.id) === slug) {
    redirect(`/product/${product.slug}`);
  }

  const queryClient = getQueryClient();
  await queryClient.prefetchQuery({
    queryKey: catalogKeys.product(product.id),
    queryFn: () => catalogService.getProduct(product.id),
  });

  const url = `${SITE}${productPath(product)}`;
  const availability = product.availability
    ? "https://schema.org/InStock"
    : "https://schema.org/OutOfStock";
  const breadcrumbs: Record<string, unknown>[] = [
    { "@type": "ListItem", position: 1, name: "خانه", item: SITE },
  ];
  if (product.category?.name) {
    breadcrumbs.push({
      "@type": "ListItem",
      position: 2,
      name: product.category.name,
      item: product.category.slug
        ? `${SITE}/categories/${product.category.slug}`
        : undefined,
    });
    breadcrumbs.push({
      "@type": "ListItem",
      position: 3,
      name: product.name,
      item: url,
    });
  } else {
    breadcrumbs.push({
      "@type": "ListItem",
      position: 2,
      name: product.name,
      item: url,
    });
  }

  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Product",
        "@id": `${url}#product`,
        name: product.name,
        sku: product.sku,
        description: resolveJsonLdDescription({
          shortDescription: product.short_description,
          description: product.description,
          name: product.name,
        }),
        image: product.thumbnail ? [product.thumbnail] : undefined,
        brand: product.brand?.name
          ? { "@type": "Brand", name: product.brand.name }
          : undefined,
        offers: {
          "@type": "Offer",
          url,
          priceCurrency: "IRR",
          price: product.base_price ?? undefined,
          availability,
          itemCondition: "https://schema.org/NewCondition",
          seller: { "@type": "Organization", name: "کارزار", url: SITE },
        },
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: breadcrumbs,
      },
    ],
  };

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
