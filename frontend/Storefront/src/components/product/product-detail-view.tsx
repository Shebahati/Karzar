"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
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
import { SectionHeading } from "@/components/home/section-heading";
import { useFlatCategories, useProduct } from "@/features/catalog/queries";
import { categoryHref } from "@/config/nav-groups";
import {
  filterEditorialDescription,
  hasRenderableSpecs,
} from "@/lib/pdp-description";
import { formatToman } from "@/lib/utils";

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

  const showSpecSection =
    hasRenderableSpecs(product.specifications) ||
    Boolean(
      filterEditorialDescription(
        product.description,
        product.specifications,
        product.short_description,
      ),
    );

  return (
    <Container className="pt-6 pb-24 lg:py-10">
      <nav className="mb-6 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
        <Link href="/" className="hover:text-primary">
          خانه
        </Link>
        <ChevronLeft size="small" set="light" />
        <Link href="/catalog" className="hover:text-primary">
          فروشگاه
        </Link>
        {crumbs.length > 0
          ? crumbs.map((crumb) => (
              <span key={crumb.id} className="flex items-center gap-1.5">
                <ChevronLeft size="small" set="light" />
                <Link href={categoryHref(crumb)} className="hover:text-primary">
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

      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <ProductGallery images={product.images} alt={product.name} />
        </div>

        <div className="flex flex-col">
          {product.brand && (
            <Link
              href={
                product.brand.slug
                  ? `/brands/${product.brand.slug}`
                  : `/catalog?brand=${product.brand.id}`
              }
              className="text-sm font-bold text-primary"
            >
              {product.brand.name}
              {product.brand.country ? ` · ${product.brand.country}` : ""}
            </Link>
          )}
          <h1 className="mt-2 text-2xl font-bold leading-relaxed text-foreground">
            {product.name}
          </h1>

          {product.short_description ? (
            <p className="mt-3 text-sm leading-8 text-foreground/90">
              {product.short_description}
            </p>
          ) : null}

          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
            <span className="text-muted-foreground" dir="ltr">
              کد کالا: {product.sku}
            </span>
            <StockBadge status={product.stock_status} available={product.availability} />
          </div>

          <div className="mt-6 rounded-2xl bg-secondary/60 p-5">
            <div className="mb-4 flex items-end justify-between">
              {hasPrice ? (
                <div>
                  {product.original_price && (
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground line-through tnum">
                        {formatToman(product.original_price)}
                      </span>
                      {product.discount_percent && (
                        <Badge variant="primary">٪{product.discount_percent}</Badge>
                      )}
                    </div>
                  )}
                  <div className="mt-1 text-2xl font-bold text-foreground tnum">
                    {formatToman(product.base_price)}
                  </div>
                </div>
              ) : (
                <div>
                  <p className="text-sm text-muted-foreground">قیمت این محصول</p>
                  <p className="mt-1 text-xl font-bold text-primary">با استعلام تعیین می‌شود</p>
                </div>
              )}
            </div>
            <TwoLaneActions product={product} />
          </div>

          <ProductTrustStrip
            className="mt-5"
            warrantyText={product.warranty_text}
            isOriginal={product.is_original}
          />

          <ProductPdfCta product={product} />
        </div>
      </div>

      {showSpecSection ? (
        <section className="mt-12" aria-labelledby="pdp-specs-heading">
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

      <section className="mt-12">
        <SectionHeading title="دیدگاه کاربران" />
        <ProductComments productId={product.id} />
      </section>

      <section className="mt-12 pb-4">
        <SectionHeading title="محصولات مرتبط" />
        <RelatedProducts productId={product.id} />
      </section>

      <MobileStickyBuyBar product={product} />
    </Container>
  );
}

function StockBadge({ status, available }: { status: string; available: boolean }) {
  return <Badge variant={available ? "success" : "muted"}>{status}</Badge>;
}

function DetailSkeleton() {
  return (
    <Container className="py-10">
      <div className="grid gap-8 lg:grid-cols-2">
        <Skeleton className="aspect-square rounded-2xl" />
        <div className="space-y-4">
          <Skeleton className="h-5 w-24" />
          <Skeleton className="h-8 w-3/4" />
          <Skeleton className="h-5 w-1/2" />
          <Skeleton className="h-40 w-full rounded-2xl" />
          <Skeleton className="h-24 w-full rounded-2xl" />
        </div>
      </div>
    </Container>
  );
}
