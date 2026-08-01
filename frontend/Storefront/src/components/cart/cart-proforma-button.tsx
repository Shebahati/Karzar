"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Document } from "react-iconly";
import { Button } from "@/components/ui/button";
import { isLoggedIn } from "@/lib/api-client";
import { downloadGuestCartProforma } from "@/services/proforma";
import { cn } from "@/lib/utils";
import type { CartLine } from "@/store/cart-store";

const LOGIN_GATE_MESSAGE = "برای دریافت پیش‌فاکتور وارد حساب شوید";
const CART_RETURN = "/login?next=/cart";

/**
 * «دریافت پیش فاکتور» — cart sample HTML print.
 * Button stays visible/enabled-looking; guests are gated to login (return to cart).
 */
export function CartProformaButton({
  lines,
  className,
  size = "lg",
  fullWidth = true,
  showHint = true,
}: {
  lines: CartLine[];
  className?: string;
  size?: "sm" | "md" | "lg";
  fullWidth?: boolean;
  showHint?: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [gateOpen, setGateOpen] = useState(false);
  const empty = lines.length === 0;

  const handleClick = async () => {
    if (empty || busy) return;
    setError(null);

    if (!isLoggedIn()) {
      setGateOpen(true);
      return;
    }

    setGateOpen(false);
    setBusy(true);
    try {
      await downloadGuestCartProforma(lines);
    } catch (err) {
      const code = err instanceof Error ? err.message : "";
      setError(
        code === "POPUP_BLOCKED"
          ? "پنجره پیش‌فاکتور مسدود شد. اجازه پاپ‌آپ را فعال کنید و دوباره بزنید."
          : "ساخت پیش‌فاکتور ناموفق بود. دوباره تلاش کنید.",
      );
    } finally {
      setBusy(false);
    }
  };

  if (empty) return null;

  return (
    <div className={cn(fullWidth && "w-full", className)}>
      <Button
        type="button"
        variant="outline"
        size={size}
        className={cn(fullWidth && "w-full", "gap-2")}
        disabled={busy}
        aria-haspopup={gateOpen ? "dialog" : undefined}
        onClick={() => void handleClick()}
      >
        <Document set="bold" size="small" />
        {busy ? "در حال ساخت…" : "دریافت پیش فاکتور"}
      </Button>
      {showHint && !gateOpen && (
        <p className="mt-2 text-center text-[11px] leading-5 text-muted-foreground">
          پیش‌فاکتور سبد — چاپ یا ذخیره PDF · نیاز به ورود
        </p>
      )}
      {gateOpen && (
        <div
          role="dialog"
          aria-modal="false"
          aria-labelledby="proforma-login-gate-title"
          className="mt-2 rounded-xl border border-border bg-card px-3 py-3 text-center shadow-soft"
        >
          <p
            id="proforma-login-gate-title"
            className="text-sm font-medium leading-6 text-foreground"
          >
            {LOGIN_GATE_MESSAGE}
          </p>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
            <Button
              type="button"
              size="sm"
              className="min-w-[7.5rem]"
              onClick={() => router.push(CART_RETURN)}
            >
              ورود به حساب
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setGateOpen(false)}
            >
              انصراف
            </Button>
          </div>
        </div>
      )}
      {error && (
        <p className="mt-1 text-center text-xs text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
