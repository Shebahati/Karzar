"use client";

import Link from "next/link";
import { Document } from "react-iconly";
import { Button } from "@/components/ui/button";
import { CartProformaButton } from "@/components/cart/cart-proforma-button";
import { formatToman } from "@/lib/utils";
import type { CartLine } from "@/store/cart-store";

/** Sticky checkout CTA for cart/quote pages on phones. */
export function MobileCartDock({
  mode,
  total,
  itemCount,
  lines = [],
  checkoutDisabled = false,
}: {
  mode: "cart" | "quote";
  total: number;
  itemCount: number;
  /** Cart lines for login-gated sample proforma (cart mode only). */
  lines?: CartLine[];
  /** When true, block checkout CTA (e.g. any OOS line). */
  checkoutDisabled?: boolean;
}) {
  if (itemCount === 0) return null;

  return (
    <div className="mobile-dock px-4 py-3">
      <div className="mx-auto flex max-w-lg flex-col gap-2">
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1">
            {mode === "cart" ? (
              <>
                <p className="text-xs text-muted-foreground">مجموع</p>
                <p className="text-base font-bold text-foreground tnum">{formatToman(total)}</p>
              </>
            ) : (
              <>
                <p className="text-xs text-muted-foreground">اقلام استعلام</p>
                <p className="text-base font-bold text-foreground tnum">{itemCount} قلم</p>
              </>
            )}
          </div>
          {mode === "cart" ? (
            checkoutDisabled ? (
              <Button size="lg" className="shrink-0 px-5" disabled>
                تکمیل خرید
              </Button>
            ) : (
              <Link href="/checkout" className="shrink-0">
                <Button size="lg" className="px-5">
                  تکمیل خرید
                </Button>
              </Link>
            )
          ) : (
            <Link href="/checkout?mode=quote" className="shrink-0">
              <Button size="lg" className="gap-1.5 px-5">
                <Document set="bold" size="small" />
                ثبت استعلام
              </Button>
            </Link>
          )}
        </div>
        {mode === "cart" && (
          <CartProformaButton
            lines={lines}
            size="md"
            showHint={false}
          />
        )}
      </div>
    </div>
  );
}
