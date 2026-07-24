"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Buy, Document } from "react-iconly";
import { Badge } from "@/components/ui/badge";
import { ProductPlaceholder } from "@/components/ui/product-placeholder";
import { cn, formatToman } from "@/lib/utils";
import { useCartStore } from "@/store/cart-store";
import type { ProductSummary } from "@/types/product";

export function ProductCard({
  product,
  className,
}: {
  product: ProductSummary;
  className?: string;
}) {
  const addToCart = useCartStore((s) => s.addToCart);
  const addToQuote = useCartStore((s) => s.addToQuote);
  const hasPrice = product.base_price != null;
  const outOfStock = !product.availability;
  const [addedFlash, setAddedFlash] = useState(false);

  const quickAdd = (e: React.MouseEvent) => {
    e.preventDefault();
    if (outOfStock) return;
    if (hasPrice) addToCart(product);
    else addToQuote(product);
    setAddedFlash(true);
    window.setTimeout(() => setAddedFlash(false), 1800);
  };

  return (
    <Link
      href={`/product/${product.id}`}
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-xl bg-card shadow-soft transition-shadow duration-200 hover:shadow-elevated",
        className,
      )}
    >
      <div className="relative aspect-square overflow-hidden bg-muted/40">
        {product.thumbnail ? (
          <Image
            src={product.thumbnail}
            alt={product.name}
            fill
            sizes="(max-width: 768px) 50vw, 25vw"
            className="object-contain p-3 transition-transform duration-300 group-hover:scale-[1.03]"
          />
        ) : (
          <ProductPlaceholder name={product.name} sku={product.sku} />
        )}

        <div className="absolute inset-x-3 top-3 flex items-start justify-between">
          <div className="flex flex-col gap-1.5">
            {product.discount_percent ? (
              <Badge variant="primary">٪{product.discount_percent} تخفیف</Badge>
            ) : null}
          </div>
        </div>

        {outOfStock && (
          <div className="absolute inset-0 grid place-items-center bg-foreground/40">
            <span className="rounded-md bg-foreground px-4 py-1.5 text-xs font-medium text-white">
              ناموجود
            </span>
          </div>
        )}

        {addedFlash && (
          <div className="absolute inset-x-3 bottom-3 rounded-md bg-success px-3 py-1.5 text-center text-[11px] font-medium text-success-foreground">
            {hasPrice ? "به سبد اضافه شد" : "به استعلام اضافه شد"}
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col p-4">
        {product.brand && (
          <span className="text-xs font-medium text-muted-foreground">{product.brand.name}</span>
        )}
        <h3 className="mt-1 line-clamp-2 min-h-[2.75rem] text-sm font-medium leading-6 text-foreground transition-colors group-hover:text-primary">
          {product.name}
        </h3>

        <div className="mt-auto flex items-end justify-between pt-3">
          <div>
            {hasPrice ? (
              <>
                {product.original_price && (
                  <span className="block text-xs text-muted-foreground line-through tnum">
                    {formatToman(product.original_price)}
                  </span>
                )}
                <span className="text-sm font-medium text-ink tnum">
                  {formatToman(product.base_price)}
                </span>
              </>
            ) : (
              <span className="text-sm font-medium text-accent-foreground">استعلام قیمت</span>
            )}
          </div>

          <button
            type="button"
            onClick={quickAdd}
            disabled={outOfStock}
            aria-label={hasPrice ? "افزودن به سبد خرید" : "افزودن به استعلام"}
            className={cn(
              "grid h-11 w-11 place-items-center rounded-lg text-primary-foreground shadow-soft transition-transform active:scale-95 disabled:opacity-40",
              hasPrice
                ? "bg-primary"
                : "bg-card text-foreground ring-1 ring-inset ring-border hover:bg-accent",
            )}
          >
            {hasPrice ? (
              <Buy size="small" set="bold" />
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
    <div className="overflow-hidden rounded-xl bg-card shadow-soft">
      <div className="aspect-square shimmer bg-muted" />
      <div className="space-y-2 p-4">
        <div className="h-3 w-16 rounded bg-muted" />
        <div className="h-4 w-full rounded bg-muted" />
        <div className="h-4 w-2/3 rounded bg-muted" />
      </div>
    </div>
  );
}
