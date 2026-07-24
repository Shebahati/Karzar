"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Buy, Delete, Document, Danger } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { cn, formatToman, toPersianDigits } from "@/lib/utils";
import { isLoggedIn } from "@/lib/api-client";
import { useCartStore, type CartLine } from "@/store/cart-store";
import { MobileCartDock } from "@/components/cart/mobile-cart-dock";

type Mode = "cart" | "quote";

function stockIssue(line: CartLine): string | null {
  if (!line.product.availability || line.product.stock_status === "out_of_stock") {
    return "این کالا در حال حاضر ناموجود است.";
  }
  if (line.product.stock_status === "low_stock") {
    return "موجودی این کالا محدود است؛ قبل از پرداخت همگام‌سازی کنید.";
  }
  return null;
}

/** Shared view for both the priced cart and the price-less quote/RFQ basket. */
export function CartView({ mode }: { mode: Mode }) {
  const [mounted, setMounted] = useState(false);
  const [showRestored, setShowRestored] = useState(false);
  const [reconciling, setReconciling] = useState(false);

  const lines = useCartStore((s) => (mode === "cart" ? s.cart : s.quote));
  const setQty = useCartStore((s) =>
    mode === "cart" ? s.setCartQuantity : s.setQuoteQuantity,
  );
  const remove = useCartStore((s) =>
    mode === "cart" ? s.removeFromCart : s.removeFromQuote,
  );
  const clear = useCartStore((s) => (mode === "cart" ? s.clearCart : s.clearQuote));
  const otherCount = useCartStore((s) =>
    mode === "cart"
      ? s.quote.reduce((n, l) => n + l.quantity, 0)
      : s.cart.reduce((n, l) => n + l.quantity, 0),
  );
  const lastSyncError = useCartStore((s) => s.lastSyncError);
  const clearSyncError = useCartStore((s) => s.clearSyncError);
  const reconcileFromServer = useCartStore((s) => s.reconcileFromServer);

  useEffect(() => {
    setMounted(true);
    if (mode === "quote" && sessionStorage.getItem("karzar.inquiry.restored") === "1") {
      setShowRestored(true);
      sessionStorage.removeItem("karzar.inquiry.restored");
    }
  }, [mode]);

  useEffect(() => {
    if (!mounted || !isLoggedIn()) return;
    let cancelled = false;
    setReconciling(true);
    void reconcileFromServer().finally(() => {
      if (!cancelled) setReconciling(false);
    });
    return () => {
      cancelled = true;
    };
  }, [mounted, reconcileFromServer]);

  const title = mode === "cart" ? "سبد خرید" : "استعلام قیمت";
  const total = lines.reduce(
    (sum, l) => sum + Number(l.product.base_price ?? 0) * l.quantity,
    0,
  );

  const stockWarnings = useMemo(
    () =>
      mode === "cart"
        ? lines
            .map((line) => ({ line, issue: stockIssue(line) }))
            .filter((x): x is { line: CartLine; issue: string } => Boolean(x.issue))
        : [],
    [lines, mode],
  );

  if (!mounted) {
    return <Container className="py-16" />;
  }

  if (!lines.length) {
    return (
      <Container className="py-16">
        <div className="grid place-items-center rounded-2xl bg-card py-20 text-center shadow-soft">
          <span className="grid h-16 w-16 place-items-center rounded-2xl bg-accent text-primary">
            {mode === "cart" ? <Buy set="bold" /> : <Document set="bold" />}
          </span>
          <p className="mt-4 font-bold text-foreground">{title} شما خالی است</p>
          <Link href="/catalog" className="mt-4">
            <Button>مشاهده محصولات</Button>
          </Link>
        </div>
      </Container>
    );
  }

  return (
    <Container className="pt-8 pb-24 lg:py-12">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{title}</h1>
          {reconciling && (
            <p className="mt-1 text-xs text-muted-foreground">در حال همگام‌سازی با سرور…</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {isLoggedIn() && (
            <button
              type="button"
              disabled={reconciling}
              onClick={() => {
                setReconciling(true);
                void reconcileFromServer().finally(() => setReconciling(false));
              }}
              className="text-sm font-medium text-primary hover:underline disabled:opacity-50"
            >
              همگام‌سازی سبد
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              if (window.confirm("همه اقلام این سبد حذف شوند؟")) clear();
            }}
            className="text-sm font-medium text-muted-foreground hover:text-destructive"
          >
            خالی کردن
          </button>
        </div>
      </div>

      {lastSyncError && (
        <div
          role="alert"
          className="mb-4 flex items-start justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
        >
          <span>{lastSyncError}</span>
          <button
            type="button"
            className="shrink-0 text-xs font-medium underline"
            onClick={() => clearSyncError()}
          >
            بستن
          </button>
        </div>
      )}

      {stockWarnings.length > 0 && (
        <div
          role="status"
          className="mb-4 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-foreground"
        >
          <div className="mb-2 flex items-center gap-2 font-bold text-destructive">
            <Danger set="bold" size={18} primaryColor="currentColor" />
            اختلاف موجودی با سرور
          </div>
          <ul className="space-y-1 text-muted-foreground">
            {stockWarnings.map(({ line, issue }) => (
              <li key={line.product.id}>
                <span className="font-medium text-foreground">{line.product.name}</span>
                {" — "}
                {issue}
              </li>
            ))}
          </ul>
        </div>
      )}

      {otherCount > 0 && (
        <div className="mb-4 rounded-lg bg-secondary px-4 py-3 text-sm text-foreground">
          {mode === "cart" ? (
            <>
              {toPersianDigits(otherCount)} قلم در{" "}
              <Link href="/quote" className="font-medium text-primary">
                سبد استعلام
              </Link>{" "}
              دارید.
            </>
          ) : (
            <>
              {toPersianDigits(otherCount)} قلم در{" "}
              <Link href="/cart" className="font-medium text-primary">
                سبد خرید
              </Link>{" "}
              دارید.
            </>
          )}
        </div>
      )}

      {mode === "quote" && showRestored && (
        <div className="mb-4 rounded-2xl border border-primary/20 bg-accent/60 p-4 text-sm leading-7 text-foreground">
          <p className="font-bold text-primary">استعلام قبلی شما بازیابی شد</p>
          <p className="mt-1 text-muted-foreground">
            پس از ورود، سبد استعلام ناتمام قبلی‌تان اینجا قرار گرفت. می‌توانید آن را تکمیل و ثبت کنید.
          </p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-3 lg:col-span-2">
          {lines.map((line) => (
            <CartRow
              key={line.product.id}
              line={line}
              issue={mode === "cart" ? stockIssue(line) : null}
              onQty={setQty}
              onRemove={remove}
            />
          ))}
        </div>

        <div className="lg:col-span-1">
          <div className="sticky top-32 hidden rounded-2xl bg-card p-6 shadow-card lg:block">
            <h2 className="text-base font-bold text-foreground">خلاصه سفارش</h2>
            {mode === "cart" ? (
              <>
                <div className="mt-4 flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">مجموع</span>
                  <span className="font-bold text-foreground tnum">{formatToman(total)}</span>
                </div>
                <Link href="/checkout" className="mt-6 block">
                  <Button size="lg" className="w-full" disabled={stockWarnings.some((w) => w.line.product.stock_status === "out_of_stock")}>
                    تکمیل خرید و پرداخت
                  </Button>
                </Link>
              </>
            ) : (
              <>
                <p className="mt-4 text-sm leading-7 text-muted-foreground">
                  این اقلام برای دریافت پیش‌فاکتور و استعلام قیمت ثبت می‌شوند. کارشناسان ما در اسرع
                  وقت با شما تماس می‌گیرند.
                </p>
                <Link href="/checkout?mode=quote" className="mt-6 block">
                  <Button size="lg" className="w-full gap-2">
                    <Document set="bold" />
                    ثبت درخواست استعلام
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </div>

      <MobileCartDock mode={mode} total={total} itemCount={lines.length} />
    </Container>
  );
}

function CartRow({
  line,
  issue,
  onQty,
  onRemove,
}: {
  line: CartLine;
  issue: string | null;
  onQty: (id: number, qty: number) => void;
  onRemove: (id: number) => void;
}) {
  const { product, quantity } = line;
  const hasPrice = product.base_price != null;

  return (
    <div
      className={cn(
        "flex gap-4 rounded-2xl bg-card p-4 shadow-soft",
        issue && "ring-1 ring-destructive/25",
      )}
    >
      <div className="relative h-24 w-24 shrink-0 overflow-hidden rounded-xl bg-accent">
        {product.thumbnail ? (
          <Image
            src={product.thumbnail}
            alt={product.name}
            fill
            sizes="96px"
            className="object-contain p-1"
          />
        ) : (
          <span className="grid h-full w-full place-items-center text-lg font-medium text-accent-foreground">
            {(product.name || "ک").slice(0, 1)}
          </span>
        )}
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <Link
          href={`/product/${product.id}`}
          className="line-clamp-2 text-sm font-bold text-foreground hover:text-primary"
        >
          {product.name}
        </Link>
        {product.brand && (
          <span className="mt-1 text-xs text-muted-foreground">{product.brand.name}</span>
        )}
        {issue && <p className="mt-1 text-xs font-medium text-destructive">{issue}</p>}

        <div className="mt-auto flex items-center justify-between pt-2">
          <div className="flex items-center gap-1 rounded-xl bg-secondary p-1">
            <button
              type="button"
              aria-label="کاهش"
              onClick={() => onQty(product.id, quantity - 1)}
              className="touch-target rounded-lg bg-white text-lg text-foreground shadow-soft"
            >
              −
            </button>
            <span className="min-w-8 text-center text-sm font-bold tnum">{quantity}</span>
            <button
              type="button"
              aria-label="افزایش"
              onClick={() => onQty(product.id, quantity + 1)}
              className="touch-target rounded-lg bg-white text-lg text-foreground shadow-soft"
            >
              +
            </button>
          </div>

          <span className={cn("text-sm font-bold tnum", hasPrice ? "text-foreground" : "text-primary")}>
            {hasPrice ? formatToman(Number(product.base_price) * quantity) : "استعلام قیمت"}
          </span>
        </div>
      </div>

      <button
        type="button"
        aria-label="حذف"
        onClick={() => onRemove(product.id)}
        className="touch-target shrink-0 self-start rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-primary"
      >
        <Delete size="small" set="light" />
      </button>
    </div>
  );
}
