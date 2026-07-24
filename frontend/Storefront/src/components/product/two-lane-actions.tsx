"use client";

import { useState } from "react";
import Link from "next/link";
import { Buy, Call, Document, Plus } from "react-iconly";
import { Button } from "@/components/ui/button";
import { useCartStore } from "@/store/cart-store";
import type { ProductDetail, ProductSummary } from "@/types/product";

/**
 * Two-lane purchase:
 * - priced → add to cart
 * - price-less → add to inquiry/quote (no fake SMS success)
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
    <div className="space-y-3">
      {!outOfStock && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">تعداد</span>
          <div className="flex items-center gap-1 rounded-lg bg-secondary p-1">
            <button
              type="button"
              aria-label="کاهش"
              onClick={() => setQty((q) => Math.max(1, q - 1))}
              className="touch-target rounded-md bg-white text-lg text-foreground shadow-soft"
            >
              −
            </button>
            <span className="min-w-10 text-center text-sm font-medium tnum">{qty}</span>
            <button
              type="button"
              aria-label="افزایش"
              onClick={() => setQty((q) => q + 1)}
              className="touch-target rounded-md bg-white text-foreground shadow-soft"
            >
              <Plus size="small" set="bold" />
            </button>
          </div>
        </div>
      )}

      {hasPrice ? (
        <Button
          size="lg"
          className="w-full"
          disabled={outOfStock}
          onClick={() => handleAdd("cart")}
        >
          <Buy set="bold" />
          {outOfStock ? "ناموجود" : "افزودن به سبد خرید"}
        </Button>
      ) : (
        <Button
          size="lg"
          variant="outline"
          className="w-full border-foreground/25 bg-card text-foreground hover:bg-secondary"
          disabled={outOfStock}
          onClick={() => handleAdd("quote")}
        >
          <Document set="bold" />
          {outOfStock ? "ناموجود" : "افزودن به استعلام"}
        </Button>
      )}

      {justAdded && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-success/10 px-4 py-3 text-sm text-success">
          <span className="font-medium">
            {justAdded === "cart" ? "به سبد خرید اضافه شد." : "به سبد استعلام اضافه شد."}
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
        <p className="flex items-start gap-2 text-xs leading-6 text-muted-foreground">
          <Call size="small" set="light" />
          برای مشاوره تخصصی از صفحه{" "}
          <Link href="/contact" className="font-medium text-foreground underline-offset-2 hover:underline">
            تماس با ما
          </Link>{" "}
          پیام بگذارید.
        </p>
      )}
    </div>
  );
}
