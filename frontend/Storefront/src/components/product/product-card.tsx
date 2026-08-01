"use client";

import { useState } from "react";
import Link from "next/link";
import { Buy, Document } from "react-iconly";
import { ProductPlaceholder } from "@/components/ui/product-placeholder";
import { SafeImage } from "@/components/ui/safe-image";
import { CONTENT_IMAGE_QUALITY, lcpImageProps } from "@/lib/cwv";
import { toSafeNextImageSrc } from "@/lib/image-remote-patterns";
import { cn, formatToman } from "@/lib/utils";
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
}: {
  product: ProductSummary;
  className?: string;
  /** Mark above-the-fold PLP/home cards as LCP candidates. */
  priority?: boolean;
}) {
  const addToCart = useCartStore((s) => s.addToCart);
  const addToQuote = useCartStore((s) => s.addToQuote);
  const hasPrice = product.base_price != null;
  const outOfStock = !product.availability;
  const [addedFlash, setAddedFlash] = useState(false);
  const images = resolveCardImages(product);
  const hasMultiImage = images.length > 1;
  const cue = stockCue(product);

  const quickAdd = (e: React.MouseEvent) => {
    e.preventDefault();
    if (outOfStock) return;
    if (hasPrice) addToCart(product);
    else addToQuote(product);
    setAddedFlash(true);
    window.setTimeout(() => setAddedFlash(false), 1800);
  };

  const imageProps = priority
    ? lcpImageProps()
    : { loading: "lazy" as const, quality: CONTENT_IMAGE_QUALITY };

  return (
    <Link
      href={productPath(product)}
      className={cn(
        "group relative flex h-full flex-col overflow-hidden rounded-2xl bg-card",
        "transition-[box-shadow,transform] duration-[350ms] ease-out",
        "hover:-translate-y-0.5 hover:shadow-[0_12px_28px_-20px_rgba(94,95,94,0.45)]",
        className,
      )}
    >
      {/* Media */}
      <div className="relative aspect-square overflow-hidden bg-[#E9E8E7]">
        {images.length === 0 ? (
          <ProductPlaceholder name={product.name} sku={product.sku} />
        ) : hasMultiImage ? (
          <>
            <SafeImage
              src={images[0]!}
              alt={product.name}
              fill
              sizes="(max-width: 768px) 50vw, 25vw"
              className="object-cover transition-opacity duration-[350ms] ease-out group-hover:opacity-0"
              fallback={<ProductPlaceholder name={product.name} sku={product.sku} />}
              {...imageProps}
            />
            <SafeImage
              src={images[1]!}
              alt=""
              aria-hidden
              fill
              sizes="(max-width: 768px) 50vw, 25vw"
              className="object-cover opacity-0 transition-opacity duration-[350ms] ease-out group-hover:opacity-100"
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
            className="object-cover transition-transform duration-[350ms] ease-out will-change-transform group-hover:scale-[1.07]"
            fallback={<ProductPlaceholder name={product.name} sku={product.sku} />}
            {...imageProps}
          />
        )}

        {product.discount_percent ? (
          <span className="absolute start-3 top-3 rounded-md bg-[#D02327] px-2 py-1 text-[11px] font-bold text-white">
            ٪{product.discount_percent} تخفیف
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

      {/* Footer */}
      <div className="flex flex-1 flex-col gap-2 px-3.5 pb-3.5 pt-3 sm:px-4 sm:pb-4">
        <div className="flex items-center justify-between gap-2">
          {product.brand ? (
            <span className="truncate text-[11px] font-medium tracking-wide text-[#5E5F5E]">
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

        <h3 className="line-clamp-2 min-h-[2.5rem] text-[13px] font-semibold leading-5 text-[#1a1a1a] transition-colors duration-[350ms] group-hover:text-[#D02327] sm:min-h-[2.75rem] sm:text-sm sm:leading-6">
          {product.name}
        </h3>

        <div className="mt-auto flex items-end justify-between gap-3 pt-1">
          <div className="min-w-0">
            {hasPrice ? (
              <>
                {product.original_price ? (
                  <span className="block text-[11px] text-[#5E5F5E]/60 line-through tnum">
                    {formatToman(product.original_price)}
                  </span>
                ) : null}
                <span className="block text-[15px] font-bold leading-none tracking-tight text-[#1a1a1a] tnum sm:text-base">
                  {formatToman(product.base_price)}
                </span>
              </>
            ) : (
              <div>
                <span className="block text-[10px] font-medium text-[#5E5F5E]">
                  بدون قیمت ثابت
                </span>
                <span className="mt-0.5 block text-sm font-bold text-[#D02327]">استعلام قیمت</span>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={quickAdd}
            disabled={outOfStock}
            aria-label={hasPrice ? "افزودن به سبد خرید" : "افزودن به استعلام"}
            className={cn(
              "grid h-9 w-9 shrink-0 place-items-center rounded-lg transition-[transform,background-color] duration-[350ms] ease-out",
              "active:scale-95 disabled:pointer-events-none disabled:opacity-35",
              hasPrice
                ? "bg-[#D02327] text-white"
                : "bg-[#F3F3F3] text-[#5E5F5E] hover:text-[#D02327]",
            )}
          >
            {hasPrice ? (
              <Buy size="small" set="bold" primaryColor="currentColor" />
            ) : (
              <Document size="small" set="bold" primaryColor="currentColor" />
            )}
          </button>
        </div>
      </div>
    </Link>
  );
}

export function ProductCardSkeleton() {
  return (
    <div className="overflow-hidden rounded-2xl bg-card">
      <div className="aspect-square shimmer bg-[#E9E8E7]" />
      <div className="space-y-2.5 px-3.5 py-3 sm:px-4 sm:pb-4">
        <div className="flex items-center justify-between">
          <div className="h-2.5 w-16 rounded bg-muted" />
          <div className="h-2.5 w-12 rounded bg-muted" />
        </div>
        <div className="h-4 w-full rounded bg-muted" />
        <div className="h-4 w-2/3 rounded bg-muted" />
        <div className="flex items-end justify-between pt-1">
          <div className="h-5 w-24 rounded bg-muted" />
          <div className="h-9 w-9 rounded-lg bg-muted" />
        </div>
      </div>
    </div>
  );
}
