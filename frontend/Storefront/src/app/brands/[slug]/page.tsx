import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { BrandHubView } from "@/components/brand/brand-hub-view";
import { Container } from "@/components/ui/container";
import { ProductCardSkeleton } from "@/components/product/product-card";
import { NOINDEX_FOLLOW, isFacetedSearchParams } from "@/lib/crawl-hygiene";
import { buildBrandHubJsonLd } from "@/lib/json-ld";
import { catalogService } from "@/services/catalog";
import type { Brand } from "@/types/category";

type SearchParams = Record<string, string | string[] | undefined>;

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<SearchParams>;
};

const HUB_PLP = { limit: 24, skip: 0 } as const;

/** D21 Q1=A / Q2=A: below ≥1 active products → still 200, noindex. */
function isThinBrandHub(productCount: number | null | undefined): boolean {
  return (productCount ?? 0) < 1;
}

export async function generateMetadata({
  params,
  searchParams,
}: Props): Promise<Metadata> {
  const { slug } = await params;
  const sp = await searchParams;
  const faceted = isFacetedSearchParams(sp);
  try {
    const brand = await catalogService.getBrandBySlug(slug);
    const thin = isThinBrandHub(brand.product_count);
    const title = brand.meta_title || `${brand.name} | کارزار`;
    const description =
      brand.meta_description ||
      `محصولات برند ${brand.name} در فروشگاه ابزار صنعتی کارزار.`;
    const canonical = `/brands/${brand.slug ?? slug}`;
    return {
      title,
      description,
      alternates: { canonical },
      openGraph: { title, description, type: "website" },
      ...(thin || faceted ? { robots: NOINDEX_FOLLOW } : {}),
    };
  } catch {
    return {
      title: "برند یافت نشد | کارزار",
      robots: { index: false, follow: false },
    };
  }
}

export default async function BrandHubPage({ params }: Props) {
  const { slug } = await params;
  let brand: Brand;
  try {
    brand = await catalogService.getBrandBySlug(slug);
  } catch {
    notFound();
  }

  let jsonLd: Record<string, unknown> | null = null;
  try {
    const productsPage = await catalogService.listProducts({
      ...HUB_PLP,
      brand_ids: [brand.id],
    });
    jsonLd = buildBrandHubJsonLd({
      brand,
      products: productsPage.data ?? [],
    });
  } catch {
    jsonLd = null;
  }

  return (
    <>
      {jsonLd ? (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      ) : null}
      <Suspense
        fallback={
          <Container className="py-10">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <ProductCardSkeleton key={i} />
              ))}
            </div>
          </Container>
        }
      >
        <BrandHubView brand={brand} />
      </Suspense>
    </>
  );
}
