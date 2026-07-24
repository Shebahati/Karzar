"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Buy, TickSquare } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { AuthStep, type ResolvedCustomer } from "@/components/checkout/auth-step";
import { DetailsStep, type DetailsResult } from "@/components/checkout/details-step";
import { OrderSummary } from "@/components/checkout/order-summary";
import { useInitPayment, useSubmitCheckout } from "@/features/checkout/queries";
import { useMe } from "@/features/auth/queries";
import { useCartStore } from "@/store/cart-store";
import { isLoggedIn } from "@/lib/api-client";
import { ApiError } from "@/lib/api-client";
import { ERROR_CODES } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { savePendingInquiry } from "@/lib/inquiry-pending";
import { savePendingPayment } from "@/lib/pending-payment";
import type { CheckoutPayload } from "@/types/checkout";

type Step = "auth" | "details";

export function CheckoutView() {
  const router = useRouter();
  const sp = useSearchParams();
  const isInquiry = sp.get("mode") === "quote";

  const cart = useCartStore((s) => s.cart);
  const quote = useCartStore((s) => s.quote);
  const clearCart = useCartStore((s) => s.clearCart);
  const clearQuote = useCartStore((s) => s.clearQuote);
  const reconcileFromServer = useCartStore((s) => s.reconcileFromServer);

  const lines = isInquiry ? quote : cart;

  const [mounted, setMounted] = useState(false);
  const [step, setStep] = useState<Step>("auth");
  const [customer, setCustomer] = useState<ResolvedCustomer | null>(null);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);
  const [pendingPayOrder, setPendingPayOrder] = useState<{
    order_id: number;
    tracking_code: string;
  } | null>(null);

  const submit = useSubmitCheckout();
  const initPayment = useInitPayment();
  const { data: me } = useMe(mounted && !isInquiry);

  useEffect(() => {
    setMounted(true);
    if (isLoggedIn()) {
      setStep("details");
    } else if (!isInquiry) {
      setStep("auth");
    }
  }, [isInquiry]);

  useEffect(() => {
    if (!me || customer) return;
    setCustomer({
      full_name: me.full_name ?? "",
      phone: me.phone,
      is_guest: false,
    });
  }, [me, customer]);

  const userLoggedIn = isLoggedIn();

  const canPay = isInquiry || userLoggedIn;

  const handleDetails = async (result: DetailsResult) => {
    if (!isInquiry && !isLoggedIn()) {
      setCheckoutError("برای پرداخت آنلاین باید وارد حساب کاربری شوید.");
      setStep("auth");
      return;
    }

    setCheckoutError(null);

    // Prefer server cart as source of truth before purchase checkout.
    if (!isInquiry && isLoggedIn()) {
      const sync = await reconcileFromServer();
      if (!sync.ok) {
        setCheckoutError(
          sync.error ??
            "همگام‌سازی سبد با سرور ناموفق بود. دوباره تلاش کنید یا اقلام را بررسی کنید.",
        );
        return;
      }
      const blocked = useCartStore
        .getState()
        .cart.filter(
          (l) => !l.product.availability || l.product.stock_status === "out_of_stock",
        );
      if (blocked.length > 0) {
        setCheckoutError(
          `برخی اقلام ناموجودند: ${blocked.map((l) => l.product.name).join("، ")}. سبد را اصلاح کنید.`,
        );
        return;
      }
    }

    const currentLines = isInquiry
      ? useCartStore.getState().quote
      : useCartStore.getState().cart;

    const payload: CheckoutPayload = {
      mode: isInquiry ? "inquiry" : "purchase",
      customer: {
        full_name: result.full_name,
        phone: result.phone,
        is_guest: customer?.is_guest ?? false,
      },
      items: currentLines.map((l) => ({ product_id: l.product.id, quantity: l.quantity })),
      note: result.note ?? null,
      shipping: result.shipping,
      company_name: result.company_name ?? null,
    };

    submit.mutate(payload, {
      onSuccess: async (res) => {
        if (isInquiry) {
          savePendingInquiry(result.phone, {
            full_name: result.full_name,
            tracking_code: res.tracking_code,
            created_at: res.created_at,
            lines: currentLines.map((l) => ({ product_id: l.product.id, quantity: l.quantity })),
          });
          clearQuote();
          router.push(`/checkout/success?ref=${res.tracking_code}&mode=inquiry`);
          return;
        }

        try {
          setPaying(true);
          savePendingPayment(res.order_id, res.tracking_code);

          const payment = await initPayment.mutateAsync({ order_id: res.order_id });
          const { redirectToPaymentUrl } = await import("@/lib/payment-url");
          redirectToPaymentUrl(payment.payment_url);
        } catch (err) {
          setPaying(false);
          if (err instanceof ApiError && err.errorCode === ERROR_CODES.GUEST_ORDER_NOT_PAYABLE) {
            setCheckoutError("پرداخت آنلاین فقط برای کاربران واردشده امکان‌پذیر است. لطفاً وارد شوید.");
            setStep("auth");
            return;
          }
          setPendingPayOrder({ order_id: res.order_id, tracking_code: res.tracking_code });
          setCheckoutError(
            `سفارش با کد ${res.tracking_code} ثبت شد اما اتصال به درگاه ناموفق بود. می‌توانید پرداخت را دوباره امتحان کنید.`,
          );
        }
      },
      onError: (err) => {
        if (err instanceof ApiError && err.errorCode === ERROR_CODES.GUEST_ORDER_NOT_PAYABLE) {
          setCheckoutError("پرداخت آنلاین فقط برای کاربران واردشده امکان‌پذیر است. لطفاً وارد شوید.");
          setStep("auth");
          return;
        }
        const message =
          err instanceof ApiError && err.message
            ? err.message
            : "ثبت با خطا مواجه شد. لطفاً دوباره تلاش کنید.";
        setCheckoutError(message);
      },
    });
  };

  const steps = useMemo(
    () => [
      { key: "auth", label: "احراز هویت", shortLabel: "ورود" },
      {
        key: "details",
        label: isInquiry ? "اطلاعات استعلام" : "اطلاعات ارسال و پرداخت",
        shortLabel: isInquiry ? "استعلام" : "ارسال",
      },
    ],
    [isInquiry],
  );

  const retryPayment = async () => {
    if (!pendingPayOrder) return;
    try {
      setPaying(true);
      setCheckoutError(null);
      savePendingPayment(pendingPayOrder.order_id, pendingPayOrder.tracking_code);
      const payment = await initPayment.mutateAsync({ order_id: pendingPayOrder.order_id });
      const { redirectToPaymentUrl } = await import("@/lib/payment-url");
      redirectToPaymentUrl(payment.payment_url);
    } catch {
      setPaying(false);
      setCheckoutError("اتصال به درگاه دوباره ناموفق بود. بعداً از سفارش‌های من پرداخت را پیگیری کنید.");
    }
  };

  if (!mounted) return <Container className="py-16" />;

  if (!lines.length) {
    return (
      <Container className="py-20">
        <div className="grid place-items-center rounded-2xl bg-card py-16 text-center shadow-soft">
          <span className="grid h-16 w-16 place-items-center rounded-2xl bg-accent text-primary">
            <Buy set="bold" />
          </span>
          <p className="mt-4 font-bold text-foreground">
            {isInquiry ? "سبد استعلام خالی است" : "سبد خرید خالی است"}
          </p>
          <Link href="/catalog" className="mt-4">
            <Button>مشاهده محصولات</Button>
          </Link>
        </div>
      </Container>
    );
  }

  const activeIndex = step === "auth" ? 0 : 1;
  const submitting = submit.isPending || initPayment.isPending || paying;

  return (
    <Container className="pt-8 pb-24 lg:py-12">
      <h1 className="text-2xl font-bold text-foreground">
        {isInquiry ? "تکمیل استعلام قیمت" : "تکمیل خرید"}
      </h1>

      <ol className="mt-6 flex items-center gap-2">
        {steps.map((s, i) => (
          <li key={s.key} className="flex flex-1 items-center gap-2">
            <span
              className={cn(
                "grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm font-bold transition-colors",
                i < activeIndex
                  ? "bg-success text-success-foreground"
                  : i === activeIndex
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-muted-foreground",
              )}
            >
              {i < activeIndex ? <TickSquare size="small" set="bold" /> : i + 1}
            </span>
            <span
              className={cn(
                "text-xs font-bold sm:text-sm",
                i <= activeIndex ? "text-foreground" : "text-muted-foreground",
              )}
            >
              <span className="sm:hidden">{s.shortLabel}</span>
              <span className="hidden sm:inline">{s.label}</span>
            </span>
            {i < steps.length - 1 && (
              <span className="mx-1 h-0.5 flex-1 rounded-full bg-border" />
            )}
          </li>
        ))}
      </ol>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          {step === "auth" ? (
            <AuthStep
              isInquiry={isInquiry}
              onResolved={(c) => {
                setCustomer(c);
                setStep("details");
                setCheckoutError(null);
              }}
            />
          ) : (
            <DetailsStep
              isInquiry={isInquiry}
              customer={customer}
              submitting={submitting}
              canPay={canPay}
              onSubmit={handleDetails}
              onBack={() => setStep("auth")}
            />
          )}
          {checkoutError && (
            <div className="mt-3 space-y-3 rounded-lg bg-destructive/10 p-4" role="alert">
              <p className="text-sm text-destructive">{checkoutError}</p>
              {pendingPayOrder && (
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" disabled={paying} onClick={() => void retryPayment()}>
                    {paying ? "در حال اتصال…" : "پرداخت مجدد / انتقال به درگاه"}
                  </Button>
                  <Link href={`/account/orders/${encodeURIComponent(pendingPayOrder.tracking_code)}`}>
                    <Button size="sm" variant="outline">
                      مشاهده سفارش
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="lg:col-span-1">
          <div className="sticky top-32">
            <OrderSummary lines={lines} isInquiry={isInquiry} />
          </div>
        </div>
      </div>
    </Container>
  );
}
