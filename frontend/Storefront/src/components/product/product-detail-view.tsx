"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ChevronLeft } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ProductGallery } from "@/components/product/product-gallery";
import { TwoLaneActions } from "@/components/product/two-lane-actions";
import { MobileStickyBuyBar } from "@/components/product/mobile-sticky-buy-bar";
import { ProductSpecTabs } from "@/components/product/product-spec-tabs";
import { ProductTrustStrip } from "@/components/product/product-trust-strip";
import { ProductPdfCta } from "@/components/product/product-pdf-cta";
import { ProductAccessoriesSlot } from "@/components/product/product-accessories-slot";
import {
  findBrandLogoUrl,
  PdpBrandMark,
} from "@/components/product/pdp-brand-mark";
import { ProductKnowledgeRail } from "@/components/product/product-knowledge-rail";
import { SectionHeading } from "@/components/home/section-heading";
import {
  useBrands,
  useFlatCategories,
  useProduct,
} from "@/features/catalog/queries";
import { categoryHref } from "@/config/nav-groups";
import {
  filterEditorialDescription,
  hasRenderableSpecs,
} from "@/lib/pdp-description";
import { cn, formatToman } from "@/lib/utils";

const easePremium = [0.22, 1, 0.36, 1] as const;

const ProductComments = dynamic(
  () =>
    import("@/components/product/product-comments").then((m) => m.ProductComments),
  {
    loading: () => <Skeleton className="h-40 w-full rounded-2xl" />,
    ssr: false,
  },
);

const RelatedProducts = dynamic(
  () =>
    import("@/components/product/related-products").then((m) => m.RelatedProducts),
  {
    loading: () => <Skeleton className="h-48 w-full rounded-2xl" />,
    ssr: false,
  },
);

