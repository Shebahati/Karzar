"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Buy, Call, Danger, Delete, Document, Plus, Send, ShieldDone } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { SafeImage } from "@/components/ui/safe-image";
import { cn, formatToman, toPersianDigits } from "@/lib/utils";
import { productPath } from "@/lib/product-url";
import { isLoggedIn } from "@/lib/api-client";
import { productLineSavings } from "@/types/product";
import { useCartStore, type CartLine } from "@/store/cart-store";
import { MobileCartDock } from "@/components/cart/mobile-cart-dock";
import { CartProformaButton } from "@/components/cart/cart-proforma-button";

type Mode = "cart" | "quote";

const TRUST_CUES = [
  { Icon: ShieldDone, title: "ضمانت اصالت", desc: "کالای اصلی" },
  { Icon: Send, title: "ارسال سراسر کشور", desc: "پس از تأیید سفارش" },
  { Icon: Call, title: "پشتیبانی", desc: "۹ تا ۱۸" },
] as const;

function stockIssue(line: CartLine): string | null {
  if (
    !line.product.availability ||
    line.product.stock_status === "out_of_stock" ||
    line.product.stock_status === "ناموجود"
  ) {
    return "این کالا در حال حاضر ناموجود است.";
  }
  return null;
}

function itemCountLabel(n: number) {
  return `${toPersianDigits(n)} قلم`;
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
  const unitCount = lines.reduce((n, l) => n + l.quantity, 0);
  const total = lines.reduce(
    (sum, l) => sum + Number(l.product.base_price ?? 0) * l.quantity,
    0,
  );
  const totalSavings =
    mode === "cart"
      ? lines.reduce((sum, l) => sum + productLineSavings(l.product, l.quantity), 0)
      : 0;

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
    return (
      <div className="overflow-x-clip bg-hero-glow">
        <Container className="py-16" />
      </div>
    );
  }

  if (!lines.length) {
    return (
      <div className="overflow-x-clip bg-hero-glow">
        <Container className="py-12 sm:py-16">
          <div
            className={cn(
              "relative mx-auto max-w-lg overflow-hidden rounded-3xl bg-card px-6 py-14 text-center sm:px-10 sm:py-16",
              "shadow-[0_1px_0_rgba(94,95,94,0.05),0_20px_48px_-28px_rgba(94,95,94,0.35)]",
              "ring-1 ring-inset ring-[#5E5F5E]/[0.08]",
            )}
          >
            <span
              aria-hidden
              className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-l from-transparent via-primary/35 to-transparent"
            />
            <span className="mx-auto grid h-16 w-16 place-items-center rounded-2xl bg-primary/[0.08] text-primary ring-1 ring-inset ring-primary/15">
              {mode === "cart" ? <Buy set="bold" /> : <Document set="bold" />}
            </span>
            <h1 className="mt-5 text-xl font-bold text-foreground sm:text-2xl">{title} شما خالی است</h1>
            <p className="mx-auto mt-2 max-w-sm text-sm leading-7 text-[#5E5F5E]">
              {mode === "cart"
                ? "محصولات ابزار صنعتی را به سبد اضافه کنید و خرید را با خیال راحت تکمیل کنید."
                : "اقلام موردنیاز را اضافه کنید تا کارشناسان کارزار پیش‌فاکتور رسمی برایتان صادر کنند."}
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-2.5">
              <Link href="/catalog">
                <Button size="lg">مشاهده محصولات</Button>
              </Link>
              <Link href="/">
                <Button size="lg" variant="soft">
                  بازگشت به خانه
                </Button>
              </Link>
            </div>
            <ul className="mt-10 grid grid-cols-3 gap-2 border-t border-[#5E5F5E]/10 pt-6 text-center">
              {TRUST_CUES.map(({ Icon, title: t }) => (
                <li key={t} className="min-w-0 space-y-1.5 px-1">
                  <span className="mx-auto grid h-9 w-9 place-items-center rounded-xl bg-[#F7F7F7] text-primary">
                    <Icon set="bold" size="small" primaryColor="#D02327" />
                  </span>
                  <p className="truncate text-[11px] font-bold text-foreground sm:text-xs">{t}</p>
                </li>
              ))}
            </ul>
          </div>
        </Container>
      </div>
    );
  }

  return (
    <div className="overflow-x-clip bg-hero-glow">
      <Container className="pt-7 pb-36 sm:pt-9 lg:py-12 lg:pb-12">
        {/* Header */}
        <header className="mb-6 flex min-w-0 flex-wrap items-end justify-between gap-3 sm:mb-8">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-[1.75rem]">
                {title}
              </h1>
              <span className="inline-flex items-center rounded-full bg-primary/[0.08] px-2.5 py-1 text-xs font-bold text-primary ring-1 ring-inset ring-primary/15 tnum">
                {itemCountLabel(unitCount)}
              </span>
            </div>
            <p className="mt-1.5 text-sm text-[#5E5F5E]">
              {mode === "cart"
                ? "مرور اقلام، بررسی قیمت و تکمیل خرید"
                : "مرور اقلام و ثبت درخواست استعلام قیمت"}
            </p>
            {reconciling && (
              <p className="mt-1 text-xs text-muted-foreground">در حال همگام‌سازی با سرور…</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => {
              if (window.confirm("همه اقلام این سبد حذف شوند؟")) clear();
            }}
            className="inline-flex shrink-0 items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-destructive"
          >
            <Delete size="small" set="light" />
            خالی کردن
          </button>
        </header>

        {lastSyncError && (
          <div
            role="alert"
            className="mb-4 flex min-w-0 items-start justify-between gap-3 overflow-hidden rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          >
            <span className="min-w-0 break-words">{lastSyncError}</span>
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
            className="mb-4 overflow-hidden rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-foreground"
          >
            <div className="mb-2 flex items-center gap-2 font-bold text-destructive">
              <Danger set="bold" size={18} primaryColor="currentColor" />
              اختلاف موجودی با سرور
            </div>
            <ul className="space-y-1 text-muted-foreground">
              {stockWarnings.map(({ line, issue }) => (
                <li key={line.product.id} className="min-w-0 break-words">
                  <span className="font-medium text-foreground">{line.product.name}</span>
                  {" — "}
                  {issue}
                </li>
              ))}
            </ul>
          </div>
        )}

        {otherCount > 0 && (
          <div className="mb-4 overflow-hidden rounded-xl bg-secondary/80 px-4 py-3 text-sm text-foreground ring-1 ring-inset ring-[#5E5F5E]/[0.06]">
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
          <div className="mb-4 overflow-hidden rounded-2xl border border-primary/20 bg-accent/60 p-4 text-sm leading-7 text-foreground">
            <p className="font-bold text-primary">استعلام قبلی شما بازیابی شد</p>
            <p className="mt-1 text-muted-foreground">
              پس از ورود، سبد استعلام ناتمام قبلی‌تان اینجا قرار گرفت. می‌توانید آن را تکمیل و ثبت کنید.
            </p>
          </div>
        )}

        <div className="grid min-w-0 gap-6 lg:grid-cols-3 lg:gap-8">
          {/* Line items */}
          <div className="min-w-0 space-y-3 sm:space-y-3.5 lg:col-span-2">
            {lines.map((line) => (
              <CartRow
                key={line.product.id}
                line={line}
                issue={mode === "cart" ? stockIssue(line) : null}
                onQty={setQty}
                onRemove={remove}
              />
            ))}

            {/* Soft trust strip under lines — fills bare space without noise */}
            <ul
              aria-label="مزایای خرید از کارزار"
              className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3 sm:gap-2.5"
            >
              {TRUST_CUES.map(({ Icon, title: t, desc }) => (
                <li
                  key={t}
                  className={cn(
                    "flex min-w-0 items-center gap-3 overflow-hidden rounded-2xl bg-card/80 px-3.5 py-3",
                    "ring-1 ring-inset ring-[#5E5F5E]/[0.07]",
                  )}
                >
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-primary/[0.07] text-primary ring-1 ring-inset ring-primary/10">
                    <Icon set="bold" size="small" primaryColor="#D02327" />
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-[13px] font-bold text-foreground">{t}</span>
                    <span className="block truncate text-[11px] text-[#5E5F5E]">{desc}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>

          {/* Desktop summary */}
          <aside className="min-w-0 lg:col-span-1">
            <div
              className={cn(
                "relative sticky top-28 hidden overflow-hidden rounded-3xl bg-card lg:block",
                "p-6 shadow-[0_1px_0_rgba(94,95,94,0.05),0_24px_48px_-28px_rgba(94,95,94,0.32)]",
                "ring-1 ring-inset ring-[#5E5F5E]/[0.08]",
              )}
            >
              <span
                aria-hidden
                className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-l from-transparent via-primary/30 to-transparent"
              />
              <h2 className="text-base font-bold text-foreground">خلاصه سفارش</h2>
              <p className="mt-1 text-xs text-[#5E5F5E]">
                {toPersianDigits(lines.length)} کالا · {itemCountLabel(unitCount)}
              </p>

              {mode === "cart" ? (
                <>
                  <dl className="mt-5 space-y-3 text-sm">
                    <div className="flex items-center justify-between gap-3">
                      <dt className="text-[#5E5F5E]">جمع جزء</dt>
                      <dd className="font-medium text-foreground tnum">{formatToman(total)}</dd>
                    </div>
                    {totalSavings > 0 && (
                      <div className="flex items-center justify-between gap-3">
                        <dt className="text-[#5E5F5E]">سود شما از این خرید</dt>
                        <dd className="font-bold text-[#D02327] tnum">
                          {formatToman(totalSavings)}
                        </dd>
                      </div>
                    )}
                    <div className="flex items-start justify-between gap-3">
                      <dt className="text-[#5E5F5E]">هزینه ارسال</dt>
                      <dd className="max-w-[11rem] text-end text-xs leading-5 text-[#5E5F5E]">
                        در مرحله بعد محاسبه می‌شود
                      </dd>
                    </div>
                    <div className="flex items-center justify-between gap-3 border-t border-[#5E5F5E]/10 pt-3">
                      <dt className="font-bold text-foreground">مبلغ قابل پرداخت</dt>
                      <dd className="text-base font-bold text-foreground tnum">{formatToman(total)}</dd>
                    </div>
                  </dl>

                  {stockWarnings.length > 0 ? (
                    <Button size="lg" className="mt-6 w-full" disabled>
                      تکمیل خرید و پرداخت
                    </Button>
                  ) : (
                    <Link href="/checkout" className="mt-6 block">
                      <Button size="lg" className="w-full">
                        تکمیل خرید و پرداخت
                      </Button>
                    </Link>
                  )}
                  <CartProformaButton lines={lines} className="mt-3" />
                  <p className="mt-4 text-center text-[11px] leading-5 text-[#5E5F5E]">
                    پرداخت امن از درگاه رسمی · امکان دریافت پیش‌فاکتور
                  </p>
                </>
              ) : (
                <>
                  <p className="mt-4 text-sm leading-7 text-[#5E5F5E]">
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
          </aside>
        </div>

        <MobileCartDock
          mode={mode}
          total={total}
          totalSavings={totalSavings}
          itemCount={lines.length}
          unitCount={unitCount}
          lines={mode === "cart" ? lines : undefined}
          checkoutDisabled={mode === "cart" && stockWarnings.length > 0}
        />
      </Container>
    </div>
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
  const unitPrice = hasPrice ? Number(product.base_price) : null;
  const lineTotal = unitPrice != null ? unitPrice * quantity : null;
  const lineSavings = productLineSavings(product, quantity);
  const metaBits = [
    product.brand?.name,
    product.sku ? `کد ${toPersianDigits(product.sku)}` : null,
  ].filter(Boolean);

  return (
    <article
      className={cn(
        "relative min-w-0 overflow-hidden rounded-2xl bg-card sm:rounded-[1.25rem]",
        "p-3.5 sm:p-4",
        "shadow-[0_1px_0_rgba(94,95,94,0.04),0_12px_28px_-18px_rgba(94,95,94,0.28)]",
        "ring-1 ring-inset ring-[#5E5F5E]/[0.08]",
        issue && "ring-destructive/25",
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-y-3 start-0 w-[3px] rounded-e-full bg-primary/70"
      />

      {/* Top: thumb + copy + remove */}
      <div className="flex min-w-0 gap-3 sm:gap-4">
        <Link
          href={productPath(product)}
          className="relative h-[4.5rem] w-[4.5rem] shrink-0 overflow-hidden rounded-xl bg-[#F4F4F4] ring-1 ring-inset ring-[#5E5F5E]/[0.06] sm:h-24 sm:w-24 sm:rounded-[0.9rem]"
        >
          <SafeImage
            src={product.thumbnail ?? ""}
            alt={product.name}
            fill
            sizes="(max-width: 640px) 72px, 96px"
            className="object-contain p-1.5"
            fallback={
              <span className="grid h-full w-full place-items-center text-lg font-medium text-[#5E5F5E]">
                {(product.name || "ک").slice(0, 1)}
              </span>
            }
          />
        </Link>

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex min-w-0 items-start gap-2">
            <div className="min-w-0 flex-1">
              <Link
                href={productPath(product)}
                className="line-clamp-2 break-words text-[13px] font-bold leading-snug text-foreground hover:text-primary sm:text-sm"
              >
                {product.name}
              </Link>
              {metaBits.length > 0 && (
                <p className="mt-1 truncate text-[11px] text-[#5E5F5E] sm:text-xs">
                  {metaBits.join(" · ")}
                </p>
              )}
              {hasPrice && unitPrice != null && (
                <p className="mt-1.5 hidden text-xs text-[#5E5F5E] tnum sm:block">
                  واحد: {formatToman(unitPrice)}
                </p>
              )}
              {issue && (
                <p className="mt-1.5 text-xs font-medium leading-5 text-destructive break-words">
                  {issue}
                </p>
              )}
            </div>

            <button
              type="button"
              aria-label="حذف از سبد"
              onClick={() => onRemove(product.id)}
              className="touch-target shrink-0 rounded-xl text-[#5E5F5E] transition-colors hover:bg-[#F7F7F7] hover:text-primary"
            >
              <Delete size="small" set="light" />
            </button>
          </div>

          {/* Desktop qty + total inline */}
          <div className="mt-auto hidden items-center justify-between gap-3 pt-3 sm:flex">
            <QtyStepper
              quantity={quantity}
              onDec={() => onQty(product.id, quantity - 1)}
              onInc={() => onQty(product.id, quantity + 1)}
            />
            <div className="min-w-0 shrink-0 text-end">
              <span
                className={cn(
                  "block text-sm font-bold tnum",
                  hasPrice ? "text-foreground" : "text-primary",
                )}
              >
                {lineTotal != null ? formatToman(lineTotal) : "استعلام قیمت"}
              </span>
              {lineSavings > 0 && (
                <span className="mt-0.5 block text-xs font-medium text-[#D02327] tnum">
                  سود شما: {formatToman(lineSavings)}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Mobile footer: qty + line total — full width, no squeeze */}
      <div className="mt-3 flex min-w-0 items-center justify-between gap-3 border-t border-[#5E5F5E]/[0.08] pt-3 sm:hidden">
        <QtyStepper
          quantity={quantity}
          onDec={() => onQty(product.id, quantity - 1)}
          onInc={() => onQty(product.id, quantity + 1)}
        />
        <div className="min-w-0 text-end">
          {hasPrice && unitPrice != null && (
            <p className="truncate text-[10px] text-[#5E5F5E] tnum">
              واحد {formatToman(unitPrice)}
            </p>
          )}
          <p
            className={cn(
              "truncate text-sm font-bold tnum",
              hasPrice ? "text-foreground" : "text-primary",
            )}
          >
            {lineTotal != null ? formatToman(lineTotal) : "استعلام قیمت"}
          </p>
          {lineSavings > 0 && (
            <p className="mt-0.5 truncate text-[11px] font-medium text-[#D02327] tnum">
              سود شما: {formatToman(lineSavings)}
            </p>
          )}
        </div>
      </div>
    </article>
  );
}

function QtyStepper({
  quantity,
  onDec,
  onInc,
}: {
  quantity: number;
  onDec: () => void;
  onInc: () => void;
}) {
  return (
    <div className="flex shrink-0 items-center gap-0.5 rounded-xl bg-[#F4F4F4] p-1 ring-1 ring-inset ring-[#5E5F5E]/[0.06]">
      <button
        type="button"
        aria-label="کاهش تعداد"
        onClick={onDec}
        className="grid min-h-11 min-w-11 place-items-center rounded-lg bg-white text-base font-medium leading-none text-foreground shadow-sm"
      >
        −
      </button>
      <span className="min-w-9 text-center text-sm font-bold tnum">{toPersianDigits(quantity)}</span>
      <button
        type="button"
        aria-label="افزایش تعداد"
        onClick={onInc}
        className="grid min-h-11 min-w-11 place-items-center rounded-lg bg-white text-foreground shadow-sm"
      >
        <Plus size="small" set="bold" primaryColor="#5E5F5E" />
      </button>
    </div>
  );
}
