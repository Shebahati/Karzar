"use client";

import { ProductCard, ProductCardSkeleton } from "@/components/product/product-card";
import { AutoCarousel } from "@/components/ui/auto-carousel";
import { isPlpLcpIndex } from "@/lib/cwv";
import { cn } from "@/lib/utils";
import type { ProductSummary } from "@/types/product";

export function ProductCarousel({
  products,
  isLoading,
  variant = "default",
  autoPlay = true,
  intervalMs = 3400,
}: {
  products: ProductSummary[];
  isLoading?: boolean;
  variant?: "default" | "featured" | "deal";
  autoPlay?: boolean;
  intervalMs?: number;
}) {
  const cardWidth =
    variant === "featured"
      ? "w-[230px] sm:w-[270px]"
      : variant === "deal"
        ? "w-[220px] sm:w-[260px]"
        : "w-[210px] sm:w-[250px]";

  if (isLoading) {
    return (
      <div className="flex gap-3 overflow-hidden sm:gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className={cn("shrink-0", cardWidth)}>
            <ProductCardSkeleton />
          </div>
        ))}
      </div>
    );
  }

  // Duplicate for seamless infinite feel when short lists
  const loop =
    products.length > 0 && products.length < 8
      ? [...products, ...products, ...products]
      : products.length >= 8
        ? [...products, ...products]
        : products;

  if (loop.length === 0) return null;

  return (
    <div
      className={cn(
        variant === "featured" &&
          "rounded-3xl bg-gradient-to-l from-secondary/80 to-transparent p-1 sm:p-2",
        variant === "deal" &&
          "rounded-3xl border border-primary/10 bg-[linear-gradient(120deg,rgba(208,35,39,0.05),rgba(94,95,94,0.06))] p-3 sm:p-4",
      )}
    >
      <AutoCarousel
        autoPlay={autoPlay && products.length > 1}
        intervalMs={intervalMs}
        itemClassName={cardWidth}
        gapClass="gap-3 sm:gap-4"
        trackClassName="pb-2"
        showControls={products.length > 2}
        controlClassName="h-11 w-11"
      >
        {loop.map((p, i) => (
          <ProductCard key={`${p.id}-${i}`} product={p} priority={isPlpLcpIndex(i, 2)} />
        ))}
      </AutoCarousel>
    </div>
  );
}