export function ProductDetailView({ id }: { id: number }) {
  const { data: product, isLoading, isError } = useProduct(id);
  const { data: categories = [] } = useFlatCategories();
  const { data: brands = [] } = useBrands();
  const reducedMotion = useReducedMotion();

  if (isLoading) return <DetailSkeleton />;

  if (isError || !product) {
    return (
      <Container className="py-20 text-center">
        <p className="text-lg font-bold text-foreground">محصول یافت نشد</p>
        <Link href="/catalog" className="mt-4 inline-block text-sm font-bold text-primary">
          بازگشت به فروشگاه
        </Link>
      </Container>
    );
  }

  const hasPrice = product.base_price != null;
  const byId = new Map(categories.map((c) => [c.id, c]));
  const pathIds = [
    ...(product.category?.ancestor_ids ?? []),
    ...(product.category?.id != null ? [product.category.id] : []),
  ];
  const crumbs = pathIds
    .map((cid) => byId.get(cid))
    .filter((c): c is NonNullable<typeof c> => Boolean(c));
  const breadcrumbNames =
    crumbs.length > 0
      ? crumbs.map((c) => c.name)
      : (product.category?.breadcrumb ?? []);

  const brandLogoUrl = findBrandLogoUrl(product.brand, brands);

  const showSpecSection =
    hasRenderableSpecs(product.specifications) ||
    Boolean(
      filterEditorialDescription(
        product.description,
        product.specifications,
        product.short_description,
      ),
    );

  const fadeUp = reducedMotion
    ? undefined
    : { initial: { opacity: 0, y: 14 }, animate: { opacity: 1, y: 0 } };

  return (
    <div className="relative pb-24 lg:pb-14">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[min(52vh,420px)]"
        style={{
          background: `
            radial-gradient(48% 55% at 88% 0%, rgba(208,35,39,0.045), transparent 70%),
            linear-gradient(180deg, hsl(0 0% 97.5%) 0%, transparent 100%)
          `,
        }}
      />

      <Container className="pt-5 sm:pt-8 lg:pt-10">
        <nav
          aria-label="مسیر صفحه"
          className="mb-6 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground sm:mb-8"
        >
          <Link href="/" className="transition-colors hover:text-primary">
            خانه
          </Link>
          <ChevronLeft size="small" set="light" />
          <Link href="/catalog" className="transition-colors hover:text-primary">
            فروشگاه
          </Link>
          {crumbs.length > 0
            ? crumbs.map((crumb) => (
                <span key={crumb.id} className="flex items-center gap-1.5">
                  <ChevronLeft size="small" set="light" />
                  <Link
                    href={categoryHref(crumb)}
                    className="transition-colors hover:text-primary"
                  >
                    {crumb.name}
                  </Link>
                </span>
              ))
            : breadcrumbNames.map((crumb) => (
                <span key={crumb} className="flex items-center gap-1.5">
                  <ChevronLeft size="small" set="light" />
                  {crumb}
                </span>
              ))}
        </nav>

        {/* Hero: clean gallery + commerce — no orbit beside photos */}
        <section
          aria-label="معرفی محصول"
          className="grid items-start gap-10 lg:grid-cols-2 lg:gap-14 xl:gap-16"
        >
          <motion.div
            className="min-w-0"
            {...(fadeUp ?? {})}
            transition={{ duration: 0.55, ease: easePremium }}
          >
            <ProductGallery images={product.images} alt={product.name} />
          </motion.div>

          <motion.div
            className="flex min-w-0 flex-col"
            {...(fadeUp ?? {})}
            transition={{
              duration: 0.6,
              ease: easePremium,
              delay: reducedMotion ? 0 : 0.05,
            }}
          >
            <h1 className="text-[1.4rem] font-bold leading-[1.55] tracking-tight text-foreground sm:text-2xl lg:text-[1.7rem] lg:leading-[1.5]">
              {product.name}
            </h1>

            {product.short_description ? (
              <p className="mt-3 max-w-xl text-sm leading-8 text-foreground/85">
                {product.short_description}
              </p>
            ) : null}

            <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
              <span className="text-muted-foreground" dir="ltr">
                کد کالا:{" "}
                <span className="font-medium text-foreground tnum">{product.sku}</span>
              </span>
              <StockBadge status={product.stock_status} available={product.availability} />
            </div>

            {/* Buy box — sole interactive surface in the hero */}
            <div
              className={cn(
                "mt-7 rounded-2xl bg-secondary/55 p-5 sm:p-6",
                "ring-1 ring-steel/[0.06]",
              )}
            >
              <div className="mb-5">
                {hasPrice ? (
                  <div>
                    {product.original_price && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground line-through tnum">
                          {formatToman(product.original_price)}
                        </span>
                        {product.discount_percent ? (
                          <Badge variant="primary">٪{product.discount_percent}</Badge>
                        ) : null}
                      </div>
                    )}
                    <div className="mt-1 text-[1.65rem] font-bold tracking-tight text-foreground tnum sm:text-3xl">
                      {formatToman(product.base_price)}
                    </div>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm text-muted-foreground">قیمت این محصول</p>
                    <p className="mt-1 text-xl font-bold text-primary">
                      با استعلام تعیین می‌شود
                    </p>
                  </div>
                )}
              </div>
              <TwoLaneActions product={product} />
            </div>

            {/* Brand — quiet row under buy box, not hero chrome */}
            {product.brand ? (
              <div className="mt-5 border-t border-steel/10 pt-5">
                <PdpBrandMark
                  brand={product.brand}
                  logoUrl={brandLogoUrl}
                  density="quiet"
                />
              </div>
            ) : null}

            <ProductTrustStrip
              className="mt-5"
              warrantyText={product.warranty_text}
              isOriginal={product.is_original}
            />

            <ProductPdfCta product={product} />
          </motion.div>
        </section>

        {showSpecSection ? (
          <section className="mt-16 sm:mt-20" aria-labelledby="pdp-specs-heading">
            <SectionHeading
              id="pdp-specs-heading"
              title="مشخصات فنی"
              subtitle="جدول مشخصات منبع اصلی است؛ توضیحات تحریریه جداگانه نمایش داده می‌شود"
            />
            <ProductSpecTabs
              specifications={product.specifications}
              description={product.description}
              shortDescription={product.short_description}
            />
          </section>
        ) : null}

        <ProductAccessoriesSlot product={product} />

        <ProductKnowledgeRail productId={product.id} />

        <section className="mt-16 sm:mt-20">
          <SectionHeading title="دیدگاه کاربران" />
          <ProductComments productId={product.id} />
        </section>

        <section className="mt-16 pb-4 sm:mt-20">
          <SectionHeading title="محصولات مرتبط" />
          <RelatedProducts productId={product.id} />
        </section>

        <MobileStickyBuyBar product={product} />
      </Container>
    </div>
  );
}

function StockBadge({ status, available }: { status: string; available: boolean }) {
  return <Badge variant={available ? "success" : "muted"}>{status}</Badge>;
}

function DetailSkeleton() {
  return (
    <Container className="py-10">
      <div className="grid gap-10 lg:grid-cols-2 lg:gap-14">
        <Skeleton className="aspect-square rounded-xl" />
        <div className="space-y-4">
          <Skeleton className="h-8 w-4/5" />
          <Skeleton className="h-5 w-1/2" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="mt-4 h-44 w-full rounded-2xl" />
          <Skeleton className="h-12 w-48 rounded-xl" />
          <Skeleton className="h-20 w-full rounded-xl" />
        </div>
      </div>
    </Container>
  );
}
