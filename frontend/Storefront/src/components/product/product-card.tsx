"use client";

import { useState } from "react";
import Link from "next/link";
import { Document } from "react-iconly";
import { CardAddToCartCta } from "@/components/product/card-add-to-cart-cta";
import { ProductPlaceholder } from "@/components/ui/product-placeholder";
import { SafeImage } from "@/components/ui/safe-image";
import { CONTENT_IMAGE_QUALITY, lcpImageProps } from "@/lib/cwv";
import { toSafeNextImageSrc } from "@/lib/image-remote-patterns";
import { useCanHover } from "@/lib/use-motion-safe";
import { cn, formatNumber, formatToman } from "@/lib/utils";
import { productPath } from "@/lib/product-url";
import { useCartStore } from "@/store/cart-store";
import type { ProductImage, ProductSummary } from "@/types/product";

/** Ordered unique image URLs for card media (thumbnail first, then gallery). */
function resolveCardImages(product: ProductSummary): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  const push = (url: string | null | undefined) => {
    const safe = toSafeNextImageSrc(url);
    if (!safe || seen.has(safe)) return;
    seen.add(safe);
    out.push(safe);
  };

  push(product.thumbnail);

  if (product.images?.length) {
    const sorted = [...product.images].sort(
      (a: ProductImage, b: ProductImage) =>
        Number(b.is_primary) - Number(a.is_primary) || a.id - b.id,
    );
    for (const img of sorted) push(img.url);
  }

  return out;
}

function stockCue(product: ProductSummary): { label: string; tone: "ok" | "low" | "out" } | null {
  if (!product.availability || product.stock_status === "out_of_stock" || product.stock_status === "ناموجود") {
    return { label: "ناموجود", tone: "out" };
  }
  const status = product.stock_status;
  if (status === "موجودی محدود" || status === "low_stock") {
    return { label: "موجودی محدود", tone: "low" };
  }
  if (status === "موجود" || status === "in_stock") {
    return { label: "موجود", tone: "ok" };
  }
  if (status) return { label: status, tone: "ok" };
  return null;
}

