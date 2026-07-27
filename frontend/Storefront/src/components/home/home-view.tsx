"use client";

import { useMemo } from "react";
import { Container } from "@/components/ui/container";
import { Hero } from "@/components/home/hero";
import { CategoryGrid } from "@/components/home/category-grid";
import { ProductCarousel } from "@/components/home/product-carousel";
import { BrandStrip } from "@/components/home/brand-strip";
import { ArticlesSection } from "@/components/home/articles-section";
import { WhyKarzar } from "@/components/home/why-karzar";
import { FeatureStrip } from "@/components/home/feature-strip";
import { SectionHeading } from "@/components/home/section-heading";
import { useProducts } from "@/features/catalog/queries";
import type { ProductSummary } from "@/types/product";

/**
 * Rank "bestsellers" from live catalog data until BE exposes sort=bestsellers.
 * Prefers available, discounted, then newer items — all from real product rows.
 */
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
export function HomeView() {
  const catalog = useProducts({ limit: 48, sort: "newest" });
  const products = catalog.data?.data;

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
    <div className="pb-10 lg:pb-16">
      {/* Full-bleed hero — outside Container; section rhythm lives in .home-stack */}
      <Hero />

      <Container className="home-stack">
        <section aria-labelledby="home-categories-heading">
          <SectionHeading
            id="home-categories-heading"
            title="دسته‌بندی محصولات"
            subtitle="مسیر سریع به دسته‌های اصلی کاتالوگ — اندازه‌گیری در ابتدا"
            href="/catalog"
            hrefLabel="همه محصولات"
          />
          <CategoryGrid />
        </section>

        <FeatureStrip />

        <section>
          <SectionHeading
            title="پرفروش‌ترین محصولات"
            subtitle="انتخاب سریع از موجودی زنده کاتالوگ"
            href="/catalog?sort=newest"
          />
          <ProductCarousel
            products={bestsellers}
            isLoading={catalog.isLoading}
            variant="featured"
          />
        </section>

        <section>
          <SectionHeading title="برندهای معتبر" subtitle="نمایندگی رسمی برترین برندها" />
          <BrandStrip />
        </section>

        {(catalog.isLoading || deals.length > 0) && (
          <section>
            <SectionHeading
              title="پیشنهادهای تخفیف‌دار"
              subtitle="قیمت ویژه روی ابزارهای منتخب"
              href="/catalog?sort=newest"
            />
            <ProductCarousel products={deals} isLoading={catalog.isLoading} variant="deal" />
          </section>
        )}

        <WhyKarzar />

        <section>
          <SectionHeading
            title="مجله کارزار"
            subtitle="راهنماها و مقالات تخصصی"
            href="/blog"
          />
          <ArticlesSection />
        </section>
      </Container>
    </div>
  );
}
