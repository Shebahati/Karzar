import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CategoryHubView } from "@/components/category/category-hub-view";
import { Container } from "@/components/ui/container";
import { ProductCardSkeleton } from "@/components/product/product-card";
import {
  NOINDEX_FOLLOW,
  isEmptyCategoryHub,
  isFacetedSearchParams,
} from "@/lib/crawl-hygiene";
import { getHubIntro, hubIntroExcerpt } from "@/lib/hub-intros";
import { buildCategoryHubJsonLd } from "@/lib/json-ld";
import { catalogService } from "@/services/catalog";
import type { CategoryFlat } from "@/types/category";

type SearchParams = Record<string, string | string[] | undefined>;

type Props = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<SearchParams>;
};

const HUB_PLP = { limit: 24, skip: 0 } as const;

export async function generateMetadata({
  params,
  searchParams,
}: Props): Promise<Metadata> {
  const { slug } = await params;
  const sp = await searchParams;
  const faceted = isFacetedSearchParams(sp, { ignoreCategoryKeys: true });
  try {
    const category = await catalogService.getCategoryBySlug(slug);
    if (isEmptyCategoryHub(category.product_count)) {
      return {
        title: "دسته یافت نشد | کارزار",
        robots: { index: false, follow: false },
      };
    }
    const intro = getHubIntro(category.slug ?? slug);
    const title = category.meta_title || `${category.name} | کارزار`;
    const description =
      category.meta_description ||
      (intro ? hubIntroExcerpt(intro) : null) ||
      `خرید و مشاهده محصولات دسته ${category.name} در فروشگاه ابزار صنعتی کارزار.`;
    return {
      title,
      description,
      alternates: { canonical: `/categories/${category.slug ?? slug}` },
      openGraph: { title, description, type: "website" },
      ...(faceted ? { robots: NOINDEX_FOLLOW } : {}),
    };
  } catch {
    return { title: "دسته یافت نشد | کارزار", robots: { index: false, follow: false } };
  }
}

function resolveAncestors(
  category: CategoryFlat,
  all: CategoryFlat[],
): CategoryFlat[] {
  const byId = new Map(all.map((c) => [c.id, c]));
  return (category.ancestor_ids ?? [])
    .map((id) => byId.get(id))
    .filter((c): c is CategoryFlat => Boolean(c));
}

export default async function CategoryHubPage({ params }: Props) {
  const { slug } = await params;
  let category: CategoryFlat;
  try {
    category = await catalogService.getCategoryBySlug(slug);
  } catch {
    notFound();
  }

  // Soft-404 → hard 404: empty hubs must not return 200.
  if (isEmptyCategoryHub(category.product_count)) {
    notFound();
  }

  const intro = getHubIntro(category.slug ?? slug);

  let jsonLd: Record<string, unknown> | null = null;
  try {
    const [all, productsPage] = await Promise.all([
      catalogService.listCategoriesFlat(),
      catalogService.listProducts({
        ...HUB_PLP,
        category_id: category.id,
      }),
    ]);
    const categoryForLd =
      !category.meta_description && intro
        ? { ...category, meta_description: hubIntroExcerpt(intro) }
        : category;
    jsonLd = buildCategoryHubJsonLd({
      category: categoryForLd,
      ancestors: resolveAncestors(category, all),
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
        <CategoryHubView category={category} intro={intro} />
      </Suspense>
    </>
  );
}
