import type { Metadata } from "next";
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

const SITE = "https://www.karzartools.com";

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
      const url = `${SITE}/product/${productId}`;
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

      jsonLd = {
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
