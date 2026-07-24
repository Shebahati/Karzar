"use client";

import { Container } from "@/components/ui/container";
import { Hero } from "@/components/home/hero";
import { CategoryGrid } from "@/components/home/category-grid";
import { ProductCarousel } from "@/components/home/product-carousel";
import { BrandStrip } from "@/components/home/brand-strip";
import { ArticlesSection } from "@/components/home/articles-section";
import { FeatureStrip } from "@/components/home/feature-strip";
import { WhyKarzar } from "@/components/home/why-karzar";
import { SectionHeading } from "@/components/home/section-heading";
import { useProducts } from "@/features/catalog/queries";

/** Client island for the home page — hydrated from RSC prefetch. */
export function HomeView() {
  const discounted = useProducts({ limit: 12, sort: "newest" });
  const newest = useProducts({ limit: 10, sort: "newest" });

  const discountList = discounted.data?.data.filter((p) => p.discount_percent) ?? [];

  return (
    <div className="bg-hero-glow pb-8 lg:pb-12">
      <Container className="space-y-10 py-5 sm:space-y-14 sm:py-8">
        <section>
          <Hero />
        </section>

        <section>
          <SectionHeading
            title="دسته‌بندی محصولات"
            subtitle="سریع‌تر به ابزار مورد نیازتان برسید"
            href="/catalog"
          />
          <CategoryGrid />
        </section>

        <section>
          <FeatureStrip />
        </section>

        <WhyKarzar />

        {(discounted.isLoading || discountList.length > 0) && (
          <section>
            <SectionHeading
              title="پیشنهادهای ویژه"
              subtitle="تخفیف روی ابزارهای منتخب"
              href="/catalog"
            />
            <ProductCarousel products={discountList} isLoading={discounted.isLoading} />
          </section>
        )}

        <section>
          <SectionHeading
            title="جدیدترین محصولات"
            subtitle="تازه‌ترین کالاهای فروشگاه"
            href="/catalog?sort=newest"
          />
          <ProductCarousel products={newest.data?.data ?? []} isLoading={newest.isLoading} />
        </section>

        <section>
          <SectionHeading title="برندهای معتبر" subtitle="نمایندگی رسمی برترین برندها" />
          <BrandStrip />
        </section>

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
