"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { Call, ChevronLeft, Star } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ProductGallery } from "@/components/product/product-gallery";
import { TwoLaneActions } from "@/components/product/two-lane-actions";
import { MobileStickyBuyBar } from "@/components/product/mobile-sticky-buy-bar";
import { ProductSpecTabs } from "@/components/product/product-spec-tabs";
import {
  buildPdpTrustItems,
  PdpAssistStrip,
  type PdpTrustItem,
} from "@/components/product/product-trust-strip";
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
  useComments,
  useFlatCategories,
  useProduct,
} from "@/features/catalog/queries";
import { categoryHref } from "@/config/nav-groups";
import {
  filterEditorialDescription,
  hasRenderableSpecs,
  pickKeySpecTeasers,
} from "@/lib/pdp-description";
import { cn, formatNumber, formatToman } from "@/lib/utils";
import type { ProductDetail } from "@/types/product";

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
  const keySpecs = pickKeySpecTeasers(product.specifications, 4);
  const buyCardTrust = buildPdpTrustItems({
    warrantyText: product.warranty_text,
    isOriginal: product.is_original,
  });

  const showSpecSection =
    hasRenderableSpecs(product.specifications) ||
    Boolean(
      filterEditorialDescription(
        product.description,
        product.specifications,
        product.short_description,
      ),
    );

  const buyCardProps = {
    product,
    brandLogoUrl,
    hasPrice,
    trust: buyCardTrust,
  } as const;

  return (
    <div className="relative pb-28 lg:pb-14">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[min(48svh,420px)] max-lg:hidden"
        style={{
          background: `
            radial-gradient(42% 50% at 92% 0%, rgba(208,35,39,0.055), transparent 68%),
            radial-gradient(38% 45% at 8% 12%, rgba(94,95,94,0.04), transparent 70%),
            linear-gradient(180deg, hsl(0 0% 97.4%) 0%, transparent 100%)
          `,
        }}
      />

      {/*
        Mobile: zero inline padding so gallery/sheet are edge-to-edge without
        ever using -mx* (those fight global overflow-x-clip and clip RTL left).
        Desktop keeps Container lg:px-8.
      */}
      <Container className="pt-3 sm:pt-5 lg:pt-6 max-lg:px-0 [@media(max-height:800px)]:pt-2 [@media(max-height:800px)]:sm:pt-3 [@media(max-height:800px)]:lg:pt-3">
        <nav
          aria-label="مسیر صفحه"
          className="mb-3 flex flex-wrap items-center gap-1.5 px-5 text-xs text-muted-foreground sm:mb-5 sm:px-6 max-lg:mb-2.5 lg:px-0 [@media(max-height:800px)]:mb-2 [@media(max-height:800px)]:sm:mb-3"
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

        {/*
          Flat 3-col page grid — same tracks/gaps as the polished pre-shell hero:
            gallery 1.08fr | info 1fr | buy minmax(248px,0.76fr)
          Explicit 2 rows so buy can row-span-2 and stick through lower sections
          without the broken nested shell (1fr|0.76fr) that inflated the card.

          Mobile sticky parallax (correct pattern — no void / no RTL clip):
            • Sticky applies ONLY to the gallery block (capped square height).
            • Sheet/buy/lower are siblings that scroll over it (z-1, −mt overlap).
            • Wrapper is the sticky containing block; it does NOT inflate gallery height.
            • No −mx bleeds (padding instead) — safe under overflow-x-clip + RTL.
          `lg:contents` keeps desktop children on the page grid.
        */}
        <div
          aria-label="معرفی محصول"
          className={cn(
            "grid w-full min-w-0 max-w-full items-start gap-6 sm:gap-8 max-lg:gap-0",
            "lg:grid-cols-[minmax(0,1.08fr)_minmax(0,1fr)_minmax(248px,0.76fr)]",
            "lg:grid-rows-[auto_1fr]",
            "lg:gap-x-10 xl:gap-x-14 lg:gap-y-0",
            "[@media(max-height:800px)]:lg:gap-x-8",
          )}
        >
          <div className="w-full min-w-0 max-w-full max-lg:relative lg:contents">
            {/* Opacity-only: transform would break position:sticky. */}
            <motion.div
              className={cn(
                "w-full min-w-0 max-w-full",
                "max-lg:sticky max-lg:top-0 max-lg:z-0",
              )}
              initial={reducedMotion ? undefined : { opacity: 0 }}
              animate={reducedMotion ? undefined : { opacity: 1 }}
              transition={{ duration: 0.55, ease: easePremium }}
            >
              <ProductGallery images={product.images} alt={product.name} />
            </motion.div>

            <motion.div
              className={cn(
                "flex w-full min-w-0 max-w-full flex-col",
                /* Soft sheet slides over sticky gallery — padding gutters, never −mx */
                "relative z-[1] max-lg:-mt-5 max-lg:px-5 max-lg:pt-4 max-lg:pb-1",
                "max-lg:rounded-t-[1.35rem] max-lg:bg-white",
                "max-lg:shadow-[0_-12px_40px_-24px_rgba(94,95,94,0.35)]",
                "sm:max-lg:px-6",
                /* Desktop: restore flat column (Container owns gutters) */
                "lg:z-auto lg:mt-0 lg:rounded-none lg:bg-transparent lg:px-0 lg:pt-0 lg:pb-0 lg:shadow-none",
              )}
              initial={reducedMotion ? undefined : { opacity: 0 }}
              animate={reducedMotion ? undefined : { opacity: 1 }}
              transition={{
                duration: 0.55,
                ease: easePremium,
                delay: reducedMotion ? 0 : 0.04,
              }}
            >
            {/* Sheet grab affordance — mobile only */}
            <span
              aria-hidden
              className="mx-auto mb-4 h-1 w-9 shrink-0 rounded-full bg-steel/20 lg:hidden"
            />

            {product.discount_percent && product.discount_percent > 0 ? (
              <div className="mb-4 flex items-center justify-between gap-3 rounded-xl bg-[#D02327]/[0.07] px-3 py-2.5 lg:hidden">
                <span className="text-[12px] font-bold text-primary">
                  فروش ویژه
                </span>
                <span className="rounded-md bg-[#D02327] px-2 py-0.5 text-[11px] font-bold text-white tnum">
                  ٪{formatNumber(product.discount_percent)} تخفیف
                </span>
              </div>
            ) : null}

            {product.brand ? (
              <p className="mb-2 text-[11px] font-semibold tracking-wide text-steel lg:hidden">
                {product.brand.name}
                {product.category ? (
                  <span className="font-medium text-muted-foreground">
                    {" "}
                    · {product.category.name}
                  </span>
                ) : null}
              </p>
            ) : null}

            <h1
              className={cn(
                "text-balance font-bold tracking-tight text-foreground",
                /* Mobile: tighter, clearer hierarchy */
                "text-[1.22rem] leading-[1.45]",
                "sm:text-[1.55rem] sm:leading-[1.45]",
                /* Desktop unchanged */
                "lg:text-[1.45rem] xl:text-[1.65rem]",
                "[@media(max-height:800px)]:text-[1.2rem] [@media(max-height:800px)]:sm:text-[1.35rem]",
              )}
            >
              {product.name}
            </h1>

            {product.short_description ? (
              <p className="mt-2.5 text-sm leading-7 text-foreground/80 max-lg:mt-2 max-lg:line-clamp-3 max-lg:leading-6 [@media(max-height:800px)]:mt-2 [@media(max-height:800px)]:line-clamp-2 [@media(max-height:800px)]:leading-6">
                {product.short_description}
              </p>
            ) : null}

            {/* Meta: desktop SKU→stock; mobile stock first via order */}
            <div
              className={cn(
                "mt-3.5 flex flex-wrap items-center gap-x-3 gap-y-2 text-sm",
                "max-lg:mt-3 max-lg:gap-x-2.5 max-lg:gap-y-1.5",
                "[@media(max-height:800px)]:mt-2.5",
              )}
            >
              <span
                className={cn(
                  "rounded-md bg-secondary/65 px-2 py-0.5 text-[11px] text-muted-foreground",
                  "max-lg:order-2 max-lg:rounded-none max-lg:bg-transparent max-lg:px-0 max-lg:py-0 max-lg:text-[12px]",
                )}
              >
                کد کالا:{" "}
                <span
                  className="font-semibold text-foreground tnum max-lg:font-medium"
                  dir="ltr"
                >
                  {product.sku}
                </span>
              </span>
              <span className="max-lg:order-1">
                <StockBadge
                  status={product.stock_status}
                  available={product.availability}
                />
              </span>
            </div>

            <MobileSocialProof productId={product.id} />

            {keySpecs.length > 0 ? (
              <div
                className={cn(
                  "mt-5 rounded-xl bg-secondary/45 p-3.5 sm:p-4",
                  "ring-1 ring-steel/[0.06]",
                  /* Mobile: airier sheet block, aligned with content edges */
                  "max-lg:mt-6 max-lg:rounded-2xl max-lg:bg-secondary/40 max-lg:p-4 max-lg:pt-3.5",
                  "max-lg:ring-steel/[0.05]",
                  "[@media(max-height:800px)]:mt-3.5 [@media(max-height:800px)]:p-3",
                )}
              >
                <h2
                  className={cn(
                    "text-[11px] font-bold tracking-[0.06em] text-steel",
                    "max-lg:text-[12px] max-lg:tracking-[0.04em] max-lg:text-foreground/70",
                  )}
                >
                  ویژگی‌های کلیدی
                </h2>
                <ul
                  className={cn(
                    "mt-2.5 space-y-0 divide-y divide-steel/[0.07]",
                    "max-lg:mt-3.5",
                    "[@media(max-height:720px)]:[&_li:nth-child(n+3)]:hidden",
                  )}
                >
                  {keySpecs.map((spec) => (
                    <li
                      key={`${spec.key}-${spec.value}`}
                      className={cn(
                        "grid grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)] gap-3 py-2 text-[13px]",
                        "first:pt-0 last:pb-0",
                        /* Mobile: label | value with clear gap, no red dots */
                        "max-lg:grid-cols-[minmax(0,1fr)_minmax(0,auto)] max-lg:items-baseline max-lg:gap-x-5 max-lg:py-2.5",
                        "[@media(max-height:800px)]:py-1.5",
                      )}
                    >
                      <span className="flex items-start gap-2 font-medium text-steel max-lg:gap-0 max-lg:text-[13px] max-lg:leading-snug">
                        <span
                          aria-hidden
                          className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#D02327] max-lg:hidden"
                        />
                        {spec.key}
                      </span>
                      <span className="text-end font-semibold tracking-tight text-foreground max-lg:ps-2 max-lg:text-[13px] max-lg:leading-snug">
                        {spec.value}
                      </span>
                    </li>
                  ))}
                </ul>
                {showSpecSection ? (
                  <a
                    href="#pdp-specs-heading"
                    className={cn(
                      "mt-2.5 inline-block text-xs font-bold text-primary underline-offset-4 transition hover:underline",
                      "max-lg:mt-3.5 max-lg:border-t max-lg:border-steel/[0.08] max-lg:pt-3",
                    )}
                  >
                    مشاهده مشخصات کامل
                  </a>
                ) : null}
              </div>
            ) : null}

            <Link
              href="/contact"
              className={cn(
                "group mt-5 inline-flex min-h-10 w-full items-center justify-center gap-2.5 rounded-xl sm:min-h-11 sm:w-auto sm:justify-start sm:pe-5 sm:ps-3.5",
                "bg-secondary/55 text-[13px] font-semibold tracking-tight text-foreground",
                "ring-1 ring-inset ring-steel/[0.08]",
                "transition-[background-color,box-shadow,ring-color,color] duration-300 ease-out",
                "hover-fine:bg-white hover-fine:text-primary hover-fine:ring-primary/20",
                "hover-fine:shadow-[0_10px_28px_-22px_rgba(208,35,39,0.35)]",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35",
                "max-lg:mt-5",
                "[@media(max-height:800px)]:mt-3.5",
              )}
            >
              <span
                className={cn(
                  "grid h-8 w-8 shrink-0 place-items-center rounded-lg",
                  "bg-[#D02327]/[0.08] text-primary",
                  "ring-1 ring-inset ring-primary/10",
                  "transition-[background-color,transform] duration-300",
                  "group-hover:bg-[#D02327]/[0.12] group-hover:scale-[1.03]",
                )}
              >
                <Call set="bold" size="small" primaryColor="#D02327" />
              </span>
              مشاوره تخصصی
            </Link>

            <ProductPdfCta
              product={product}
              className="mt-4 max-lg:mt-3.5 [@media(max-height:800px)]:mt-3"
            />
            </motion.div>

            {/* Desktop sticky buy — spans both explicit rows (hero + lower).
                Opacity-only motion: transform would break position:sticky. */}
            <motion.aside
              aria-label="خرید محصول"
              className="hidden min-w-0 self-start lg:sticky lg:top-24 lg:z-[1] lg:col-start-3 lg:row-span-2 lg:block [@media(max-height:800px)]:lg:top-20"
              initial={reducedMotion ? undefined : { opacity: 0 }}
              animate={reducedMotion ? undefined : { opacity: 1 }}
              transition={{
                duration: 0.55,
                ease: easePremium,
                delay: reducedMotion ? 0 : 0.08,
              }}
            >
              <PdpBuyCard {...buyCardProps} />
            </motion.aside>

            {/* Mobile / tablet: buy card continues soft sheet */}
            <div
              className={cn(
                "relative z-[1] w-full min-w-0 max-w-full bg-white px-5 pb-6 pt-4 sm:px-6 lg:hidden",
              )}
            >
              <PdpBuyCard {...buyCardProps} />
            </div>

            {/* Lower sections share gallery+info width; buy column stays reserved */}
            <div
              className={cn(
                "relative z-[1] w-full min-w-0 max-w-full lg:col-span-2",
                "max-lg:bg-background max-lg:px-5 max-lg:pb-2 sm:max-lg:px-6",
                "lg:bg-transparent lg:px-0 lg:pb-0",
              )}
            >
              <PdpAssistStrip className="mt-7 sm:mt-8 max-lg:mt-5 [@media(max-height:800px)]:mt-5" />

              {showSpecSection ? (
                <section
                  className="mt-12 sm:mt-20 max-lg:mt-10"
                  aria-labelledby="pdp-specs-heading"
                >
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

              <section className="mt-12 sm:mt-20 max-lg:mt-10">
                <SectionHeading title="محصولات مرتبط" />
                <RelatedProducts productId={product.id} />
              </section>

              <ProductKnowledgeRail productId={product.id} />

              <section
                className="mt-12 sm:mt-20 max-lg:mt-10"
                aria-labelledby="pdp-reviews-heading"
              >
                <SectionHeading
                  id="pdp-reviews-heading"
                  title="دیدگاه کاربران"
                  subtitle="تجربهٔ واقعی خریداران — کوتاه و خوانا"
                />
                <ProductComments productId={product.id} />
              </section>

              <div className="pb-4">
                <ProductAccessoriesSlot product={product} />
              </div>
            </div>
          </div>
        </div>

        <MobileStickyBuyBar product={product} />
      </Container>
    </div>
  );
}

function MobileSocialProof({ productId }: { productId: number }) {
  const { data } = useComments(productId);
  if (!data?.length) return null;

  const avg =
    data.reduce((sum, c) => sum + (c.rating ?? 0), 0) / data.length;

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 lg:hidden">
      <span className="inline-flex items-center gap-1 rounded-full bg-secondary/70 px-2.5 py-1 text-[12px] font-bold text-foreground ring-1 ring-steel/[0.08]">
        <Star set="bold" size="small" primaryColor="#E5A100" />
        <span className="tnum">{avg.toFixed(1)}</span>
      </span>
      <a
        href="#pdp-reviews-heading"
        className="rounded-full bg-secondary/55 px-2.5 py-1 text-[12px] font-semibold text-steel ring-1 ring-steel/[0.08] transition-colors hover:text-primary"
      >
        <span className="tnum">{formatNumber(data.length)}</span> دیدگاه
      </a>
    </div>
  );
}

