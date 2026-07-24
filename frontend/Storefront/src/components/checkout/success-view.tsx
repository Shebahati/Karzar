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
    <Container className="grid min-h-[70vh] place-items-center py-12">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="w-full max-w-lg rounded-3xl bg-card p-8 text-center shadow-elevated sm:p-12"
      >
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 14, delay: 0.15 }}
          className="mx-auto grid h-20 w-20 place-items-center rounded-full bg-success text-success-foreground shadow-elevated"
        >
          <TickSquare set="bold" size="xlarge" />
        </motion.span>

        <h1 className="mt-6 text-2xl font-bold text-foreground">
          {isInquiry ? "استعلام شما ثبت شد" : paid ? "پرداخت با موفقیت انجام شد" : "سفارش شما ثبت شد"}
        </h1>
        <p className="mt-2 text-sm leading-7 text-muted-foreground">
          {isInquiry
            ? "کارشناسان ما درخواست شما را بررسی کرده و در اسرع وقت پیش‌فاکتور را ارسال می‌کنند."
            : paid
              ? "از خرید شما سپاسگزاریم. سفارش در حال پردازش است."
              : "از خرید شما سپاسگزاریم. وضعیت را با کد پیگیری در حساب کاربری دنبال کنید."}
        </p>

        <div className="mt-6 rounded-2xl bg-secondary p-5">
          <p className="text-xs text-muted-foreground">کد پیگیری</p>
          <div className="mt-1 flex items-center justify-center gap-3">
            <p className="text-2xl font-bold tracking-wider text-primary tnum">{toPersianDigits(ref)}</p>
            <button
              type="button"
              onClick={() => {
                void navigator.clipboard?.writeText(ref).then(() => {
                  setCopied(true);
                  window.setTimeout(() => setCopied(false), 2000);
                });
              }}
              aria-label="کپی کد پیگیری"
              className="grid h-8 w-8 place-items-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-primary"
            >
              <Paper size="small" set={copied ? "bold" : "light"} />
            </button>
          </div>
          {copied && <p className="mt-1 text-xs text-success">کد پیگیری کپی شد.</p>}
        </div>

        <div className="mt-6 rounded-2xl border border-border p-5 text-start">
          <p className="text-sm font-bold text-foreground">وضعیت {isInquiry ? "استعلام" : "سفارش"}</p>
          {isPending && (
            <div className="mt-3 space-y-2">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-full" />
            </div>
          )}
          {isError && (
            <p className="mt-2 text-sm text-muted-foreground">
              اطلاعات وضعیت در حال حاضر در دسترس نیست.
            </p>
          )}
          {tracking && (
            <>
              <p className="mt-2 text-sm font-bold text-primary">{tracking.status_label}</p>
              {tracking.postal_tracking_code && (
                <p className="mt-2 text-xs text-muted-foreground">
                  کد رهگیری پست:{" "}
                  <span className="font-bold text-foreground tnum">{tracking.postal_tracking_code}</span>
                </p>
              )}
              <OrderTimeline
                events={tracking.timeline}
                estimated={Boolean(tracking.timeline_estimated)}
              />
            </>
          )}
        </div>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link href="/" className="flex-1">
            <Button variant="soft" size="lg" className="w-full gap-2">
              <Home set="bold" />
              بازگشت به خانه
            </Button>
          </Link>
          <Link
            href={isInquiry ? `/account/orders/${encodeURIComponent(ref)}` : "/account/orders"}
            className="flex-1"
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
