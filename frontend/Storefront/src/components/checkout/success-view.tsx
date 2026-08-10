"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Call, Document, Home, Paper, TickSquare } from "react-iconly";
import { Container } from "@/components/ui/container";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { OrderTimeline } from "@/components/orders/order-timeline";
import { useOrderTracking } from "@/features/orders/queries";
import { toPersianDigits } from "@/lib/utils";

export function SuccessView() {
  const sp = useSearchParams();
  const ref = sp.get("ref") ?? "KZ-000000";
  const isInquiry = sp.get("mode") === "inquiry";
  const paid = sp.get("paid") === "1";
  const [copied, setCopied] = useState(false);

  const { data: tracking, isPending, isError } = useOrderTracking(ref, Boolean(ref));

  return (
    <Container className="grid min-h-[70vh] w-full min-w-0 place-items-center overflow-x-clip py-8 sm:py-12">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="w-full min-w-0 max-w-lg overflow-hidden rounded-3xl bg-card p-5 text-center shadow-elevated sm:p-8 md:p-12"
      >
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 14, delay: 0.15 }}
          className="mx-auto grid h-20 w-20 place-items-center rounded-full bg-success text-success-foreground shadow-elevated"
        >
          <TickSquare set="bold" size="xlarge" />
        </motion.span>

        <h1 className="mt-6 break-words text-xl font-bold text-foreground sm:text-2xl">
          {isInquiry ? "استعلام شما ثبت شد" : paid ? "پرداخت با موفقیت انجام شد" : "سفارش شما ثبت شد"}
        </h1>
        <p className="mt-2 break-words text-sm leading-7 text-muted-foreground">
          {isInquiry
            ? "کارشناسان ما درخواست شما را بررسی کرده و در اسرع وقت پیش‌فاکتور را ارسال می‌کنند."
            : paid
              ? "از خرید شما سپاسگزاریم. سفارش در حال پردازش است."
              : "از خرید شما سپاسگزاریم. وضعیت را با کد پیگیری در حساب کاربری دنبال کنید."}
        </p>

        <div className="mt-6 min-w-0 rounded-2xl bg-secondary p-4 sm:p-5">
          <p className="text-xs text-muted-foreground">کد پیگیری</p>
          <div className="mt-1 flex min-w-0 items-center justify-center gap-2 sm:gap-3">
            <p className="min-w-0 break-all text-xl font-bold tracking-wider text-primary tnum sm:text-2xl">
              {toPersianDigits(ref)}
            </p>
            <button
              type="button"
              onClick={() => {
                void navigator.clipboard?.writeText(ref).then(() => {
                  setCopied(true);
                  window.setTimeout(() => setCopied(false), 2000);
                });
              }}
              aria-label="کپی کد پیگیری"
              className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-primary"
            >
              <Paper size="small" set={copied ? "bold" : "light"} />
            </button>
          </div>
          {copied && <p className="mt-1 text-xs text-success">کد پیگیری کپی شد.</p>}
        </div>

        <div className="mt-6 min-w-0 overflow-hidden rounded-2xl border border-border p-4 text-start sm:p-5">
          <p className="text-sm font-bold text-foreground">وضعیت {isInquiry ? "استعلام" : "سفارش"}</p>
          {isPending && (
            <div className="mt-3 space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-full" />
            </div>
          )}
          {isError && (
            <p className="mt-2 break-words text-sm text-muted-foreground">
              اطلاعات وضعیت در حال حاضر در دسترس نیست.
            </p>
          )}
          {tracking && (
            <>
              <p className="mt-2 break-words text-sm font-bold text-primary">{tracking.status_label}</p>
              {tracking.postal_tracking_code && (
                <p className="mt-2 break-words text-xs text-muted-foreground">
                  کد رهگیری پست:{" "}
                  <span className="break-all font-bold text-foreground tnum">
                    {tracking.postal_tracking_code}
                  </span>
                </p>
              )}
              <div className="mt-3 min-w-0 max-w-full overflow-x-auto">
                <OrderTimeline
                  events={tracking.timeline}
                  estimated={Boolean(tracking.timeline_estimated)}
                />
              </div>
            </>
          )}
        </div>

        <div className="mt-8 flex min-w-0 flex-col gap-3 sm:flex-row">
          <Link href="/" className="min-w-0 flex-1">
            <Button variant="soft" size="lg" className="w-full gap-2">
              <Home set="bold" />
              بازگشت به خانه
            </Button>
          </Link>
          <Link
            href={isInquiry ? `/account/orders/${encodeURIComponent(ref)}` : "/account/orders"}
            className="min-w-0 flex-1"
          >
            <Button size="lg" className="w-full gap-2">
              {isInquiry ? <Document set="bold" /> : <Call set="bold" />}
              {isInquiry ? "پیگیری استعلام" : "سفارش‌های من"}
            </Button>
          </Link>
        </div>
      </motion.div>
    </Container>
  );
}
