"use client";

import { useMemo } from "react";
import { Container } from "@/components/ui/container";
import { Hero } from "@/components/home/hero";
import { CategoryGrid } from "@/components/home/category-grid";
import { ProductCarousel } from "@/components/home/product-carousel";
import { BrandStrip } from "@/components/home/brand-strip";
import { ArticlesSection } from "@/components/home/articles-section";
import { WhyKarzar } from "@/components/home/why-karzar";
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
        (p.stock_status === "low_stock" ? 12 : 0) +
        (p.stock_status === "in_stock" || p.availability ? 8 : 0) +
        (p.is_original ? 4 : 0);
      return score(b) - score(a);
    })
    .slice(0, 12);
}

/** Client island for the home page — hydrated from RSC prefetch. */
export function HomeView() {
  const catalog = useProducts({ limit: 48, sort: "newest" });
  const products = catalog.data?.data ?? [];

  const bestsellers = useMemo(() => rankBestsellers(products), [products]);
  const deals = useMemo(
    () =>
      products
        .filter((p) => (p.discount_percent ?? 0) > 0)
        .sort((a, b) => (b.discount_percent ?? 0) - (a.discount_percent ?? 0))
        .slice(0, 12),
    [products],
  );

  return (
    <div className="pb-10 lg:pb-16">
      <section className="relative">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-[70vh] bg-[radial-gradient(ellipse_at_top,_rgba(94,95,94,0.09),_transparent_60%)]" />
        <Container className="relative pt-2 sm:pt-4">
          <Hero />
        </Container>
      </section>

      <Container className="space-y-14 py-8 sm:space-y-20 sm:py-12">
        <section>
          <SectionHeading
            title="پرفروش‌ترین محصولات"
            subtitle="بر اساس داده‌های زنده کاتالوگ فروشگاه"
            href="/catalog?sort=newest"
          />
          <ProductCarousel
            products={bestsellers}
            isLoading={catalog.isLoading}
            variant="featured"
          />
        </section>

        <section>
          <SectionHeading
            title="دسته‌بندی محصولات"
            subtitle="از ریشهٔ درخت دسته‌ها شروع کنید"
            href="/catalog"
          />
          <CategoryGrid />
        </section>

        <section>
          <SectionHeading title="برندهای معتبر" subtitle="نمایندگی رسمی برترین برندها" />
          <BrandStrip />
        </section>

        {(catalog.isLoading || deals.length > 0) && (
          <section>
            <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">
                  Offers
                </p>
                <h2 className="mt-1 text-xl font-bold text-foreground sm:text-2xl">
                  پیشنهادهای تخفیف‌دار
                </h2>
                <p className="mt-1 text-sm text-steel">
                  قیمت‌های ویژه روی ابزارهای منتخب — با موشن و انتخاب سریع
                </p>
              </div>
            </div>
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
