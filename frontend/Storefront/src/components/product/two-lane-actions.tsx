"use client";

import { useState } from "react";
import Link from "next/link";
import { Buy, Call, Document, Plus } from "react-iconly";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useCartStore } from "@/store/cart-store";
import type { ProductDetail, ProductSummary } from "@/types/product";

/**
 * Two-lane purchase:
 * - priced → add to cart
 * - price-less → add to inquiry/quote (no fake SMS success)
 *
 * Compact density: denser qty/CTA chrome for the sticky buy card,
 * with clear vertical rhythm (not crushed).
 */
export function TwoLaneActions({
  product,
  onAdded,
}: {
  product: ProductDetail;
  onAdded?: (lane: "cart" | "quote") => void;
}) {
  const addToCart = useCartStore((s) => s.addToCart);
  const addToQuote = useCartStore((s) => s.addToQuote);
  const [qty, setQty] = useState(1);
  const [justAdded, setJustAdded] = useState<"cart" | "quote" | null>(null);

  const hasPrice = product.base_price != null;
  const outOfStock = !product.availability;

  const summary: ProductSummary = {
    id: product.id,
    sku: product.sku,
    name: product.name,
    thumbnail: product.thumbnail,
    base_price: product.base_price,
    original_price: product.original_price,
    discount_percent: product.discount_percent,
    stock_status: product.stock_status,
    availability: product.availability,
    is_original: product.is_original,
    category: product.category,
    brand: product.brand,
  };

  const handleAdd = (lane: "cart" | "quote") => {
    if (lane === "cart") addToCart(summary, qty);
    else addToQuote(summary, qty);
    setJustAdded(lane);
    onAdded?.(lane);
    window.setTimeout(() => setJustAdded(null), 4000);
  };

  return (
    <div className="flex flex-col gap-3.5">
      {!outOfStock && (
        <div className="flex items-center justify-between gap-3">
          <span className="text-[12px] font-medium text-steel">تعداد</span>
          <div
            className={cn(
              "inline-flex items-center gap-0.5 rounded-lg bg-secondary/70 p-0.5",
              "ring-1 ring-steel/[0.1]",
            )}
          >
            <button
              type="button"
              aria-label="کاهش"
              onClick={() => setQty((q) => Math.max(1, q - 1))}
              className={cn(
                "grid h-8 w-8 place-items-center rounded-md bg-white",
                "text-base font-medium leading-none text-foreground",
                "shadow-[0_1px_2px_rgba(94,95,94,0.08)]",
                "transition-colors hover:text-[#D02327]",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35",
              )}
            >
              −
            </button>
            <span className="min-w-8 select-none text-center text-[13px] font-bold tabular-nums text-foreground tnum">
              {qty}
            </span>
            <button
              type="button"
              aria-label="افزایش"
              onClick={() => setQty((q) => q + 1)}
              className={cn(
                "grid h-8 w-8 place-items-center rounded-md bg-white",
                "text-foreground shadow-[0_1px_2px_rgba(94,95,94,0.08)]",
                "transition-colors hover:text-[#D02327]",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/35",
              )}
            >
              <Plus size="small" set="bold" primaryColor="currentColor" />
            </button>
          </div>
        </div>
      )}

      {hasPrice ? (
        <Button
          size="md"
          className={cn(
            "h-11 w-full rounded-xl text-[13px] font-bold tracking-tight",
            "shadow-[0_10px_24px_-14px_rgba(208,35,39,0.55)]",
          )}
          disabled={outOfStock}
          onClick={() => handleAdd("cart")}
        >
          <Buy set="bold" size="small" />
          {outOfStock ? "ناموجود" : "افزودن به سبد خرید"}
        </Button>
      ) : (
        <Button
          size="md"
          variant="outline"
          className={cn(
            "h-11 w-full rounded-xl text-[13px] font-bold tracking-tight",
            "border-steel/20 bg-white text-foreground",
            "hover-fine:bg-secondary hover-fine:ring-steel/25",
          )}
          disabled={outOfStock}
          onClick={() => handleAdd("quote")}
        >
          <Document set="bold" size="small" />
          {outOfStock ? "ناموجود" : "افزودن به استعلام"}
        </Button>
      )}

      {justAdded && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-success/10 px-3 py-2.5 text-[12px] text-success">
          <span className="font-medium">
            {justAdded === "cart"
              ? "به سبد خرید اضافه شد."
              : "به سبد استعلام اضافه شد."}
          </span>
          <Link
            href={justAdded === "cart" ? "/cart" : "/quote"}
            className="font-bold underline-offset-2 hover:underline"
          >
            {justAdded === "cart" ? "مشاهده سبد" : "مشاهده استعلام"}
          </Link>
        </div>
      )}

      {!hasPrice && (
        <p className="flex items-start gap-1.5 text-[11px] leading-5 text-muted-foreground">
          <Call size="small" set="light" />
          برای مشاوره تخصصی از صفحه{" "}
          <Link
            href="/contact"
            className="font-medium text-foreground underline-offset-2 hover:underline"
          >
            تماس با ما
          </Link>{" "}
          پیام بگذارید.
        </p>
      )}
    </div>
  );
}
