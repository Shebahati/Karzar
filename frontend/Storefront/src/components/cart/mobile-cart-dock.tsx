"use client";

import Link from "next/link";
import { Document } from "react-iconly";
import { Button } from "@/components/ui/button";
import { formatToman } from "@/lib/utils";

/** Sticky checkout CTA for cart/quote pages on phones. */
export function MobileCartDock({
  mode,
  total,
  itemCount,
}: {
  mode: "cart" | "quote";
  total: number;
  itemCount: number;
}) {
  if (itemCount === 0) return null;

  return (
    <div className="mobile-dock px-4 py-3">
      <div className="mx-auto flex max-w-lg items-center gap-3">
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
          <Link href="/checkout" className="shrink-0">
            <Button size="lg" className="px-5">
              تکمیل خرید
            </Button>
          </Link>
        ) : (
          <Link href="/checkout?mode=quote" className="shrink-0">
            <Button size="lg" className="gap-1.5 px-5">
              <Document set="bold" size="small" />
              ثبت استعلام
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
}
