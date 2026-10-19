"use client";

import { Fragment, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { catalogService } from "@/services/catalog";
import {
  buildCuratedBestsellerProducts,
  shouldRenderCuratedBestsellersRail,
} from "@/features/home/curated-bestsellers";
import { Container } from "@/components/ui/container";
import { Hero } from "@/components/home/hero";
import { MobileCategorySection } from "@/components/home/mobile-category-section";
import { ProductCarousel } from "@/components/home/product-carousel";
import { BrandStrip } from "@/components/home/brand-strip";
import { WhyKarzar } from "@/components/home/why-karzar";
import { FeatureStrip } from "@/components/home/feature-strip";
import { HomeContactSection } from "@/components/home/home-contact-section";
import { ArticlesSection } from "@/components/home/articles-section";
import {
  MostViewedYesterdaySection,
  rankYesterdayMostViewed,
} from "@/components/home/most-viewed-yesterday-section";
import { SectionHeading } from "@/components/home/section-heading";
import { HomeCategoryCarousel } from "@/components/home/home-category-carousel";
import { CATEGORY_ICON_BY_SLUG } from "@/config/category-icons";
import { DISCOUNTS_CATALOG_HREF } from "@/config/l1-categories";
import { useArticles, useCategoryTree, useProducts } from "@/features/catalog/queries";
import {
  HOME_CATALOG_PRODUCTS_PARAMS,
  HOME_DEALS_PRODUCTS_PARAMS,
} from "@/features/home/home-catalog-params";
import { useHomeLayoutPack } from "@/features/home/use-home-layout";
import { defaultHomeLayoutPack } from "@/types/home-layout";
import type { Brand, CategoryTreeNode } from "@/types/category";
import type { DesignedHeroPack } from "@/types/hero-design";

/** Client island for the home page — hydrated from RSC prefetch. */
export function HomeView({
  initialBrands = [],
  initialCategoryTree = [],
  initialDesignedHeroPack = null,
  initialDesignedHeroPackUpdatedAt,
}: {
  initialBrands?: Brand[];
  initialCategoryTree?: CategoryTreeNode[];
  initialDesignedHeroPack?: DesignedHeroPack | null;
  initialDesignedHeroPackUpdatedAt?: number;
}) {
  const layoutQuery = useHomeLayoutPack();
  const sections =
    layoutQuery.data?.sections ?? defaultHomeLayoutPack().sections;

  const catalog = useProducts(HOME_CATALOG_PRODUCTS_PARAMS);
  const dealsQuery = useProducts(HOME_DEALS_PRODUCTS_PARAMS);
  const articlesQuery = useArticles();
  const categoryTreeQuery = useCategoryTree();
  const products = catalog.data?.data;
  const deals = dealsQuery.data?.data ?? [];
  const hasArticles =
    articlesQuery.isLoading || (articlesQuery.data?.length ?? 0) > 0;

  const tree = categoryTreeQuery.data?.length
    ? categoryTreeQuery.data
    : initialCategoryTree;

  const selection = useQuery({
    queryKey: ["home-bestsellers-published"],
    queryFn: () => catalogService.getPublishedBestsellers(),
    staleTime: 30_000,
  });
  const selectedIds = selection.data?.product_ids ?? [];
  const selectedKey = selectedIds.join(",");
  const curated = useQuery({
    queryKey: ["home-bestsellers-products", selectedKey],
    queryFn: () => catalogService.getProductsByIds(selectedIds),
    enabled: selection.isSuccess && selectedIds.length > 0,
    staleTime: 30_000,
  });
  const bestsellers = useMemo(
    () => buildCuratedBestsellerProducts(selectedIds, curated.data),
    [selectedKey, curated.data],
  );
  const yesterdayMostViewed = useMemo(
    () => rankYesterdayMostViewed(products ?? []),
    [products],
  );

  return (
    <div className="overflow-x-clip">
      {/*
        ── Sticky hero + sheet overlay (DISABLED — restore quickly if needed) ──
        Hero stayed fixed; home sections scrolled over it (md+). Re-enable by
        swapping the two active wrappers below with this commented pair:

        <div className="relative h-[62svh] max-w-full overflow-x-clip md:sticky md:top-0 md:z-0 md:h-[100svh]">
          <Hero />
        </div>
        <div className="relative mt-5 max-w-full overflow-x-clip bg-background pb-10 md:z-10 md:-mt-1 md:rounded-t-[2.25rem] md:pb-16 md:shadow-[0_-28px_80px_rgba(0,0,0,0.38)]">
          <div
            aria-hidden
            className="mx-auto mb-2 mt-3 hidden h-1.5 w-12 rounded-full bg-border/80 md:mt-4 md:block"
          />
          …Container + sections…
        </div>
      */}

      {/*
        svh (not dvh/vh): Android Chrome grows dvh ~40–56px when the URL bar
        hides on first scroll — a 62dvh hero then reflows and the page jumps.
        Small viewport units stay locked to the chrome-expanded size.
      */}
      {/*
        Hero owns its height (fallback 62svh/100svh or campaign min/max). A fixed
        outer svh wrapper caused gap (desktop) or overflow into the next section (compact campaign).
      */}
      <div className="relative max-w-full overflow-x-clip [overflow-anchor:none]">
        <Hero
          initialDesignedHeroPack={initialDesignedHeroPack}
          initialDesignedHeroPackUpdatedAt={initialDesignedHeroPackUpdatedAt}
        />
      </div>

      <div className="relative mt-5 max-w-full overflow-x-clip bg-background pb-10 md:pb-16">
        <Container className="home-stack pt-3 md:pt-6">
          {/*
            Mobile: L1 categories first (not in hero). Desktop: categories stay in hero dock —
            no separate orbs grid here (avoids duplication).
          */}
          <MobileCategorySection initialTree={initialCategoryTree} />

          {sections
            .filter((s) => s.enabled)
            .map((section) => {
              switch (section.type) {
                case "discounts":
                  if (!dealsQuery.isLoading && deals.length === 0) return null;
                  return (
                    <section
                      key={section.id}
                      aria-labelledby="home-discounts-heading"
                    >
                      <ProductCarousel
                        products={deals}
                        isLoading={dealsQuery.isLoading}
                        variant="deal"
                        headingId="home-discounts-heading"
                        lead={{
                          title: "پرتخفیف‌ها",
                          href: DISCOUNTS_CATALOG_HREF,
                          hrefLabel: "مشاهده همه",
                          iconSrc: CATEGORY_ICON_BY_SLUG.takhfif!,
                        }}
                      />
                    </section>
                  );

                case "bestsellers":
                  if (
                    !shouldRenderCuratedBestsellersRail({
                      selectionLoaded: selection.isSuccess,
                      selectedIds,
                      productsLoading: curated.isLoading,
                      visibleCount: bestsellers.length,
                    })
                  )
                    return null;
                  return (
                    <section key={section.id}>
                      <SectionHeading
                        title="پرفروش‌ها"
                        href="/catalog"
                      />
                      <ProductCarousel
                        products={bestsellers}
                        isLoading={selection.isLoading || (selectedIds.length > 0 && curated.isLoading)}
                        variant="featured"
                      />
                    </section>
                  );

                case "features":
                  return <WhyKarzar key={section.id} />;

                case "trust":
                  return <FeatureStrip key={section.id} />;

                case "category_carousel":
                  return (
                    <HomeCategoryCarousel
                      key={section.id}
                      section={section}
                      tree={tree}
                    />
                  );

                case "brands":
                  return (
                    <section key={section.id}>
                      <SectionHeading title="برندهای معتبر" />
                      <BrandStrip initialBrands={initialBrands} />
                    </section>
                  );

                case "articles":
                  return (
                    <Fragment key={section.id}>
                      {hasArticles ? (
                        <section aria-labelledby="home-articles-heading">
                          <SectionHeading
                            id="home-articles-heading"
                            title="مقالات پر بازدید"
                            subtitle="راهنماها و نکات فنی پرمخاطب مجله کارزار"
                            href="/blog"
                            hrefLabel="همه مقالات"
                          />
                          <ArticlesSection />
                        </section>
                      ) : null}
                      <MostViewedYesterdaySection
                        products={yesterdayMostViewed}
                        isLoading={catalog.isLoading}
                      />
                    </Fragment>
                  );

                case "contact":
                  return <HomeContactSection key={section.id} />;

                default:
                  return null;
              }
            })}
        </Container>
      </div>
    </div>
  );
}
