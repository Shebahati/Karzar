"use client";

import { useMemo } from "react";
import { Container } from "@/components/ui/container";
import { Hero } from "@/components/home/hero";
import { CategoryOrbsGrid } from "@/components/home/category-orbs-grid";
import { MobileCategorySection } from "@/components/home/mobile-category-section";
import { ProductCarousel } from "@/components/home/product-carousel";
import { BrandStrip } from "@/components/home/brand-strip";
import { WhyKarzar } from "@/components/home/why-karzar";
import { FeatureStrip } from "@/components/home/feature-strip";
import { HomeContactSection } from "@/components/home/home-contact-section";
import { ArticlesSection } from "@/components/home/articles-section";
import { SectionHeading } from "@/components/home/section-heading";
import { useArticles, useProducts } from "@/features/catalog/queries";
import type { Brand, CategoryTreeNode } from "@/types/category";
import type { ProductSummary } from "@/types/product";

function rankBestsellers(products: ProductSummary[]): ProductSummary[] {
  return [...products]
    .filter((p) => p.availability !== false)
    .sort((a, b) => {
      const score = (p: ProductSummary) =>
        (p.discount_percent ?? 0) * 3 +
        (p.stock_status === "موجود" || p.stock_status === "in_stock" || p.availability ? 8 : 0) +
        (p.is_original ? 4 : 0);
      return score(b) - score(a);
    })
    .slice(0, 12);
}

/** Client island for the home page — hydrated from RSC prefetch. */
export function HomeView({
  initialBrands = [],
  initialCategoryTree = [],
}: {
  initialBrands?: Brand[];
  initialCategoryTree?: CategoryTreeNode[];
}) {
  const catalog = useProducts({ limit: 48, sort: "newest" });
  const articlesQuery = useArticles();
  const products = catalog.data?.data;
  const hasArticles =
    articlesQuery.isLoading || (articlesQuery.data?.length ?? 0) > 0;

  const bestsellers = useMemo(() => rankBestsellers(products ?? []), [products]);
  const deals = useMemo(
    () =>
      (products ?? [])
        .filter((p) => (p.discount_percent ?? 0) > 0)
        .sort((a, b) => (b.discount_percent ?? 0) - (a.discount_percent ?? 0))
        .slice(0, 12),
    [products],
  );

  return (
    <div>
      {/* Mobile: compact hero + normal flow. md+: sticky snap + full viewport */}
      <div className="hero-snap relative h-[62dvh] md:sticky md:top-0 md:z-0 md:h-[100dvh]">
        <Hero />
      </div>

      <div className="home-snap relative mt-5 bg-background pb-10 md:z-10 md:-mt-1 md:rounded-t-[2.25rem] md:pb-16 md:shadow-[0_-28px_80px_rgba(0,0,0,0.38)]">
        <div
          aria-hidden
          className="mx-auto mb-2 mt-3 hidden h-1.5 w-12 rounded-full bg-border/80 md:mt-4 md:block"
        />
        <Container className="home-stack pt-3 md:pt-6">
          <MobileCategorySection initialTree={initialCategoryTree} />

          {(catalog.isLoading || deals.length > 0) && (
            <section>
              <SectionHeading
                title="پرتخفیف‌ها"
                subtitle="بهترین تخفیف‌های ابزار صنعتی — اسلاید خودکار"
                href="/catalog"
                hrefLabel="همه محصولات پرتخفیف"
              />
              <ProductCarousel
                products={deals}
                isLoading={catalog.isLoading}
                variant="deal"
                autoPlay
              />
            </section>
          )}

          <section>
            <SectionHeading
              title="پرفروش‌ها"
              subtitle="انتخاب سریع از موجودی زنده کاتالوگ"
              href="/catalog?sort=newest"
            />
            <ProductCarousel
              products={bestsellers}
              isLoading={catalog.isLoading}
              variant="featured"
              autoPlay
            />
          </section>

          <FeatureStrip />

          <WhyKarzar />

          <section>
            <SectionHeading title="برندهای معتبر" subtitle="نمایندگی رسمی برترین برندها" />
            <BrandStrip initialBrands={initialBrands} />
          </section>

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

          <section
            aria-labelledby="home-orbs-heading-lg"
            className="relative hidden overflow-hidden md:block"
          >
            <div
              aria-hidden
              className="pointer-events-none absolute -inset-x-8 -top-6 bottom-0 -z-10"
            >
              <div className="absolute inset-0 bg-gradient-to-b from-[#F8F8F8] via-transparent to-transparent" />
              <div className="absolute -start-20 top-4 h-48 w-48 rounded-full bg-primary/[0.04] blur-3xl" />
              <div className="absolute -end-16 top-20 h-40 w-40 rounded-full bg-[#5E5F5E]/[0.05] blur-3xl" />
            </div>

            <SectionHeading
              id="home-orbs-heading-lg"
              title="دسته‌بندی محصولات"
              subtitle="مسیر سریع به دسته‌های اصلی فروشگاه"
              href="/catalog"
              hrefLabel="همه محصولات"
            />
            <CategoryOrbsGrid maxItems={null} initialTree={initialCategoryTree} />
          </section>

          <HomeContactSection />
        </Container>
      </div>
    </div>
  );
}