function PdpBuyCard({
  product,
  brandLogoUrl,
  hasPrice,
  trust,
}: {
  product: ProductDetail;
  brandLogoUrl: string | null | undefined;
  hasPrice: boolean;
  trust: PdpTrustItem[];
}) {
  return (
    <div
      className={cn(
        "relative flex min-h-[22rem] flex-col overflow-hidden rounded-[1.25rem] bg-white",
        "px-3.5 sm:min-h-[23.5rem] sm:px-4",
        "ring-1 ring-steel/[0.09]",
        "shadow-[0_20px_48px_-28px_rgba(94,95,94,0.42)]",
        /* Mobile: softer, less towering — sticky bar owns the primary CTA chrome */
        "max-lg:min-h-0 max-lg:rounded-2xl max-lg:shadow-[0_12px_32px_-24px_rgba(94,95,94,0.35)]",
        "[@media(max-height:800px)]:min-h-0",
      )}
    >
      <span
        aria-hidden
        className="absolute inset-x-0 top-0 h-[2.5px] bg-gradient-to-l from-[#D02327] via-[#D02327]/75 to-transparent"
      />

      <div className="border-b border-steel/[0.08] px-0 pb-3.5 pt-4 sm:pb-4 sm:pt-[1.15rem] [@media(max-height:800px)]:pb-3 [@media(max-height:800px)]:pt-3.5">
        {product.brand ? (
          <>
            <PdpBrandMark
              brand={product.brand}
              logoUrl={brandLogoUrl}
              density="quiet"
            />
            {product.category ? (
              <p className="mt-2.5 truncate text-[11px] leading-none text-steel">
                دسته:{" "}
                <Link
                  href={categoryHref(product.category)}
                  className="font-medium text-foreground transition-colors hover:text-primary"
                >
                  {product.category.name}
                </Link>
              </p>
            ) : null}
          </>
        ) : product.category ? (
          <>
            <p className="text-[10px] font-medium leading-none text-steel">
              دسته
            </p>
            <Link
              href={categoryHref(product.category)}
              className="mt-1.5 inline-block text-[13px] font-semibold tracking-tight text-foreground transition-colors hover:text-primary"
            >
              {product.category.name}
            </Link>
          </>
        ) : (
          <p className="text-[12px] font-medium text-steel">خرید محصول</p>
        )}
      </div>

      <div className="border-b border-steel/[0.08] py-3.5 sm:py-4 [@media(max-height:800px)]:py-3">
        {hasPrice ? (
          <div>
            <p className="text-[10px] font-medium tracking-[0.04em] text-steel">
              قیمت
            </p>
            {product.original_price && (
              <div className="mt-1.5 flex flex-wrap items-center gap-2">
                <span className="text-xs text-muted-foreground line-through tnum">
                  {formatToman(product.original_price)}
                </span>
                {product.discount_percent ? (
                  <Badge variant="primary">٪{product.discount_percent}</Badge>
                ) : null}
              </div>
            )}
            <div className="mt-1.5 text-[1.28rem] font-bold leading-none tracking-tight text-foreground tnum sm:text-[1.36rem] [@media(max-height:800px)]:text-[1.2rem]">
              {formatToman(product.base_price)}
            </div>
          </div>
        ) : (
          <div>
            <p className="text-[10px] font-medium tracking-[0.04em] text-steel">
              قیمت این محصول
            </p>
            <p className="mt-1.5 text-[15px] font-bold leading-snug text-primary">
              با استعلام تعیین می‌شود
            </p>
          </div>
        )}
      </div>

      <div
        className={cn(
          "py-3.5 sm:py-4 [@media(max-height:800px)]:py-3",
          trust.length === 0 && "pb-4 sm:pb-5",
        )}
      >
        <TwoLaneActions product={product} />
      </div>

      {trust.length > 0 ? (
        <ul className="mt-auto divide-y divide-steel/[0.08] border-t border-steel/[0.08] pb-2 sm:pb-2.5">
          {trust.map(({ key, title, desc, Icon }) => (
            <li
              key={key}
              className="flex items-center gap-2.5 py-2.5 [@media(max-height:800px)]:py-2"
            >
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-[#D02327]/[0.08]">
                <Icon set="bold" size="small" primaryColor="#D02327" />
              </span>
              <div className="min-w-0 leading-tight">
                <p className="truncate text-[12px] font-bold tracking-tight text-foreground">
                  {title}
                </p>
                <p className="mt-0.5 truncate text-[10px] font-medium text-steel">
                  {desc}
                </p>
              </div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function StockBadge({ status, available }: { status: string; available: boolean }) {
  return <Badge variant={available ? "success" : "muted"}>{status}</Badge>;
}

function DetailSkeleton() {
  return (
    <Container className="py-6 sm:py-8 [@media(max-height:800px)]:py-4">
      <div className="grid items-start gap-6 sm:gap-8 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,1fr)_minmax(248px,0.76fr)] lg:grid-rows-[auto_1fr] lg:gap-x-10 xl:gap-x-14 lg:gap-y-0">
        <Skeleton className="mx-auto aspect-square w-full max-w-[min(100%,32rem)] rounded-2xl max-h-[min(32rem,calc(100svh-9.25rem))]" />
        <div className="space-y-3">
          <Skeleton className="h-7 w-4/5" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="mt-2 h-28 w-full rounded-xl" />
          <Skeleton className="h-10 w-40 rounded-xl" />
        </div>
        <Skeleton className="hidden h-80 w-full rounded-[1.25rem] lg:col-start-3 lg:row-span-2 lg:block" />
        <Skeleton className="h-14 w-full rounded-[1.1rem] lg:col-span-2" />
      </div>
    </Container>
  );
}