export function ProductCard({
  product,
  className,
  priority = false,
  variant = "default",
}: {
  product: ProductSummary;
  className?: string;
  /** Mark above-the-fold PLP/home cards as LCP candidates. */
  priority?: boolean;
  /** `deal` = soft white card for discounts strip. */
  variant?: "default" | "deal";
}) {
  const isDeal = variant === "deal";
  const addToQuote = useCartStore((s) => s.addToQuote);
  const hasPrice = product.base_price != null;
  const outOfStock = !product.availability;
  const [addedFlash, setAddedFlash] = useState(false);
  const canHover = useCanHover();
  const images = resolveCardImages(product);
  // Hover-swap second image only on fine pointers — halves decode work on phones.
  const hasMultiImage = canHover && images.length > 1;
  const cue = stockCue(product);
  const discount = product.discount_percent && product.discount_percent > 0
    ? product.discount_percent
    : null;

  const flashAdded = () => {
    setAddedFlash(true);
    window.setTimeout(() => setAddedFlash(false), 3800);
  };

  const quickAddQuote = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (outOfStock) return;
    addToQuote(product);
    flashAdded();
  };

  const imageProps = priority
    ? lcpImageProps()
    : { loading: "lazy" as const, quality: CONTENT_IMAGE_QUALITY };

  return (
    <Link
      href={productPath(product)}
      className={cn(
        "group relative flex h-full flex-col overflow-hidden rounded-2xl bg-card",
        "transition-[box-shadow,transform] duration-300 ease-out",
        isDeal
          ? "rounded-[1.15rem] bg-white shadow-[0_6px_18px_-10px_rgba(94,95,94,0.35)] md:hover:-translate-y-0.5 md:hover:shadow-[0_12px_28px_-14px_rgba(94,95,94,0.4)]"
          : "md:hover:-translate-y-0.5 md:hover:shadow-[0_12px_28px_-20px_rgba(94,95,94,0.45)]",
        className,
      )}
    >
      {/* Media */}
      <div
        className={cn(
          "relative aspect-square overflow-hidden",
          isDeal ? "bg-white" : "bg-[#E9E8E7]",
        )}
      >
        {images.length === 0 ? (
          <ProductPlaceholder name={product.name} sku={product.sku} />
        ) : hasMultiImage ? (
          <>
            <SafeImage
              src={images[0]!}
              alt={product.name}
              fill
              sizes="(max-width: 768px) 50vw, 25vw"
              className="object-cover object-center transition-opacity duration-300 ease-out group-hover:opacity-0"
              fallback={<ProductPlaceholder name={product.name} sku={product.sku} />}
              {...imageProps}
            />
            <SafeImage
              src={images[1]!}
              alt=""
              aria-hidden
              fill
              sizes="(max-width: 768px) 50vw, 25vw"
              className="object-cover object-center opacity-0 transition-opacity duration-300 ease-out group-hover:opacity-100"
              loading="lazy"
              quality={CONTENT_IMAGE_QUALITY}
              fallback={null}
            />
          </>
        ) : (
          <SafeImage
            src={images[0]!}
            alt={product.name}
            fill
            sizes="(max-width: 768px) 50vw, 25vw"
            className="object-cover object-center transition-transform duration-300 ease-out md:group-hover:scale-[1.07]"
            fallback={<ProductPlaceholder name={product.name} sku={product.sku} />}
            {...imageProps}
          />
        )}

        {/* Deal: discount chip on media; default keeps image-corner badge too */}
        {discount ? (
          <span
            className={cn(
              "absolute start-3 top-3 font-bold text-white",
              isDeal
                ? "rounded-md bg-[#D02327] px-2 py-1 text-[11px] leading-none"
                : "rounded-md bg-[#D02327] px-2 py-1 text-[11px]",
            )}
          >
            ٪{formatNumber(discount)} تخفیف
          </span>
        ) : null}

        {outOfStock && (
          <div className="absolute inset-0 grid place-items-center bg-[#5E5F5E]/50">
            <span className="rounded-md bg-[#1a1a1a] px-3.5 py-1.5 text-xs font-bold text-white">
              ناموجود
            </span>
          </div>
        )}

        {addedFlash && (
          <div className="absolute inset-x-3 bottom-3 rounded-lg bg-success px-3 py-1.5 text-center text-[11px] font-bold text-success-foreground">
            {hasPrice ? "به سبد اضافه شد" : "به استعلام اضافه شد"}
          </div>
        )}
      </div>

      {/* Footer — always stacked: price (full width) → ATC (full width). Height stable; price never fights CTA. */}
      {isDeal ? (
        <div className="flex flex-1 flex-col gap-2 px-3 pb-3.5 pt-2.5 sm:px-3.5 sm:pb-4">
          <h3 className="line-clamp-2 min-h-[2.4rem] text-[12.5px] font-semibold leading-5 text-[#1a1a1a] transition-colors duration-300 group-hover:text-[#D02327] sm:min-h-[2.6rem] sm:text-[13px] sm:leading-5">
            {product.name}
          </h3>

          <div className="mt-auto flex flex-col gap-2.5 pt-0.5">
            {/* Row 1 — price block, full width */}
            <div className="w-full min-w-0">
              {hasPrice ? (
                <div className="flex flex-col gap-1">
                  {product.original_price ? (
                    <span className="block whitespace-nowrap text-[11px] font-medium text-[#D02327]/55 line-through tnum">
                      {formatToman(product.original_price)}
                    </span>
                  ) : null}
                  <span className="block whitespace-nowrap text-[14px] font-bold leading-none tracking-tight text-[#1a1a1a] tnum sm:text-[15px]">
                    {formatToman(product.base_price)}
                  </span>
                </div>
              ) : (
                <span className="block text-sm font-bold text-[#D02327]">استعلام قیمت</span>
              )}
            </div>

            {/* Row 2 — ATC, full width / end-aligned */}
            {hasPrice ? (
              <CardAddToCartCta
                product={product}
                disabled={outOfStock}
                onAdded={flashAdded}
              />
            ) : null}
          </div>
        </div>
      ) : (
        <div className="flex flex-1 flex-col gap-2 px-3.5 pb-3.5 pt-3 sm:px-4 sm:pb-4">
          <div className="flex items-center justify-between gap-2">
            {product.brand ? (
              <span className="truncate text-[11px] font-medium tracking-normal text-[#5E5F5E]">
                {product.brand.name}
              </span>
            ) : (
              <span className="text-[11px] font-medium text-[#5E5F5E]/50">کارزار</span>
            )}

            {cue && !outOfStock ? (
              <span
                className={cn(
                  "inline-flex shrink-0 items-center gap-1.5 text-[10px] font-medium",
                  cue.tone === "low" ? "text-[#D02327]" : "text-[#5E5F5E]/70",
                )}
              >
                <span
                  aria-hidden
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    cue.tone === "low" ? "bg-[#D02327]" : "bg-success",
                  )}
                />
                {cue.label}
              </span>
            ) : null}
          </div>

          <h3 className="line-clamp-2 min-h-[2.5rem] text-[13px] font-semibold leading-5 text-[#1a1a1a] transition-colors duration-300 group-hover:text-[#D02327] sm:min-h-[2.75rem] sm:text-sm sm:leading-6">
            {product.name}
          </h3>

          <div className="mt-auto flex flex-col gap-2.5 pt-1">
            {/* Row 1 — price block, full width */}
            <div className="w-full min-w-0">
              {hasPrice ? (
                <div className="flex flex-col gap-1">
                  {product.original_price ? (
                    <span className="block whitespace-nowrap text-[11px] font-medium text-[#D02327]/55 line-through tnum">
                      {formatToman(product.original_price)}
                    </span>
                  ) : null}
                  <span className="block whitespace-nowrap text-[15px] font-bold leading-none tracking-tight text-[#1a1a1a] tnum sm:text-base">
                    {formatToman(product.base_price)}
                  </span>
                </div>
              ) : (
                <div>
                  <span className="block text-[10px] font-medium text-[#5E5F5E]">
                    بدون قیمت ثابت
                  </span>
                  <span className="mt-0.5 block text-sm font-bold text-[#D02327]">استعلام قیمت</span>
                </div>
              )}
            </div>

            {/* Row 2 — ATC / quote, full width / end-aligned */}
            {hasPrice ? (
              <CardAddToCartCta
                product={product}
                disabled={outOfStock}
                onAdded={flashAdded}
              />
            ) : (
              <div className="flex h-8 w-full items-center justify-end">
                <button
                  type="button"
                  onClick={quickAddQuote}
                  disabled={outOfStock}
                  aria-label="افزودن به استعلام"
                  className={cn(
                    "grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#F3F3F3] text-[#5E5F5E]",
                    "transition-[transform,background-color,color] duration-300 ease-out",
                    "hover:text-[#D02327] active:scale-95",
                    "disabled:pointer-events-none disabled:opacity-35",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D02327]/35",
                  )}
                >
                  <Document size="small" set="bold" primaryColor="currentColor" />
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </Link>
  );
}

