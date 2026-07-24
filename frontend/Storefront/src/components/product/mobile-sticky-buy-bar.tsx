"use client";

import Link from "next/link";
import { Buy, Document } from "react-iconly";
import { Button } from "@/components/ui/button";
import { formatToman } from "@/lib/utils";
import type { ProductDetail } from "@/types/product";
import { useCartStore } from "@/store/cart-store";
import { useEffect, useState } from "react";

/**
 * Compact sticky purchase bar for phones — sits above the bottom nav.
 * Full TwoLaneActions remain in the page body for qty / messaging.
 */
export function MobileStickyBuyBar({ product }: { product: ProductDetail }) {
  const addToCart = useCartStore((s) => s.addToCart);
  const addToQuote = useCartStore((s) => s.addToQuote);
  const [visible, setVisible] = useState(false);
  const [flash, setFlash] = useState<"cart" | "quote" | null>(null);

  const hasPrice = product.base_price != null;
  const outOfStock = !product.availability;

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 280);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!visible || outOfStock) return null;

  const summary = {
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

  const handle = (lane: "cart" | "quote") => {
    if (lane === "cart") addToCart(summary, 1);
    else addToQuote(summary, 1);
    setFlash(lane);
    window.setTimeout(() => setFlash(null), 2500);
  };

  return (
    <div className="mobile-dock px-4 py-3">
      <div className="mx-auto flex max-w-lg items-center gap-3">
        <div className="min-w-0 flex-1">
          {hasPrice ? (
            <p className="truncate text-sm font-bold text-foreground tnum">
              {formatToman(product.base_price)}
            </p>
          ) : (
            <p className="truncate text-sm font-bold text-primary">استعلام قیمت</p>
          )}
          {flash ? (
            <Link
              href={flash === "cart" ? "/cart" : "/quote"}
              className="text-xs font-medium text-success"
            >
              اضافه شد — مشاهده
            </Link>
          ) : (
            <p className="truncate text-[11px] text-muted-foreground">{product.name}</p>
          )}
        </div>
        {hasPrice ? (
          <Button size="lg" className="shrink-0 gap-1.5 px-4" onClick={() => handle("cart")}>
            <Buy set="bold" size="small" />
            سبد
          </Button>
        ) : (
          <Button
            size="lg"
            variant="outline"
            className="shrink-0 gap-1.5 border-foreground/20 bg-card px-4 text-foreground"
            onClick={() => handle("quote")}
          >
            <Document set="bold" size="small" />
            استعلام
          </Button>
        )}
      </div>
    </div>
  );
}
