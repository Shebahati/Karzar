"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { CloseSquare, TimeCircle } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";

const VERIFYING_COPY =
  "نتیجهٔ پرداخت از بانک دریافت شده و در حال بررسی نهایی است. لطفاً پرداخت را تکرار نکنید. نتیجه از طریق سفارش‌های شما قابل پیگیری است.";

export function PaymentFailedView() {
  const sp = useSearchParams();
  const reason = sp.get("reason");
  const isVerifying = reason === "verifying";
  const isReconciliation = reason === "reconciliation";
  const message =
    sp.get("message") ??
    (isVerifying
      ? VERIFYING_COPY
      : isReconciliation
        ? "پرداخت نیاز به بررسی دستی دارد. با پشتیبانی تماس بگیرید و پرداخت را تکرار نکنید."
        : "پرداخت انجام نشد یا توسط شما لغو گردید.");

  const title = isVerifying
    ? "پرداخت در حال بررسی است"
    : isReconciliation
      ? "نیازمند بررسی پرداخت"
      : "پرداخت ناموفق";

  return (
    <Container className="grid min-h-[70vh] place-items-center py-12">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-lg rounded-3xl bg-card p-8 text-center shadow-elevated sm:p-12"
      >
        <span
          className={
            isVerifying
              ? "mx-auto grid h-20 w-20 place-items-center rounded-full bg-amber-500/10 text-amber-700"
              : "mx-auto grid h-20 w-20 place-items-center rounded-full bg-destructive/10 text-destructive"
          }
        >
          {isVerifying ? (
            <TimeCircle set="bold" size="xlarge" />
          ) : (
            <CloseSquare set="bold" size="xlarge" />
          )}
        </span>
        <h1 className="mt-6 text-2xl font-bold text-foreground">{title}</h1>
        <p className="mt-2 text-sm leading-7 text-muted-foreground">{message}</p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link href="/account/orders" className="flex-1">
            <Button size="lg" className="w-full">
              پیگیری از سفارش‌های من
            </Button>
          </Link>
          {!isVerifying && (
            <Link href="/checkout" className="flex-1">
              <Button variant="soft" size="lg" className="w-full">
                بازگشت به تسویه‌حساب
              </Button>
            </Link>
          )}
        </div>
        <Link
          href="/catalog"
          className="mt-3 inline-block text-sm text-muted-foreground hover:text-primary"
        >
          بازگشت به فروشگاه
        </Link>
      </motion.div>
    </Container>
  );
}
