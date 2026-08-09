"use client";

import Link from "next/link";
import { Document } from "react-iconly";
import { Button } from "@/components/ui/button";
import { CartProformaButton } from "@/components/cart/cart-proforma-button";
import { formatToman, toPersianDigits } from "@/lib/utils";
import type { CartLine } from "@/store/cart-store";

/** Sticky checkout CTA for cart/quote pages on phones. */
export function MobileCartDock({
  mode,
  total,
  totalSavings = 0,
  itemCount,
  unitCount,
  lines = [],
  checkoutDisabled = false,
}: {
  mode: "cart" | "quote";
  total: number;
  /** Sum of line discount savings; hidden when 0. */
  totalSavings?: number;
  itemCount: number;
  /** Total units across lines (for richer summary). Falls back to itemCount. */
  unitCount?: number;
  /** Cart lines for login-gated sample proforma (cart mode only). */
  lines?: CartLine[];
  /** When true, block checkout CTA (e.g. any OOS line). */
  checkoutDisabled?: boolean;
}) {
  if (itemCount === 0) return null;
  const units = unitCount ?? itemCount;

  return (
    <div className="mobile-dock overflow-x-clip px-4 py-3">
      <div className="mx-auto flex w-full max-w-lg min-w-0 flex-col gap-2">
        <div className="flex min-w-0 items-center gap-3">
          <div className="min-w-0 flex-1">
            {mode === "cart" ? (
              <>
                <p className="truncate text-xs text-muted-foreground">
                  مجموع · {toPersianDigits(units)} قلم
                </p>
                <p className="truncate text-base font-bold text-foreground tnum">
                  {formatToman(total)}
                </p>
                {totalSavings > 0 && (
                  <p className="mt-0.5 truncate text-[11px] font-medium text-[#D02327] tnum">
                    سود شما از این خرید · {formatToman(totalSavings)}
                  </p>
                )}
              </>
            ) : (
              <>
                <p className="text-xs text-muted-foreground">اقلام استعلام</p>
                <p className="text-base font-bold text-foreground tnum">
                  {toPersianDigits(itemCount)} قلم
                </p>
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
          <CartProformaButton lines={lines} size="md" />
        )}
      </div>
    </div>
  );
}