export function ProductCardSkeleton({
  variant = "default",
}: {
  variant?: "default" | "deal";
}) {
  const isDeal = variant === "deal";
  return (
    <div
      className={cn(
        "overflow-hidden rounded-2xl bg-card",
        isDeal && "rounded-[1.15rem] bg-white shadow-[0_6px_18px_-10px_rgba(94,95,94,0.35)]",
      )}
    >
      <div className={cn("aspect-square shimmer", isDeal ? "bg-[#F3F3F3]" : "bg-[#E9E8E7]")} />
      <div className={cn("space-y-2.5", isDeal ? "px-3 py-3" : "px-3.5 py-3 sm:px-4 sm:pb-4")}>
        {!isDeal ? (
          <div className="flex items-center justify-between">
            <div className="h-2.5 w-16 rounded bg-muted" />
            <div className="h-2.5 w-12 rounded bg-muted" />
          </div>
        ) : null}
        <div className="h-4 w-full rounded bg-muted" />
        <div className="h-4 w-2/3 rounded bg-muted" />
        <div className="space-y-2.5 pt-1">
          <div className="h-5 w-28 rounded bg-muted" />
          <div className="flex justify-end">
            <div className="h-8 w-8 rounded-lg bg-muted" />
          </div>
        </div>
      </div>
    </div>
  );
}
