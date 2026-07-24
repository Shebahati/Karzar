"use client";

import { useRef } from "react";
import { ChevronLeft, ChevronRight } from "react-iconly";
import { ProductCard, ProductCardSkeleton } from "@/components/product/product-card";
import { useMotionSafe } from "@/lib/use-motion-safe";
import { cn } from "@/lib/utils";
import type { ProductSummary } from "@/types/product";

export function ProductCarousel({
  products,
  isLoading,
  variant = "default",
}: {
  products: ProductSummary[];
  isLoading?: boolean;
  variant?: "default" | "featured" | "deal";
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const motionSafe = useMotionSafe();

  const step = (dir: 1 | -1) => {
    const el = trackRef.current;
    if (!el) return;
    const amount = 300;
    const isRtl = getComputedStyle(el).direction === "rtl";
    el.scrollBy({ left: isRtl ? -dir * amount : dir * amount, behavior: "smooth" });
  };

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

  return (
    <div
      className={cn(
        "relative",
        variant === "featured" && "rounded-3xl bg-gradient-to-l from-secondary/80 to-transparent p-1 sm:p-2",
        variant === "deal" &&
          "rounded-3xl border border-primary/10 bg-[linear-gradient(120deg,rgba(194,32,38,0.04),rgba(94,95,94,0.06))] p-3 sm:p-4",
      )}
    >
      <div ref={trackRef} className="no-scrollbar flex gap-3 overflow-x-auto pb-2 sm:gap-4">
        {products.map((p) => (
          <div key={p.id} className={cn("shrink-0", cardWidth)}>
            <ProductCard product={p} />
          </div>
        ))}
      </div>

      {motionSafe && products.length > 3 && (
        <>
          <button
            type="button"
            aria-label="بعدی"
            onClick={() => step(1)}
            className="absolute -start-3 top-1/2 z-10 hidden h-11 w-11 -translate-y-1/2 place-items-center rounded-full border border-border/50 bg-card/95 text-steel shadow-card backdrop-blur hover:text-primary lg:grid"
          >
            <ChevronRight set="light" />
          </button>
          <button
            type="button"
            aria-label="قبلی"
            onClick={() => step(-1)}
            className="absolute -end-3 top-1/2 z-10 hidden h-11 w-11 -translate-y-1/2 place-items-center rounded-full border border-border/50 bg-card/95 text-steel shadow-card backdrop-blur hover:text-primary lg:grid"
          >
            <ChevronLeft set="light" />
          </button>
        </>
      )}
    </div>
  );
}
