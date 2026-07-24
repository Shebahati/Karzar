"use client";

import { useRef } from "react";
import { ChevronLeft, ChevronRight } from "react-iconly";
import { ProductCard, ProductCardSkeleton } from "@/components/product/product-card";
import { useMotionSafe } from "@/lib/use-motion-safe";
import type { ProductSummary } from "@/types/product";

export function ProductCarousel({
  products,
  isLoading,
}: {
  products: ProductSummary[];
  isLoading?: boolean;
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const motionSafe = useMotionSafe();

  const step = (dir: 1 | -1) => {
    const el = trackRef.current;
    if (!el) return;
    const amount = 280;
    const isRtl = getComputedStyle(el).direction === "rtl";
    // In RTL, positive scrollLeft moves opposite to LTR — invert so "next" feels natural.
    el.scrollBy({ left: isRtl ? -dir * amount : dir * amount, behavior: "smooth" });
  };

  if (isLoading) {
    return (
      <div className="flex gap-3 overflow-hidden sm:gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="w-[210px] shrink-0 sm:w-[250px]">
            <ProductCardSkeleton />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="relative">
      <div ref={trackRef} className="no-scrollbar flex gap-3 overflow-x-auto pb-2 sm:gap-4">
        {products.map((p) => (
          <div key={p.id} className="w-[210px] shrink-0 sm:w-[250px]">
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
            className="absolute -start-3 top-1/2 hidden h-11 w-11 -translate-y-1/2 place-items-center rounded-full bg-white text-foreground shadow-card hover:text-primary lg:grid"
          >
            <ChevronRight set="light" />
          </button>
          <button
            type="button"
            aria-label="قبلی"
            onClick={() => step(-1)}
            className="absolute -end-3 top-1/2 hidden h-11 w-11 -translate-y-1/2 place-items-center rounded-full bg-white text-foreground shadow-card hover:text-primary lg:grid"
          >
            <ChevronLeft set="light" />
          </button>
        </>
      )}
    </div>
  );
}
